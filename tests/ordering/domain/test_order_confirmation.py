"""Tests for order confirmation."""

import pytest
from ordering.order.events import OrderConfirmed
from ordering.order.order import Order, OrderStatus
from protean.exceptions import ValidationError


def _make_order():
    return Order.create(
        customer_id="cust-001",
        items_data=[
            {"product_id": "p1", "variant_id": "v1", "sku": "S1", "title": "T", "quantity": 1, "unit_price": 10.0}
        ],
        shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
        pricing={"subtotal": 10.0, "grand_total": 10.0},
    )


class TestConfirmOrder:
    def test_confirm_transitions_to_confirmed(self):
        order = _make_order()
        order._events.clear()
        order.confirm()
        assert order.status == OrderStatus.CONFIRMED.value

    def test_confirm_raises_event(self):
        order = _make_order()
        order._events.clear()
        order.confirm()
        assert len(order._events) == 1
        event = order._events[0]
        assert isinstance(event, OrderConfirmed)
        assert event.order_id == str(order.id)
        assert event.confirmed_at is not None

    def test_confirm_updates_timestamp(self):
        order = _make_order()
        original_updated = order.updated_at
        order.confirm()
        assert order.updated_at >= original_updated

    def test_cannot_confirm_from_paid(self):
        order = _make_order()
        order.confirm()
        order.record_payment_pending("pay-001", "cc")
        order.record_payment_success("pay-001", 10.0, "cc")
        with pytest.raises(ValidationError):
            order.confirm()
