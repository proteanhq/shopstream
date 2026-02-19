"""Tests for stock return operations."""

import pytest
from inventory.stock.events import StockReturned
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


class TestReturnToStock:
    def test_return_increases_on_hand(self):
        item = _make_item(initial_quantity=80)
        item.return_to_stock(quantity=5, order_id="ord-001")
        assert item.levels.on_hand == 85

    def test_return_increases_available(self):
        item = _make_item(initial_quantity=80)
        item.return_to_stock(quantity=5, order_id="ord-001")
        assert item.levels.available == 85

    def test_return_raises_stock_returned_event(self):
        item = _make_item(initial_quantity=80)
        item.return_to_stock(quantity=5, order_id="ord-001")
        returned_events = [e for e in item._events if isinstance(e, StockReturned)]
        assert len(returned_events) == 1
        event = returned_events[0]
        assert event.quantity == 5
        assert event.order_id == "ord-001"
        assert event.previous_on_hand == 80
        assert event.new_on_hand == 85
        assert event.new_available == 85

    def test_return_fails_with_zero_quantity(self):
        item = _make_item(initial_quantity=100)
        with pytest.raises(ValidationError) as exc_info:
            item.return_to_stock(quantity=0, order_id="ord-001")
        assert "quantity" in exc_info.value.messages

    def test_return_fails_with_negative_quantity(self):
        item = _make_item(initial_quantity=100)
        with pytest.raises(ValidationError) as exc_info:
            item.return_to_stock(quantity=-5, order_id="ord-001")
        assert "quantity" in exc_info.value.messages

    def test_return_preserves_reserved(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        item.return_to_stock(quantity=10, order_id="ord-002")
        assert item.levels.on_hand == 110
        assert item.levels.reserved == 20
        assert item.levels.available == 90

    def test_multiple_returns_accumulate(self):
        item = _make_item(initial_quantity=80)
        item.return_to_stock(quantity=5, order_id="ord-001")
        item.return_to_stock(quantity=3, order_id="ord-002")
        assert item.levels.on_hand == 88
        assert item.levels.available == 88
