"""Application tests for stock return commands."""

from inventory.stock.initialization import InitializeStock
from inventory.stock.returns import ReturnToStock
from inventory.stock.stock import InventoryItem
from protean import current_domain


def _initialize_stock(**overrides):
    defaults = {
        "product_id": "prod-001",
        "variant_id": "var-001",
        "warehouse_id": "wh-001",
        "sku": "TSHIRT-BLK-M",
        "initial_quantity": 80,
        "reorder_point": 10,
        "reorder_quantity": 50,
    }
    defaults.update(overrides)
    command = InitializeStock(**defaults)
    return current_domain.process(command, asynchronous=False)


class TestReturnToStockCommand:
    def test_return_to_stock_via_command(self):
        item_id = _initialize_stock(initial_quantity=80)
        current_domain.process(
            ReturnToStock(
                inventory_item_id=item_id,
                quantity=10,
                order_id="ord-001",
            ),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 90
        assert item.levels.available == 90
