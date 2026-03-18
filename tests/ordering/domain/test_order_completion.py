"""Tests for order completion."""

from protean.testing import given

from ordering.order.completion import CompleteOrder
from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.events import OrderCompleted
from ordering.order.fulfillment import RecordDelivery, RecordShipment
from ordering.order.order import Order, OrderStatus
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess

CREATE_ORDER_ARGS = {
    "customer_id": "cust-001",
    "items": [{"product_id": "p1", "variant_id": "v1", "sku": "S1", "title": "T", "quantity": 1, "unit_price": 50.0}],
    "shipping_address": {"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
    "billing_address": {"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
    "subtotal": 50.0,
    "shipping_cost": 0.0,
    "tax_total": 0.0,
    "discount_total": 0.0,
    "grand_total": 50.0,
    "currency": "USD",
}


def _delivered_result():
    result = given(Order).process(CreateOrder(**CREATE_ORDER_ARGS))
    order_id = str(result.aggregate.id)
    result = (
        result.process(ConfirmOrder(order_id=order_id))
        .process(RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="cc"))
        .process(RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=50.0, payment_method="cc"))
        .process(
            RecordShipment(order_id=order_id, shipment_id="ship-001", carrier="FedEx", tracking_number="TRACK-001")
        )
        .process(RecordDelivery(order_id=order_id))
    )
    return result, order_id


class TestCompleteOrder:
    def test_transitions_to_completed(self):
        result, order_id = _delivered_result()
        result = result.process(CompleteOrder(order_id=order_id))
        assert result.status == OrderStatus.COMPLETED.value

    def test_raises_event(self):
        result, order_id = _delivered_result()
        result = result.process(CompleteOrder(order_id=order_id))
        assert len(result.events) == 1
        assert OrderCompleted in result.events
        event = result.events[OrderCompleted]
        assert event.completed_at is not None

    def test_completed_is_idempotent(self):
        result, order_id = _delivered_result()
        result = result.process(CompleteOrder(order_id=order_id))
        result = result.process(CompleteOrder(order_id=order_id))
        assert result.status == OrderStatus.COMPLETED.value

    def test_cannot_complete_from_shipped(self):
        result = given(Order).process(
            CreateOrder(
                customer_id="c",
                items=[
                    {"product_id": "p", "variant_id": "v", "sku": "S", "title": "T", "quantity": 1, "unit_price": 10.0}
                ],
                shipping_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
                billing_address={"street": "1 St", "city": "C", "postal_code": "00000", "country": "US"},
                subtotal=10.0,
                shipping_cost=0.0,
                tax_total=0.0,
                discount_total=0.0,
                grand_total=10.0,
                currency="USD",
            )
        )
        order_id = str(result.aggregate.id)
        result = (
            result.process(ConfirmOrder(order_id=order_id))
            .process(RecordPaymentPending(order_id=order_id, payment_id="p", payment_method="cc"))
            .process(RecordPaymentSuccess(order_id=order_id, payment_id="p", amount=10.0, payment_method="cc"))
            .process(RecordShipment(order_id=order_id, shipment_id="s", carrier="c", tracking_number="t"))
        )
        result = result.process(CompleteOrder(order_id=order_id))
        assert result.rejected
