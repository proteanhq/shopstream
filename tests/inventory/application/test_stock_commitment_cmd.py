"""Application tests for stock commitment commands."""

from inventory.stock.initialization import InitializeStock
from inventory.stock.reservation import ConfirmReservation, ReserveStock
from inventory.stock.shipping import CommitStock
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


class TestCommitStockCommand:
    def test_commit_reduces_on_hand_via_command(self):
        item_id = _initialize_stock(initial_quantity=100)

        # Reserve
        current_domain.process(
            ReserveStock(inventory_item_id=item_id, order_id="ord-001", quantity=20),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        reservation_id = str(item.reservations[0].id)

        # Confirm
        current_domain.process(
            ConfirmReservation(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )

        # Commit
        current_domain.process(
            CommitStock(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 80
        assert item.levels.reserved == 0
        assert item.levels.available == 80

    def test_full_reserve_confirm_commit_flow(self):
        item_id = _initialize_stock(initial_quantity=100)

        # Reserve 30
        current_domain.process(
            ReserveStock(inventory_item_id=item_id, order_id="ord-001", quantity=30),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.available == 70
        reservation_id = str(item.reservations[0].id)

        # Confirm
        current_domain.process(
            ConfirmReservation(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )

        # Commit (ship)
        current_domain.process(
            CommitStock(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 70
        assert item.levels.reserved == 0
        assert item.levels.available == 70
        assert len(list(item.reservations or [])) == 0
