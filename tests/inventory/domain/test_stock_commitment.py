"""Tests for stock commitment (shipping) operations."""

import pytest
from inventory.stock.events import StockCommitted
from inventory.stock.stock import InventoryItem
from protean.exceptions import ValidationError


def _make_item(**overrides):
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
    return InventoryItem.create(**defaults)


class TestCommitStock:
    def test_commit_reduces_on_hand(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        item.confirm_reservation(reservation_id=reservation_id)
        item.commit_stock(reservation_id=reservation_id)
        assert item.levels.on_hand == 80

    def test_commit_reduces_reserved(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        item.confirm_reservation(reservation_id=reservation_id)
        item.commit_stock(reservation_id=reservation_id)
        assert item.levels.reserved == 0

    def test_commit_removes_reservation(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        item.confirm_reservation(reservation_id=reservation_id)
        item.commit_stock(reservation_id=reservation_id)
        remaining = [r for r in (item.reservations or []) if str(r.id) == str(reservation_id)]
        assert len(remaining) == 0

    def test_commit_available_stays_correct(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        item.confirm_reservation(reservation_id=reservation_id)
        item.commit_stock(reservation_id=reservation_id)
        # on_hand=80, reserved=0, available should be 80
        assert item.levels.available == 80

    def test_commit_fails_for_unconfirmed_reservation(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        # Don't confirm — should fail
        with pytest.raises(ValidationError) as exc_info:
            item.commit_stock(reservation_id=reservation_id)
        assert "reservation_id" in exc_info.value.messages

    def test_commit_fails_for_nonexistent_reservation(self):
        item = _make_item(initial_quantity=100)
        with pytest.raises(ValidationError) as exc_info:
            item.commit_stock(reservation_id="fake-id")
        assert "reservation_id" in exc_info.value.messages

    def test_commit_raises_stock_committed_event(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        item.confirm_reservation(reservation_id=reservation_id)
        item.commit_stock(reservation_id=reservation_id)
        committed_events = [e for e in item._events if isinstance(e, StockCommitted)]
        assert len(committed_events) == 1
        event = committed_events[0]
        assert event.quantity == 20
        assert event.previous_on_hand == 100
        assert event.new_on_hand == 80
        assert event.previous_reserved == 20
        assert event.new_reserved == 0

    def test_full_reserve_confirm_commit_flow(self):
        item = _make_item(initial_quantity=100)

        # Reserve
        item.reserve(order_id="ord-001", quantity=30)
        assert item.levels.on_hand == 100
        assert item.levels.reserved == 30
        assert item.levels.available == 70

        # Confirm
        reservation_id = item.reservations[0].id
        item.confirm_reservation(reservation_id=reservation_id)
        assert item.levels.reserved == 30  # No change to levels

        # Commit
        item.commit_stock(reservation_id=reservation_id)
        assert item.levels.on_hand == 70
        assert item.levels.reserved == 0
        assert item.levels.available == 70
