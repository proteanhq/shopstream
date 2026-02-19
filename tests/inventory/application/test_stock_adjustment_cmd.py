"""Application tests for stock adjustment commands."""

from inventory.stock.adjustment import AdjustStock, RecordStockCheck
from inventory.stock.initialization import InitializeStock
from inventory.stock.stock import AdjustmentType, InventoryItem
from protean import current_domain


def _initialize_stock(**overrides):
    defaults = {
        "product_id": "prod-001",
        "variant_id": "var-001",
        "warehouse_id": "wh-001",
        "sku": "TSHIRT-BLK-M",
        "initial_quantity": 100,
        "reorder_point": 10,
        "reorder_quantity": 50,
    }
    defaults.update(overrides)
    command = InitializeStock(**defaults)
    return current_domain.process(command, asynchronous=False)


class TestAdjustStockCommand:
    def test_adjust_via_command(self):
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            AdjustStock(
                inventory_item_id=item_id,
                quantity_change=-10,
                adjustment_type=AdjustmentType.SHRINKAGE.value,
                reason="Inventory shrinkage",
                adjusted_by="manager-001",
            ),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 90
        assert item.levels.available == 90

    def test_stock_check_via_command(self):
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            RecordStockCheck(
                inventory_item_id=item_id,
                counted_quantity=95,
                checked_by="checker-001",
            ),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        # Auto-adjusted from 100 to 95
        assert item.levels.on_hand == 95
        assert item.last_stock_check is not None
