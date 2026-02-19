"""Application tests for stock receiving commands."""

from inventory.stock.initialization import InitializeStock
from inventory.stock.receiving import ReceiveStock
from inventory.stock.stock import InventoryItem
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


class TestReceiveStockCommand:
    def test_receive_updates_on_hand(self):
        item_id = _initialize_stock(initial_quantity=50)
        current_domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=30),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 80
        assert item.levels.available == 80

    def test_receive_multiple_commands_accumulate(self):
        item_id = _initialize_stock(initial_quantity=50)
        current_domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=20),
            asynchronous=False,
        )
        current_domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=30),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 100
