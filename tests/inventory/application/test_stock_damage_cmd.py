"""Application tests for stock damage commands."""

from inventory.stock.damage import MarkDamaged, WriteOffDamaged
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


class TestDamageCommands:
    def test_mark_damaged_via_command(self):
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            MarkDamaged(
                inventory_item_id=item_id,
                quantity=5,
                reason="Water damage",
            ),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 95
        assert item.levels.damaged == 5

    def test_write_off_via_command(self):
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            MarkDamaged(
                inventory_item_id=item_id,
                quantity=10,
                reason="Flood",
            ),
            asynchronous=False,
        )
        current_domain.process(
            WriteOffDamaged(
                inventory_item_id=item_id,
                quantity=5,
                approved_by="manager-001",
            ),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.damaged == 5
