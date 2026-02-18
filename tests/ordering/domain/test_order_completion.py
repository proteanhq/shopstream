"""Tests for order completion."""

import pytest
from ordering.order.events import OrderCompleted
from ordering.order.order import Order, OrderStatus
from protean.exceptions import ValidationError


def _make_delivered_order():
    order = Order.create(
        customer_id="cust-001",
        items_data=[
            {"product_id": "p1", "variant_id": "v1", "sku": "S1", "title": "T", "quantity": 1, "unit_price": 50.0}
        ],
        shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        pricing={"subtotal": 50.0, "grand_total": 50.0},
    )
    order.confirm()
    order.record_payment_pending("pay-001", "cc")
    order.record_payment_success("pay-001", 50.0, "cc")
    order.record_shipment("ship-001", "FedEx", "TRACK-001")
    order.record_delivery()
    order._events.clear()
    return order


class TestCompleteOrder:
    def test_transitions_to_completed(self):
        order = _make_delivered_order()
        order.complete()
        assert order.status == OrderStatus.COMPLETED.value

    def test_raises_event(self):
        order = _make_delivered_order()
        order.complete()
        assert len(order._events) == 1
        event = order._events[0]
        assert isinstance(event, OrderCompleted)
        assert event.completed_at is not None

    def test_completed_is_terminal(self):
        order = _make_delivered_order()
        order.complete()
        with pytest.raises(ValidationError):
            order.complete()

    def test_cannot_complete_from_shipped(self):
        order = Order.create(
            customer_id="c",
            items_data=[
                {"product_id": "p", "variant_id": "v", "sku": "S", "title": "T", "quantity": 1, "unit_price": 10.0}
            ],
            shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
            billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
            pricing={"subtotal": 10.0, "grand_total": 10.0},
        )
        order.confirm()
        order.record_payment_pending("p", "cc")
        order.record_payment_success("p", 10.0, "cc")
        order.record_shipment("s", "c", "t")
        with pytest.raises(ValidationError):
            order.complete()
