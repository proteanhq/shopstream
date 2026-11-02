"""Reservation expiry — command and handler for releasing stale reservations.

Designed to be triggered periodically by an external scheduler (cron, K8s
CronJob) via the maintenance API endpoint. Queries the ReservationStatus
projection for Active reservations past their expiry time and dispatches
ReleaseReservation commands for each.
"""

from datetime import datetime, timedelta

import structlog
from protean import handle
from protean.fields import DateTime, Integer
from protean.utils.globals import current_domain
from protean.utils.processing import Priority, processing_priority

from inventory.domain import inventory
from inventory.projections.reservation_status import ReservationStatus
from inventory.stock.stock import InventoryItem

logger = structlog.get_logger(__name__)


@inventory.command(part_of="InventoryItem")
class ExpireStaleReservations:
    """Release reservations older than the specified threshold."""

    older_than_minutes: int = Integer(default=15)
    as_of: datetime | None = DateTime()  # Optional: defaults to the domain clock


@inventory.command_handler(part_of=InventoryItem)
class ExpireStaleReservationsHandler:
    @handle(ExpireStaleReservations)
    def expire_stale_reservations(self, command: ExpireStaleReservations) -> int:
        with processing_priority(Priority.LOW):
            as_of = command.as_of or current_domain.clock.now()
            threshold_minutes = 15 if command.older_than_minutes is None else command.older_than_minutes
            cutoff = as_of - timedelta(minutes=threshold_minutes)
            # Strip tzinfo for comparison with naive datetimes from DB
            cutoff_naive = cutoff.replace(tzinfo=None)

            logger.info(
                "Checking for stale reservations",
                cutoff=cutoff_naive.isoformat(),
                threshold_minutes=threshold_minutes,
            )

            expired = _expired_reservations(cutoff_naive)
            if not expired:
                logger.info("No stale reservations found")
                return 0

            # Every release joins this handler's transaction. A failed release would
            # roll back all of them, so skip any the aggregate would reject, and let
            # an unexpected failure fail the whole batch instead of reporting success.
            repo = current_domain.repository_for(InventoryItem)
            expired_count = 0
            for reservation in expired:
                item = repo.get_or_none(str(reservation.inventory_item_id))
                blocker = (
                    "Inventory item not found" if item is None else item.release_blocker(reservation.reservation_id)
                )
                if blocker is None:
                    _release(reservation)
                    expired_count += 1
                else:
                    logger.warning(
                        "Skipped stale reservation",
                        reservation_id=str(reservation.reservation_id),
                        error=blocker,
                    )

            logger.info("Stale reservation cleanup complete", expired_count=expired_count)
            return expired_count


def _expired_reservations(cutoff_naive: datetime) -> list[ReservationStatus]:
    active_reservations = current_domain.view_for(ReservationStatus).query.filter(status="Active").all().items
    return [
        reservation
        for reservation in active_reservations
        if reservation.expires_at and reservation.expires_at.replace(tzinfo=None) <= cutoff_naive
    ]


def _release(reservation: ReservationStatus) -> None:
    from inventory.stock.reservation import ReleaseReservation

    current_domain.process(
        ReleaseReservation(
            inventory_item_id=str(reservation.inventory_item_id),
            reservation_id=str(reservation.reservation_id),
            reason="timeout",
        ),
        asynchronous=False,
    )
    logger.info(
        "Released stale reservation",
        reservation_id=str(reservation.reservation_id),
        order_id=str(reservation.order_id),
        expired_at=str(reservation.expires_at),
    )
