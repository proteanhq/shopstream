"""Stock reservation — commands and handler."""

from datetime import UTC, datetime, timedelta

from protean import handle
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.stock import InventoryItem


@inventory.command(part_of="InventoryItem")
class ReserveStock:
    """Reserve stock for an order."""

    inventory_item_id = Identifier(required=True)
    order_id = Identifier(required=True)
    quantity = Integer(required=True)
    expires_at = DateTime()  # Optional; defaults to 15 minutes from now


@inventory.command(part_of="InventoryItem")
class ReleaseReservation:
    """Release a stock reservation."""

    inventory_item_id = Identifier(required=True)
    reservation_id = Identifier(required=True)
    reason = String(required=True)


@inventory.command(part_of="InventoryItem")
class ConfirmReservation:
    """Confirm a stock reservation after order payment."""

    inventory_item_id = Identifier(required=True)
    reservation_id = Identifier(required=True)


@inventory.command_handler(part_of=InventoryItem)
class ReservationHandler:
    @handle(ReserveStock)
    def reserve_stock(self, command):
        repo = current_domain.repository_for(InventoryItem)
        item = repo.get(command.inventory_item_id)

        expires_at = command.expires_at
        if expires_at is None:
            expires_at = datetime.now(UTC) + timedelta(minutes=15)

        item.reserve(
            order_id=command.order_id,
            quantity=command.quantity,
            expires_at=expires_at,
        )
        repo.add(item)

    @handle(ReleaseReservation)
    def release_reservation(self, command):
        repo = current_domain.repository_for(InventoryItem)
        item = repo.get(command.inventory_item_id)
        item.release_reservation(
            reservation_id=command.reservation_id,
            reason=command.reason,
        )
        repo.add(item)

    @handle(ConfirmReservation)
    def confirm_reservation(self, command):
        repo = current_domain.repository_for(InventoryItem)
        item = repo.get(command.inventory_item_id)
        item.confirm_reservation(reservation_id=command.reservation_id)
        repo.add(item)
