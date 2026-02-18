"""Tests for order cancellation and refund."""

import pytest
from ordering.order.events import OrderCancelled, OrderRefunded
from ordering.order.order import Order, OrderStatus
from protean.exceptions import ValidationError


def _make_order():
    return Order.create(
        customer_id="cust-001",
        items_data=[
            {"product_id": "p1", "variant_id": "v1", "sku": "S1", "title": "T", "quantity": 1, "unit_price": 50.0}
        ],
        shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        pricing={"subtotal": 50.0, "grand_total": 50.0},
    )


class TestCancelOrder:
    def test_cancel_from_created(self):
        order = _make_order()
        order._events.clear()
        order.cancel("Changed mind", "Customer")
        assert order.status == OrderStatus.CANCELLED.value

    def test_cancel_stores_reason_and_actor(self):
        order = _make_order()
        order.cancel("Duplicate order", "Admin")
        assert order.cancellation_reason == "Duplicate order"
        assert order.cancelled_by == "Admin"

    def test_cancel_raises_event(self):
        order = _make_order()
        order._events.clear()
        order.cancel("Changed mind", "Customer")
        assert len(order._events) == 1
        event = order._events[0]
        assert isinstance(event, OrderCancelled)
        assert event.reason == "Changed mind"
        assert event.cancelled_by == "Customer"

    def test_cancel_from_confirmed(self):
        order = _make_order()
        order.confirm()
        order._events.clear()
        order.cancel("Out of stock", "System")
        assert order.status == OrderStatus.CANCELLED.value

    def test_cancel_from_payment_pending(self):
        order = _make_order()
        order.confirm()
        order.record_payment_pending("pay-001", "cc")
        order._events.clear()
        order.cancel("Timeout", "System")
        assert order.status == OrderStatus.CANCELLED.value

    def test_cancel_from_paid(self):
        order = _make_order()
        order.confirm()
        order.record_payment_pending("pay-001", "cc")
        order.record_payment_success("pay-001", 50.0, "cc")
        order._events.clear()
        order.cancel("Buyer remorse", "Customer")
        assert order.status == OrderStatus.CANCELLED.value

    def test_cannot_cancel_from_shipped(self):
        order = _make_order()
        order.confirm()
        order.record_payment_pending("p", "cc")
        order.record_payment_success("p", 50.0, "cc")
        order.record_shipment("s", "c", "t")
        with pytest.raises(ValidationError):
            order.cancel("Too late", "Customer")

    def test_cannot_cancel_from_delivered(self):
        order = _make_order()
        order.confirm()
        order.record_payment_pending("p", "cc")
        order.record_payment_success("p", 50.0, "cc")
        order.record_shipment("s", "c", "t")
        order.record_delivery()
        with pytest.raises(ValidationError):
            order.cancel("Too late", "Customer")


class TestRefundOrder:
    def test_refund_cancelled_order(self):
        order = _make_order()
        order.cancel("Test", "System")
        order._events.clear()
        order.refund()
        assert order.status == OrderStatus.REFUNDED.value

    def test_refund_uses_grand_total_by_default(self):
        order = _make_order()
        order.cancel("Test", "System")
        order._events.clear()
        order.refund()
        event = order._events[0]
        assert event.refund_amount == 50.0

    def test_refund_with_custom_amount(self):
        order = _make_order()
        order.cancel("Test", "System")
        order._events.clear()
        order.refund(refund_amount=25.0)
        event = order._events[0]
        assert event.refund_amount == 25.0

    def test_refund_raises_event(self):
        order = _make_order()
        order.cancel("Test", "System")
        order._events.clear()
        order.refund()
        assert len(order._events) == 1
        assert isinstance(order._events[0], OrderRefunded)

    def test_cannot_refund_paid_order(self):
        order = _make_order()
        order.confirm()
        order.record_payment_pending("p", "cc")
        order.record_payment_success("p", 50.0, "cc")
        with pytest.raises(ValidationError):
            order.refund()

    def test_refunded_is_terminal(self):
        order = _make_order()
        order.cancel("Test", "System")
        order.refund()
        with pytest.raises(ValidationError):
            order.refund()
