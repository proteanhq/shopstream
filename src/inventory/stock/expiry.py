"""Reservation expiry — command and handler for releasing stale reservations.

Designed to be triggered periodically by an external scheduler (cron, K8s
CronJob) via the maintenance API endpoint. Queries the ReservationStatus
projection for Active reservations past their expiry time and dispatches
ReleaseReservation commands for each.
"""

from datetime import UTC, datetime, timedelta

import structlog
from protean import handle
from protean.exceptions import ObjectNotFoundError
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

    older_than_minutes = Integer(default=15)
    as_of = DateTime()  # Optional: defaults to now


@inventory.command_handler(part_of=InventoryItem)
class ExpireStaleReservationsHandler:
    @handle(ExpireStaleReservations)
    def expire_stale_reservations(self, command):
        with processing_priority(Priority.LOW):
            as_of = command.as_of or datetime.now(UTC)
            threshold_minutes = command.older_than_minutes or 15
            cutoff = as_of - timedelta(minutes=threshold_minutes)
            # Strip tzinfo for comparison with naive datetimes from DB
            cutoff_naive = cutoff.replace(tzinfo=None)

            logger.info(
                "Checking for stale reservations",
                cutoff=cutoff_naive.isoformat(),
                threshold_minutes=threshold_minutes,
            )

            # Query active reservations
            active_reservations = current_domain.view_for(ReservationStatus).query.filter(status="Active").all().items

            # Filter expired ones
            expired = []
            for reservation in active_reservations:
                if reservation.expires_at:
                    # Normalize both to naive for comparison
                    expires = (
                        reservation.expires_at.replace(tzinfo=None)
                        if reservation.expires_at.tzinfo
                        else reservation.expires_at
                    )
                    if expires <= cutoff_naive:
                        expired.append(reservation)

            if not expired:
                logger.info("No stale reservations found")
                return 0

            from inventory.stock.reservation import ReleaseReservation

            # Every release joins this handler's transaction. A failed release would
            # roll back all of them, so skip any the aggregate would reject, and let
            # an unexpected failure fail the whole batch instead of reporting success.
            repo = current_domain.repository_for(InventoryItem)
            expired_count = 0
            for reservation in expired:
                try:
                    item = repo.get(str(reservation.inventory_item_id))
                except ObjectNotFoundError:
                    blocker = "Inventory item not found"
                else:
                    blocker = item.release_blocker(reservation.reservation_id)
                if blocker is not None:
                    logger.warning(
                        "Skipped stale reservation",
                        reservation_id=str(reservation.reservation_id),
                        error=blocker,
                    )
                    continue

                current_domain.process(
                    ReleaseReservation(
                        inventory_item_id=str(reservation.inventory_item_id),
                        reservation_id=str(reservation.reservation_id),
                        reason="timeout",
                    ),
                    asynchronous=False,
                )
                expired_count += 1
                logger.info(
                    "Released stale reservation",
                    reservation_id=str(reservation.reservation_id),
                    order_id=str(reservation.order_id),
                    expired_at=str(reservation.expires_at),
                )

            logger.info("Stale reservation cleanup complete", expired_count=expired_count)
            return expired_count
