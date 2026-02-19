"""Tests for stock receiving operations."""

import pytest
from inventory.stock.events import StockReceived
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


class TestReceiveStock:
    def test_receive_increases_on_hand(self):
        item = _make_item(initial_quantity=100)
        item.receive_stock(quantity=50)
        assert item.levels.on_hand == 150

    def test_receive_increases_available(self):
        item = _make_item(initial_quantity=100)
        item.receive_stock(quantity=50)
        assert item.levels.available == 150

    def test_receive_raises_stock_received_event(self):
        item = _make_item(initial_quantity=100)
        item.receive_stock(quantity=50)
        received_events = [e for e in item._events if isinstance(e, StockReceived)]
        assert len(received_events) == 1
        event = received_events[0]
        assert event.quantity == 50
        assert event.previous_on_hand == 100
        assert event.new_on_hand == 150
        assert event.new_available == 150

    def test_receive_fails_with_zero_quantity(self):
        item = _make_item()
        with pytest.raises(ValidationError) as exc_info:
            item.receive_stock(quantity=0)
        assert "quantity" in exc_info.value.messages

    def test_receive_fails_with_negative_quantity(self):
        item = _make_item()
        with pytest.raises(ValidationError) as exc_info:
            item.receive_stock(quantity=-10)
        assert "quantity" in exc_info.value.messages

    def test_receive_multiple_times_accumulates(self):
        item = _make_item(initial_quantity=50)
        item.receive_stock(quantity=30)
        item.receive_stock(quantity=20)
        assert item.levels.on_hand == 100
        assert item.levels.available == 100

    def test_receive_with_reference(self):
        item = _make_item(initial_quantity=100)
        item.receive_stock(quantity=50, reference="PO-12345")
        received_events = [e for e in item._events if isinstance(e, StockReceived)]
        assert received_events[0].reference == "PO-12345"

    def test_receive_preserves_reserved(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        item.receive_stock(quantity=50)
        assert item.levels.on_hand == 150
        assert item.levels.reserved == 20
        assert item.levels.available == 130
