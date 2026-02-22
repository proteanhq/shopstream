"""Tests for stock event structure and field presence."""

from datetime import UTC, datetime

from inventory.stock.events import (
    DamagedStockWrittenOff,
    LowStockDetected,
    ReservationConfirmed,
    ReservationReleased,
    StockAdjusted,
    StockCheckRecorded,
    StockCommitted,
    StockInitialized,
    StockMarkedDamaged,
    StockReceived,
    StockReserved,
    StockReturned,
)


class TestStockInitializedEvent:
    def test_fields(self):
        now = datetime.now(UTC)
        event = StockInitialized(
            inventory_item_id="inv-001",
            product_id="prod-001",
            variant_id="var-001",
            warehouse_id="wh-001",
            sku="SKU-001",
            initial_quantity=100,
            reorder_point=10,
            reorder_quantity=50,
            initialized_at=now,
        )
        assert event.inventory_item_id == "inv-001"
        assert event.product_id == "prod-001"
        assert event.variant_id == "var-001"
        assert event.warehouse_id == "wh-001"
        assert event.sku == "SKU-001"
        assert event.initial_quantity == 100
        assert event.reorder_point == 10
        assert event.reorder_quantity == 50
        assert event.initialized_at == now


class TestStockReceivedEvent:
    def test_fields(self):
        now = datetime.now(UTC)
        event = StockReceived(
            inventory_item_id="inv-001",
            quantity=50,
            previous_on_hand=100,
            new_on_hand=150,
            new_available=140,
            reference="PO-12345",
            received_at=now,
        )
        assert event.inventory_item_id == "inv-001"
        assert event.quantity == 50
        assert event.previous_on_hand == 100
        assert event.new_on_hand == 150
        assert event.new_available == 140
        assert event.reference == "PO-12345"
        assert event.received_at == now


class TestStockReservedEvent:
    def test_fields(self):
        now = datetime.now(UTC)
        event = StockReserved(
            inventory_item_id="inv-001",
            reservation_id="res-001",
            order_id="ord-001",
            quantity=5,
            previous_available=100,
            new_available=95,
            reserved_at=now,
            expires_at=now,
        )
        assert event.inventory_item_id == "inv-001"
        assert event.reservation_id == "res-001"
        assert event.order_id == "ord-001"
        assert event.quantity == 5
        assert event.previous_available == 100
        assert event.new_available == 95
        assert event.reserved_at == now
        assert event.expires_at == now


class TestReservationReleasedEvent:
    def test_fields(self):
        now = datetime.now(UTC)
        event = ReservationReleased(
            inventory_item_id="inv-001",
            reservation_id="res-001",
            order_id="ord-001",
            quantity=5,
            reason="order_cancelled",
            previous_available=95,
            new_available=100,
            released_at=now,
        )
        assert event.inventory_item_id == "inv-001"
        assert event.reservation_id == "res-001"
        assert event.quantity == 5
        assert event.reason == "order_cancelled"
        assert event.previous_available == 95
        assert event.new_available == 100
        assert event.released_at == now


class TestReservationConfirmedEvent:
    def test_fields(self):
        now = datetime.now(UTC)
        event = ReservationConfirmed(
            inventory_item_id="inv-001",
            reservation_id="res-001",
            order_id="ord-001",
            quantity=5,
            confirmed_at=now,
        )
        assert event.inventory_item_id == "inv-001"
        assert event.reservation_id == "res-001"
        assert event.order_id == "ord-001"
        assert event.quantity == 5
        assert event.confirmed_at == now


class TestStockCommittedEvent:
    def test_fields(self):
        now = datetime.now(UTC)
        event = StockCommitted(
            inventory_item_id="inv-001",
            reservation_id="res-001",
            order_id="ord-001",
            quantity=5,
            previous_on_hand=100,
            new_on_hand=95,
            previous_reserved=10,
            new_reserved=5,
            committed_at=now,
        )
        assert event.inventory_item_id == "inv-001"
        assert event.reservation_id == "res-001"
        assert event.quantity == 5
        assert event.previous_on_hand == 100
        assert event.new_on_hand == 95
        assert event.previous_reserved == 10
        assert event.new_reserved == 5
        assert event.committed_at == now


class TestStockAdjustedEvent:
    def test_fields(self):
        now = datetime.now(UTC)
        event = StockAdjusted(
            inventory_item_id="inv-001",
            product_id="prod-001",
            adjustment_type="Count",
            quantity_change=-5,
            reason="Physical count discrepancy",
            adjusted_by="manager-001",
            previous_on_hand=100,
            new_on_hand=95,
            new_available=85,
            adjusted_at=now,
        )
        assert event.inventory_item_id == "inv-001"
        assert event.adjustment_type == "Count"
        assert event.quantity_change == -5
        assert event.reason == "Physical count discrepancy"
        assert event.adjusted_by == "manager-001"
        assert event.previous_on_hand == 100
        assert event.new_on_hand == 95
        assert event.new_available == 85


class TestStockMarkedDamagedEvent:
    def test_fields(self):
        now = datetime.now(UTC)
        event = StockMarkedDamaged(
            inventory_item_id="inv-001",
            product_id="prod-001",
            quantity=3,
            reason="Water damage",
            previous_on_hand=100,
            new_on_hand=97,
            previous_damaged=0,
            new_damaged=3,
            new_available=87,
            marked_at=now,
        )
        assert event.inventory_item_id == "inv-001"
        assert event.quantity == 3
        assert event.reason == "Water damage"
        assert event.previous_on_hand == 100
        assert event.new_on_hand == 97
        assert event.previous_damaged == 0
        assert event.new_damaged == 3
        assert event.new_available == 87


class TestDamagedStockWrittenOffEvent:
    def test_fields(self):
        now = datetime.now(UTC)
        event = DamagedStockWrittenOff(
            inventory_item_id="inv-001",
            product_id="prod-001",
            quantity=3,
            approved_by="manager-001",
            previous_damaged=5,
            new_damaged=2,
            written_off_at=now,
        )
        assert event.inventory_item_id == "inv-001"
        assert event.quantity == 3
        assert event.approved_by == "manager-001"
        assert event.previous_damaged == 5
        assert event.new_damaged == 2
        assert event.written_off_at == now


class TestStockReturnedEvent:
    def test_fields(self):
        now = datetime.now(UTC)
        event = StockReturned(
            inventory_item_id="inv-001",
            quantity=2,
            order_id="ord-001",
            previous_on_hand=95,
            new_on_hand=97,
            new_available=87,
            returned_at=now,
        )
        assert event.inventory_item_id == "inv-001"
        assert event.quantity == 2
        assert event.order_id == "ord-001"
        assert event.previous_on_hand == 95
        assert event.new_on_hand == 97
        assert event.new_available == 87


class TestStockCheckRecordedEvent:
    def test_fields(self):
        now = datetime.now(UTC)
        event = StockCheckRecorded(
            inventory_item_id="inv-001",
            counted_quantity=98,
            expected_quantity=100,
            discrepancy=-2,
            checked_by="checker-001",
            checked_at=now,
        )
        assert event.inventory_item_id == "inv-001"
        assert event.counted_quantity == 98
        assert event.expected_quantity == 100
        assert event.discrepancy == -2
        assert event.checked_by == "checker-001"


class TestLowStockDetectedEvent:
    def test_fields(self):
        now = datetime.now(UTC)
        event = LowStockDetected(
            inventory_item_id="inv-001",
            product_id="prod-001",
            variant_id="var-001",
            sku="SKU-001",
            current_available=5,
            reorder_point=10,
            detected_at=now,
        )
        assert event.inventory_item_id == "inv-001"
        assert event.product_id == "prod-001"
        assert event.sku == "SKU-001"
        assert event.current_available == 5
        assert event.reorder_point == 10
