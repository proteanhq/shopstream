"""Stock initialization — command and handler."""

from protean import handle
from protean.fields import Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.stock import InventoryItem


@inventory.command(part_of="InventoryItem")
class InitializeStock:
    """Create a new inventory record for a product variant at a warehouse."""

    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    warehouse_id: str = Identifier(required=True)
    sku: str = String(required=True, max_length=50)
    initial_quantity: int = Integer(default=0)
    reorder_point: int = Integer(default=10)
    reorder_quantity: int = Integer(default=50)


@inventory.command_handler(part_of=InventoryItem)
class InitializeStockHandler:
    @handle(InitializeStock)
    def initialize_stock(self, command: InitializeStock) -> str:
        item = InventoryItem.create(
            product_id=command.product_id,
            variant_id=command.variant_id,
            warehouse_id=command.warehouse_id,
            sku=command.sku,
            initial_quantity=command.initial_quantity or 0,
            reorder_point=command.reorder_point or 10,
            reorder_quantity=command.reorder_quantity or 50,
        )
        current_domain.repository_for(InventoryItem).add(item)
        return str(item.id)
