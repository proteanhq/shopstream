"""Application tests for stock initialization via domain.process()."""

from inventory.stock.initialization import InitializeStock
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


class TestInitializeStockFlow:
    def test_initialize_returns_id(self):
        item_id = _initialize_stock()
        assert item_id is not None

    def test_initialize_persists_in_event_store(self):
        item_id = _initialize_stock()
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert str(item.id) == item_id

    def test_initialize_sets_stock_levels(self):
        item_id = _initialize_stock(initial_quantity=100)
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 100
        assert item.levels.available == 100
        assert item.levels.reserved == 0

    def test_initialize_stores_events(self):
        _initialize_stock()
        messages = current_domain.event_store.store.read("inventory::inventory_item")
        stock_init_events = [
            m
            for m in messages
            if m.metadata and m.metadata.headers and m.metadata.headers.type == "Inventory.StockInitialized.v1"
        ]
        assert len(stock_init_events) >= 1

    def test_initialize_sets_sku(self):
        item_id = _initialize_stock(sku="SKU-CUSTOM")
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.sku == "SKU-CUSTOM"

    def test_initialize_sets_reorder_settings(self):
        item_id = _initialize_stock(reorder_point=25, reorder_quantity=100)
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.reorder_point == 25
        assert item.reorder_quantity == 100
