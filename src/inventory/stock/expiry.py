"""Reservation expiry — command and handler for releasing stale reservations.

Designed to be triggered periodically by an external scheduler (cron, K8s
CronJob) via the maintenance API endpoint. Queries the ReservationStatus
projection for Active reservations past their expiry time and dispatches
ReleaseReservation commands for each.
"""

from datetime import UTC, datetime, timedelta

import structlog
from protean import handle
from protean.exceptions import InvalidOperationError, ValidationError
from protean.fields import DateTime, Integer
from protean.utils.globals import current_domain

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
        as_of = command.as_of or datetime.now(UTC)
        threshold_minutes = command.older_than_minutes or 15
        cutoff = (as_of - timedelta(minutes=threshold_minutes)).replace(tzinfo=None)

        logger.info(
            "Checking for stale reservations",
            cutoff=cutoff.isoformat(),
            threshold_minutes=threshold_minutes,
        )

        # Query active reservations
        active_reservations = (
            current_domain.repository_for(ReservationStatus)._dao.query.filter(status="Active").all().items
        )

        # Filter expired ones
        expired = []
        for reservation in active_reservations:
            if reservation.expires_at and reservation.expires_at <= cutoff:
                expired.append(reservation)

        if not expired:
            logger.info("No stale reservations found")
            return 0

        from inventory.stock.reservation import ReleaseReservation

        expired_count = 0
        for reservation in expired:
            try:
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
            except (ValidationError, InvalidOperationError) as exc:
                logger.warning(
                    "Failed to release stale reservation",
                    reservation_id=str(reservation.reservation_id),
                    error=str(exc),
                )

        logger.info("Stale reservation cleanup complete", expired_count=expired_count)
        return expired_count
