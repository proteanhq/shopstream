"""Stock returns — command and handler."""

from protean import handle
from protean.fields import Identifier, Integer
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.stock import InventoryItem


@inventory.command(part_of="InventoryItem")
class ReturnToStock:
    """Add returned items back to inventory."""

    inventory_item_id = Identifier(required=True)
    quantity = Integer(required=True)
    order_id = Identifier(required=True)


@inventory.command_handler(part_of=InventoryItem)
class ReturnToStockHandler:
    @handle(ReturnToStock)
    def return_to_stock(self, command):
        repo = current_domain.repository_for(InventoryItem)
        item = repo.get(command.inventory_item_id)
        item.return_to_stock(
            quantity=command.quantity,
            order_id=command.order_id,
        )
        repo.add(item)
