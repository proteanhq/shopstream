"""Tests for damage tracking operations."""

import pytest
from inventory.stock.events import DamagedStockWrittenOff, LowStockDetected, StockMarkedDamaged
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


class TestMarkDamaged:
    def test_mark_damaged_reduces_on_hand(self):
        item = _make_item(initial_quantity=100)
        item.mark_damaged(quantity=5, reason="Water damage")
        assert item.levels.on_hand == 95

    def test_mark_damaged_increases_damaged(self):
        item = _make_item(initial_quantity=100)
        item.mark_damaged(quantity=5, reason="Water damage")
        assert item.levels.damaged == 5

    def test_mark_damaged_reduces_available(self):
        item = _make_item(initial_quantity=100)
        item.mark_damaged(quantity=5, reason="Water damage")
        assert item.levels.available == 95

    def test_mark_damaged_raises_event(self):
        item = _make_item(initial_quantity=100)
        item.mark_damaged(quantity=5, reason="Water damage")
        damaged_events = [e for e in item._events if isinstance(e, StockMarkedDamaged)]
        assert len(damaged_events) == 1
        event = damaged_events[0]
        assert event.quantity == 5
        assert event.reason == "Water damage"
        assert event.previous_on_hand == 100
        assert event.new_on_hand == 95
        assert event.previous_damaged == 0
        assert event.new_damaged == 5

    def test_mark_damaged_fails_when_exceeds_unreserved_stock(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=90)
        # Only 10 unreserved
        with pytest.raises(ValidationError) as exc_info:
            item.mark_damaged(quantity=15, reason="Flood")
        assert "quantity" in exc_info.value.messages

    def test_mark_damaged_fails_with_zero_quantity(self):
        item = _make_item(initial_quantity=100)
        with pytest.raises(ValidationError) as exc_info:
            item.mark_damaged(quantity=0, reason="Test")
        assert "quantity" in exc_info.value.messages

    def test_mark_damaged_fails_without_reason(self):
        item = _make_item(initial_quantity=100)
        with pytest.raises(ValidationError) as exc_info:
            item.mark_damaged(quantity=5, reason="")
        assert "reason" in exc_info.value.messages

    def test_mark_damaged_multiple_times(self):
        item = _make_item(initial_quantity=100)
        item.mark_damaged(quantity=5, reason="Water damage")
        item.mark_damaged(quantity=3, reason="Broken packaging")
        assert item.levels.on_hand == 92
        assert item.levels.damaged == 8
        assert item.levels.available == 92

    def test_mark_damaged_triggers_low_stock(self):
        item = _make_item(initial_quantity=20, reorder_point=10)
        item.mark_damaged(quantity=15, reason="Fire damage")
        low_stock_events = [e for e in item._events if isinstance(e, LowStockDetected)]
        assert len(low_stock_events) == 1


class TestWriteOffDamaged:
    def test_write_off_reduces_damaged(self):
        item = _make_item(initial_quantity=100)
        item.mark_damaged(quantity=10, reason="Flood")
        item.write_off_damaged(quantity=5, approved_by="manager-001")
        assert item.levels.damaged == 5

    def test_write_off_raises_event(self):
        item = _make_item(initial_quantity=100)
        item.mark_damaged(quantity=10, reason="Flood")
        item.write_off_damaged(quantity=5, approved_by="manager-001")
        writeoff_events = [e for e in item._events if isinstance(e, DamagedStockWrittenOff)]
        assert len(writeoff_events) == 1
        event = writeoff_events[0]
        assert event.quantity == 5
        assert event.approved_by == "manager-001"
        assert event.previous_damaged == 10
        assert event.new_damaged == 5

    def test_write_off_fails_when_exceeds_damaged(self):
        item = _make_item(initial_quantity=100)
        item.mark_damaged(quantity=5, reason="Test")
        with pytest.raises(ValidationError) as exc_info:
            item.write_off_damaged(quantity=10, approved_by="manager-001")
        assert "quantity" in exc_info.value.messages

    def test_write_off_fails_with_zero_quantity(self):
        item = _make_item(initial_quantity=100)
        item.mark_damaged(quantity=5, reason="Test")
        with pytest.raises(ValidationError) as exc_info:
            item.write_off_damaged(quantity=0, approved_by="manager-001")
        assert "quantity" in exc_info.value.messages

    def test_write_off_does_not_affect_on_hand(self):
        item = _make_item(initial_quantity=100)
        item.mark_damaged(quantity=10, reason="Flood")
        on_hand_after_damage = item.levels.on_hand
        item.write_off_damaged(quantity=5, approved_by="manager-001")
        assert item.levels.on_hand == on_hand_after_damage

    def test_write_off_all_damaged(self):
        item = _make_item(initial_quantity=100)
        item.mark_damaged(quantity=10, reason="Flood")
        item.write_off_damaged(quantity=10, approved_by="manager-001")
        assert item.levels.damaged == 0
