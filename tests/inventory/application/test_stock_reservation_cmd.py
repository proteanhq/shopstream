"""Application tests for stock reservation commands."""

from inventory.stock.initialization import InitializeStock
from inventory.stock.reservation import ConfirmReservation, ReleaseReservation, ReserveStock
from inventory.stock.stock import InventoryItem, ReservationStatus
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


class TestReserveStockCommand:
    def test_reserve_persists(self):
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            ReserveStock(inventory_item_id=item_id, order_id="ord-001", quantity=20),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.reserved == 20
        assert item.levels.available == 80
        assert len(item.reservations) == 1

    def test_release_persists(self):
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            ReserveStock(inventory_item_id=item_id, order_id="ord-001", quantity=20),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        reservation_id = item.reservations[0].id

        current_domain.process(
            ReleaseReservation(
                inventory_item_id=item_id,
                reservation_id=str(reservation_id),
                reason="order_cancelled",
            ),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.reserved == 0
        assert item.levels.available == 100

    def test_confirm_persists(self):
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            ReserveStock(inventory_item_id=item_id, order_id="ord-001", quantity=20),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        reservation_id = item.reservations[0].id

        current_domain.process(
            ConfirmReservation(
                inventory_item_id=item_id,
                reservation_id=str(reservation_id),
            ),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        reservation = next(r for r in item.reservations if str(r.id) == str(reservation_id))
        assert reservation.status == ReservationStatus.CONFIRMED.value

    def test_reserve_then_release_then_reserve_again(self):
        item_id = _initialize_stock(initial_quantity=100)

        # Reserve
        current_domain.process(
            ReserveStock(inventory_item_id=item_id, order_id="ord-001", quantity=50),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        reservation_id = item.reservations[0].id

        # Release
        current_domain.process(
            ReleaseReservation(
                inventory_item_id=item_id,
                reservation_id=str(reservation_id),
                reason="cancelled",
            ),
            asynchronous=False,
        )

        # Reserve again
        current_domain.process(
            ReserveStock(inventory_item_id=item_id, order_id="ord-002", quantity=30),
            asynchronous=False,
        )
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.available == 70
        assert item.levels.reserved == 30
