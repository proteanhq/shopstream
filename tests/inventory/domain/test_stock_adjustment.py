"""Tests for stock adjustment operations."""

import pytest
from inventory.stock.events import LowStockDetected, StockAdjusted, StockCheckRecorded
from inventory.stock.stock import AdjustmentType, InventoryItem
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


class TestAdjustStock:
    def test_positive_adjustment_increases_on_hand(self):
        item = _make_item(initial_quantity=100)
        item.adjust_stock(
            quantity_change=25,
            adjustment_type=AdjustmentType.CORRECTION.value,
            reason="Found extra stock",
            adjusted_by="manager-001",
        )
        assert item.levels.on_hand == 125
        assert item.levels.available == 125

    def test_negative_adjustment_decreases_on_hand(self):
        item = _make_item(initial_quantity=100)
        item.adjust_stock(
            quantity_change=-10,
            adjustment_type=AdjustmentType.SHRINKAGE.value,
            reason="Unexplained loss",
            adjusted_by="manager-001",
        )
        assert item.levels.on_hand == 90
        assert item.levels.available == 90

    def test_adjustment_fails_when_result_negative(self):
        item = _make_item(initial_quantity=10)
        with pytest.raises(ValidationError) as exc_info:
            item.adjust_stock(
                quantity_change=-20,
                adjustment_type=AdjustmentType.CORRECTION.value,
                reason="Over-correction",
                adjusted_by="manager-001",
            )
        assert "quantity_change" in exc_info.value.messages

    def test_adjustment_requires_reason(self):
        item = _make_item(initial_quantity=100)
        with pytest.raises(ValidationError) as exc_info:
            item.adjust_stock(
                quantity_change=10,
                adjustment_type=AdjustmentType.CORRECTION.value,
                reason="",
                adjusted_by="manager-001",
            )
        assert "reason" in exc_info.value.messages

    def test_adjustment_records_type_and_adjusted_by(self):
        item = _make_item(initial_quantity=100)
        item.adjust_stock(
            quantity_change=-5,
            adjustment_type=AdjustmentType.SHRINKAGE.value,
            reason="Theft",
            adjusted_by="manager-001",
        )
        adjusted_events = [e for e in item._events if isinstance(e, StockAdjusted)]
        assert len(adjusted_events) == 1
        event = adjusted_events[0]
        assert event.adjustment_type == AdjustmentType.SHRINKAGE.value
        assert event.adjusted_by == "manager-001"
        assert event.reason == "Theft"

    def test_adjustment_raises_stock_adjusted_event(self):
        item = _make_item(initial_quantity=100)
        item.adjust_stock(
            quantity_change=-15,
            adjustment_type=AdjustmentType.COUNT.value,
            reason="Physical count",
            adjusted_by="checker-001",
        )
        adjusted_events = [e for e in item._events if isinstance(e, StockAdjusted)]
        assert len(adjusted_events) == 1
        event = adjusted_events[0]
        assert event.previous_on_hand == 100
        assert event.new_on_hand == 85
        assert event.new_available == 85

    def test_adjustment_preserves_reserved(self):
        item = _make_item(initial_quantity=100)
        item.reserve(order_id="ord-001", quantity=20)
        item.adjust_stock(
            quantity_change=10,
            adjustment_type=AdjustmentType.RECEIVING_ERROR.value,
            reason="Received more than logged",
            adjusted_by="manager-001",
        )
        assert item.levels.on_hand == 110
        assert item.levels.reserved == 20
        assert item.levels.available == 90

    def test_adjustment_triggers_low_stock(self):
        item = _make_item(initial_quantity=20, reorder_point=10)
        item.adjust_stock(
            quantity_change=-15,
            adjustment_type=AdjustmentType.SHRINKAGE.value,
            reason="Loss",
            adjusted_by="manager-001",
        )
        low_stock_events = [e for e in item._events if isinstance(e, LowStockDetected)]
        assert len(low_stock_events) == 1
        assert low_stock_events[0].current_available == 5


class TestRecordStockCheck:
    def test_stock_check_records_count(self):
        item = _make_item(initial_quantity=100)
        item.record_stock_check(counted_quantity=100, checked_by="checker-001")
        check_events = [e for e in item._events if isinstance(e, StockCheckRecorded)]
        assert len(check_events) == 1
        event = check_events[0]
        assert event.counted_quantity == 100
        assert event.expected_quantity == 100
        assert event.discrepancy == 0
        assert event.checked_by == "checker-001"

    def test_stock_check_with_discrepancy(self):
        item = _make_item(initial_quantity=100)
        item.record_stock_check(counted_quantity=95, checked_by="checker-001")
        check_events = [e for e in item._events if isinstance(e, StockCheckRecorded)]
        assert len(check_events) == 1
        assert check_events[0].discrepancy == -5

    def test_stock_check_with_discrepancy_auto_adjusts(self):
        item = _make_item(initial_quantity=100)
        item.record_stock_check(counted_quantity=95, checked_by="checker-001")
        # Auto-adjustment should have happened
        assert item.levels.on_hand == 95
        assert item.levels.available == 95

    def test_stock_check_auto_adjustment_raises_event(self):
        item = _make_item(initial_quantity=100)
        item.record_stock_check(counted_quantity=95, checked_by="checker-001")
        adjusted_events = [e for e in item._events if isinstance(e, StockAdjusted)]
        assert len(adjusted_events) == 1
        event = adjusted_events[0]
        assert event.adjustment_type == AdjustmentType.COUNT.value
        assert event.quantity_change == -5

    def test_stock_check_no_discrepancy_no_adjustment(self):
        item = _make_item(initial_quantity=100)
        item.record_stock_check(counted_quantity=100, checked_by="checker-001")
        adjusted_events = [e for e in item._events if isinstance(e, StockAdjusted)]
        assert len(adjusted_events) == 0

    def test_stock_check_updates_last_stock_check(self):
        item = _make_item(initial_quantity=100)
        item.record_stock_check(counted_quantity=100, checked_by="checker-001")
        assert item.last_stock_check is not None
