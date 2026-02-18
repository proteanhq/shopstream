"""Tests for order fulfillment — processing, shipment, delivery."""

import pytest
from ordering.order.events import OrderDelivered, OrderPartiallyShipped, OrderProcessing, OrderShipped
from ordering.order.order import ItemStatus, Order, OrderStatus
from protean.exceptions import ValidationError


def _make_paid_order():
    order = Order.create(
        customer_id="cust-001",
        items_data=[
            {
                "product_id": "p1",
                "variant_id": "v1",
                "sku": "S1",
                "title": "Product 1",
                "quantity": 1,
                "unit_price": 25.0,
            },
            {
                "product_id": "p2",
                "variant_id": "v2",
                "sku": "S2",
                "title": "Product 2",
                "quantity": 1,
                "unit_price": 25.0,
            },
        ],
        shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        pricing={"subtotal": 50.0, "grand_total": 50.0},
    )
    order.confirm()
    order.record_payment_pending("pay-001", "cc")
    order.record_payment_success("pay-001", 50.0, "cc")
    order._events.clear()
    return order


class TestMarkProcessing:
    def test_transitions_to_processing(self):
        order = _make_paid_order()
        order.mark_processing()
        assert order.status == OrderStatus.PROCESSING.value

    def test_raises_event(self):
        order = _make_paid_order()
        order.mark_processing()
        assert len(order._events) == 1
        assert isinstance(order._events[0], OrderProcessing)

    def test_cannot_process_from_created(self):
        order = Order.create(
            customer_id="c",
            items_data=[
                {"product_id": "p", "variant_id": "v", "sku": "S", "title": "T", "quantity": 1, "unit_price": 10.0}
            ],
            shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
            billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
            pricing={"subtotal": 10.0, "grand_total": 10.0},
        )
        with pytest.raises(ValidationError):
            order.mark_processing()


class TestRecordShipment:
    def test_transitions_to_shipped(self):
        order = _make_paid_order()
        order.record_shipment("ship-001", "FedEx", "TRACK-001")
        assert order.status == OrderStatus.SHIPPED.value

    def test_sets_shipment_info(self):
        order = _make_paid_order()
        order.record_shipment("ship-001", "UPS", "1Z999", estimated_delivery="2026-03-01")
        assert order.carrier == "UPS"
        assert order.tracking_number == "1Z999"
        assert order.estimated_delivery == "2026-03-01"

    def test_updates_item_statuses(self):
        order = _make_paid_order()
        order.record_shipment("ship-001", "FedEx", "TRACK-001")
        for item in order.items:
            assert item.item_status == ItemStatus.SHIPPED.value

    def test_raises_event(self):
        order = _make_paid_order()
        order.record_shipment("ship-001", "FedEx", "TRACK-001")
        assert len(order._events) == 1
        event = order._events[0]
        assert isinstance(event, OrderShipped)
        assert event.carrier == "FedEx"

    def test_ship_from_processing(self):
        order = _make_paid_order()
        order.mark_processing()
        order._events.clear()
        order.record_shipment("ship-001", "FedEx", "T")
        assert order.status == OrderStatus.SHIPPED.value


class TestRecordPartialShipment:
    def test_transitions_to_partially_shipped(self):
        order = _make_paid_order()
        order.mark_processing()
        order._events.clear()
        item_id = str(order.items[0].id)
        order.record_partial_shipment("ship-001", "FedEx", "TRACK-P", [item_id])
        assert order.status == OrderStatus.PARTIALLY_SHIPPED.value

    def test_only_shipped_items_updated(self):
        order = _make_paid_order()
        order.mark_processing()
        order._events.clear()
        item_id = str(order.items[0].id)
        order.record_partial_shipment("ship-001", "FedEx", "TRACK-P", [item_id])
        assert order.items[0].item_status == ItemStatus.SHIPPED.value
        assert order.items[1].item_status == ItemStatus.PENDING.value

    def test_raises_event(self):
        order = _make_paid_order()
        order.mark_processing()
        order._events.clear()
        item_id = str(order.items[0].id)
        order.record_partial_shipment("ship-001", "FedEx", "T", [item_id])
        assert len(order._events) == 1
        assert isinstance(order._events[0], OrderPartiallyShipped)

    def test_cannot_partial_ship_from_paid(self):
        order = _make_paid_order()
        with pytest.raises(ValidationError):
            order.record_partial_shipment("s", "c", "t", ["id"])


class TestRecordDelivery:
    def test_transitions_to_delivered(self):
        order = _make_paid_order()
        order.record_shipment("ship-001", "FedEx", "TRACK-001")
        order._events.clear()
        order.record_delivery()
        assert order.status == OrderStatus.DELIVERED.value

    def test_updates_item_statuses(self):
        order = _make_paid_order()
        order.record_shipment("ship-001", "FedEx", "TRACK-001")
        order._events.clear()
        order.record_delivery()
        for item in order.items:
            assert item.item_status == ItemStatus.DELIVERED.value

    def test_raises_event(self):
        order = _make_paid_order()
        order.record_shipment("ship-001", "FedEx", "TRACK-001")
        order._events.clear()
        order.record_delivery()
        assert len(order._events) == 1
        assert isinstance(order._events[0], OrderDelivered)
