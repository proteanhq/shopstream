"""Tests for order confirmation."""

from protean.testing import given

from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.events import OrderConfirmed
from ordering.order.order import Order, OrderStatus
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess

CREATE_ORDER_ARGS = {
    "customer_id": "cust-001",
    "items": [{"product_id": "p1", "variant_id": "v1", "sku": "S1", "title": "T", "quantity": 1, "unit_price": 10.0}],
    "shipping_address": {"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
    "billing_address": {"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
    "subtotal": 10.0,
    "shipping_cost": 0.0,
    "tax_total": 0.0,
    "discount_total": 0.0,
    "grand_total": 10.0,
    "currency": "USD",
}


class TestConfirmOrder:
    def test_confirm_transitions_to_confirmed(self):
        result = given(Order).process(CreateOrder(**CREATE_ORDER_ARGS))
        order_id = str(result.aggregate.id)
        result = result.process(ConfirmOrder(order_id=order_id))
        assert result.status == OrderStatus.CONFIRMED.value

    def test_confirm_raises_event(self):
        result = given(Order).process(CreateOrder(**CREATE_ORDER_ARGS))
        order_id = str(result.aggregate.id)
        result = result.process(ConfirmOrder(order_id=order_id))
        assert len(result.events) == 1
        assert OrderConfirmed in result.events
        event = result.events[OrderConfirmed]
        assert event.order_id == order_id
        assert event.confirmed_at is not None

    def test_confirm_updates_timestamp(self):
        result = given(Order).process(CreateOrder(**CREATE_ORDER_ARGS))
        original_updated = result.aggregate.updated_at
        order_id = str(result.aggregate.id)
        result = result.process(ConfirmOrder(order_id=order_id))
        assert result.aggregate.updated_at >= original_updated

    def test_cannot_confirm_from_paid(self):
        result = given(Order).process(CreateOrder(**CREATE_ORDER_ARGS))
        order_id = str(result.aggregate.id)
        result = result.process(ConfirmOrder(order_id=order_id))
        result = result.process(RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="cc"))
        result = result.process(
            RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=10.0, payment_method="cc")
        )
        result = result.process(ConfirmOrder(order_id=order_id))
        assert result.rejected
