"""Stock receiving — command and handler."""

from protean import handle
from protean.fields import Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.stock import InventoryItem


@inventory.command(part_of="InventoryItem")
class ReceiveStock:
    """Record incoming stock received at the warehouse."""

    inventory_item_id = Identifier(required=True)
    quantity = Integer(required=True)
    reference = String(max_length=255)  # Receiving document number


@inventory.command_handler(part_of=InventoryItem)
class ReceiveStockHandler:
    @handle(ReceiveStock)
    def receive_stock(self, command):
        repo = current_domain.repository_for(InventoryItem)
        item = repo.get(command.inventory_item_id)
        item.receive_stock(
            quantity=command.quantity,
            reference=command.reference,
        )
        repo.add(item)
