"""Stock adjustment — commands and handler."""

from protean import handle
from protean.fields import Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.stock import InventoryItem


@inventory.command(part_of="InventoryItem")
class AdjustStock:
    """Manually adjust stock levels."""

    inventory_item_id: str = Identifier(required=True)
    quantity_change: int = Integer(required=True)  # Can be negative
    adjustment_type: str = String(required=True)  # Count, Shrinkage, Correction, Receiving_Error
    reason: str = String(required=True)
    adjusted_by: str = String(required=True)


@inventory.command(part_of="InventoryItem")
class RecordStockCheck:
    """Record a physical stock count."""

    inventory_item_id: str = Identifier(required=True)
    counted_quantity: int = Integer(required=True)
    checked_by: str = String(required=True)


@inventory.command_handler(part_of=InventoryItem)
class StockAdjustmentHandler:
    @handle(AdjustStock)
    def adjust_stock(self, command: AdjustStock) -> None:
        repo = current_domain.repository_for(InventoryItem)
        item = repo.get(command.inventory_item_id)
        item.adjust_stock(
            quantity_change=command.quantity_change,
            adjustment_type=command.adjustment_type,
            reason=command.reason,
            adjusted_by=command.adjusted_by,
        )
        repo.add(item)

    @handle(RecordStockCheck)
    def record_stock_check(self, command: RecordStockCheck) -> None:
        repo = current_domain.repository_for(InventoryItem)
        item = repo.get(command.inventory_item_id)
        item.record_stock_check(
            counted_quantity=command.counted_quantity,
            checked_by=command.checked_by,
        )
        repo.add(item)
