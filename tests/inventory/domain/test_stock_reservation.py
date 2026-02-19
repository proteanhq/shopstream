"""Tests for stock reservation lifecycle — reserve, release, confirm."""

from datetime import UTC, datetime, timedelta

import pytest
from inventory.stock.events import (
    LowStockDetected,
    ReservationConfirmed,
    ReservationReleased,
    StockReserved,
)
from inventory.stock.stock import InventoryItem, ReservationStatus
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


class TestReserveStock:
    def test_reserve_decreases_available(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        assert item.levels.available == 80

    def test_reserve_increases_reserved(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        assert item.levels.reserved == 20

    def test_reserve_creates_reservation_entity(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        assert len(item.reservations) == 1
        reservation = item.reservations[0]
        assert str(reservation.order_id) == "ord-001"
        assert reservation.quantity == 20
        assert reservation.status == ReservationStatus.ACTIVE.value

    def test_reserve_fails_with_zero_quantity(self):
        item = _make_item(initial_quantity=100)
        with pytest.raises(ValidationError) as exc_info:
            item.reserve(order_id="ord-001", quantity=0)
        assert "quantity" in exc_info.value.messages

    def test_reserve_fails_with_negative_quantity(self):
        item = _make_item(initial_quantity=100)
        with pytest.raises(ValidationError) as exc_info:
            item.reserve(order_id="ord-001", quantity=-5)
        assert "quantity" in exc_info.value.messages

    def test_reserve_fails_when_insufficient_stock(self):
        item = _make_item(initial_quantity=10)
        with pytest.raises(ValidationError) as exc_info:
            item.reserve(order_id="ord-001", quantity=20)
        assert "quantity" in exc_info.value.messages

    def test_reserve_fails_when_zero_available(self):
        item = _make_item(initial_quantity=0)
        with pytest.raises(ValidationError) as exc_info:
            item.reserve(order_id="ord-001", quantity=1)
        assert "quantity" in exc_info.value.messages

    def test_reserve_with_exact_available_quantity(self):
        item = _make_item(initial_quantity=50)
        item.reserve(order_id="ord-001", quantity=50)
        assert item.levels.available == 0
        assert item.levels.reserved == 50

    def test_reserve_raises_stock_reserved_event(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reserved_events = [e for e in item._events if isinstance(e, StockReserved)]
        assert len(reserved_events) == 1
        event = reserved_events[0]
        assert event.quantity == 20
        assert event.previous_available == 100
        assert event.new_available == 80

    def test_reserve_with_custom_expires_at(self):
        item = _make_item(initial_quantity=100)
        expires = datetime.now(UTC) + timedelta(hours=1)
        item.reserve(order_id="ord-001", quantity=10, expires_at=expires)
        reserved_events = [e for e in item._events if isinstance(e, StockReserved)]
        assert reserved_events[0].expires_at is not None

    def test_multiple_reservations_tracked_independently(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        item.reserve(order_id="ord-002", quantity=30)
        assert len(item.reservations) == 2
        assert item.levels.reserved == 50
        assert item.levels.available == 50

    def test_reserve_triggers_low_stock_when_below_reorder_point(self):
        item = _make_item(initial_quantity=20, reorder_point=10)
        item.reserve(order_id="ord-001", quantity=15)
        low_stock_events = [e for e in item._events if isinstance(e, LowStockDetected)]
        assert len(low_stock_events) == 1
        assert low_stock_events[0].current_available == 5


class TestReleaseReservation:
    def test_release_increases_available(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        item.release_reservation(reservation_id=reservation_id, reason="order_cancelled")
        assert item.levels.available == 100

    def test_release_decreases_reserved(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        item.release_reservation(reservation_id=reservation_id, reason="order_cancelled")
        assert item.levels.reserved == 0

    def test_release_marks_reservation_released(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        item.release_reservation(reservation_id=reservation_id, reason="timeout")
        reservation = next(r for r in item.reservations if str(r.id) == str(reservation_id))
        assert reservation.status == ReservationStatus.RELEASED.value

    def test_release_fails_for_nonexistent_reservation(self):
        item = _make_item(initial_quantity=100)
        with pytest.raises(ValidationError) as exc_info:
            item.release_reservation(reservation_id="fake-id", reason="test")
        assert "reservation_id" in exc_info.value.messages

    def test_release_fails_for_already_released_reservation(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        item.release_reservation(reservation_id=reservation_id, reason="timeout")
        with pytest.raises(ValidationError) as exc_info:
            item.release_reservation(reservation_id=reservation_id, reason="duplicate")
        assert "reservation_id" in exc_info.value.messages

    def test_release_raises_reservation_released_event(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        item.release_reservation(reservation_id=reservation_id, reason="order_cancelled")
        released_events = [e for e in item._events if isinstance(e, ReservationReleased)]
        assert len(released_events) == 1
        event = released_events[0]
        assert event.quantity == 20
        assert event.reason == "order_cancelled"
        assert event.previous_available == 80
        assert event.new_available == 100

    def test_reserve_then_release_restores_available(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=30)
        assert item.levels.available == 70
        reservation_id = item.reservations[0].id
        item.release_reservation(reservation_id=reservation_id, reason="cancelled")
        assert item.levels.available == 100
        assert item.levels.reserved == 0


class TestConfirmReservation:
    def test_confirm_marks_reservation_confirmed(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        item.confirm_reservation(reservation_id=reservation_id)
        reservation = next(r for r in item.reservations if str(r.id) == str(reservation_id))
        assert reservation.status == ReservationStatus.CONFIRMED.value

    def test_confirm_fails_for_nonexistent_reservation(self):
        item = _make_item(initial_quantity=100)
        with pytest.raises(ValidationError) as exc_info:
            item.confirm_reservation(reservation_id="fake-id")
        assert "reservation_id" in exc_info.value.messages

    def test_confirm_fails_for_already_confirmed_reservation(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        item.confirm_reservation(reservation_id=reservation_id)
        with pytest.raises(ValidationError) as exc_info:
            item.confirm_reservation(reservation_id=reservation_id)
        assert "reservation_id" in exc_info.value.messages

    def test_confirm_raises_reservation_confirmed_event(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        reservation_id = item.reservations[0].id
        item.confirm_reservation(reservation_id=reservation_id)
        confirmed_events = [e for e in item._events if isinstance(e, ReservationConfirmed)]
        assert len(confirmed_events) == 1
        assert confirmed_events[0].quantity == 20

    def test_confirm_does_not_change_stock_levels(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        item.confirm_reservation(reservation_id=item.reservations[0].id)
        assert item.levels.on_hand == 100
        assert item.levels.reserved == 20
        assert item.levels.available == 80
