"""Tests for order cancellation and refund."""

from protean.testing import given

from ordering.order.cancellation import CancelOrder, RefundOrder
from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.events import OrderCancelled, OrderRefunded
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


def _created_result():
    result = given(Order).process(CreateOrder(**CREATE_ORDER_ARGS))
    return result, str(result.aggregate.id)


class TestCancelOrder:
    def test_cancel_from_created(self):
        result, order_id = _created_result()
        result = result.process(CancelOrder(order_id=order_id, reason="Changed mind", cancelled_by="Customer"))
        assert result.status == OrderStatus.CANCELLED.value

    def test_cancel_stores_reason_and_actor(self):
        result, order_id = _created_result()
        result = result.process(CancelOrder(order_id=order_id, reason="Duplicate order", cancelled_by="Admin"))
        assert result.aggregate.cancellation_reason == "Duplicate order"
        assert result.aggregate.cancelled_by == "Admin"

    def test_cancel_raises_event(self):
        result, order_id = _created_result()
        result = result.process(CancelOrder(order_id=order_id, reason="Changed mind", cancelled_by="Customer"))
        assert len(result.events) == 1
        assert OrderCancelled in result.events
        event = result.events[OrderCancelled]
        assert event.reason == "Changed mind"
        assert event.cancelled_by == "Customer"

    def test_cancel_from_confirmed(self):
        result, order_id = _created_result()
        result = result.process(ConfirmOrder(order_id=order_id)).process(
            CancelOrder(order_id=order_id, reason="Out of stock", cancelled_by="System")
        )
        assert result.status == OrderStatus.CANCELLED.value

    def test_cancel_from_payment_pending(self):
        result, order_id = _created_result()
        result = (
            result.process(ConfirmOrder(order_id=order_id))
            .process(RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="cc"))
            .process(CancelOrder(order_id=order_id, reason="Timeout", cancelled_by="System"))
        )
        assert result.status == OrderStatus.CANCELLED.value

    def test_cancel_from_paid(self):
        result, order_id = _created_result()
        result = (
            result.process(ConfirmOrder(order_id=order_id))
            .process(RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="cc"))
            .process(RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=50.0, payment_method="cc"))
            .process(CancelOrder(order_id=order_id, reason="Buyer remorse", cancelled_by="Customer"))
        )
        assert result.status == OrderStatus.CANCELLED.value

    def test_cannot_cancel_from_shipped(self):
        result, order_id = _created_result()
        result = (
            result.process(ConfirmOrder(order_id=order_id))
            .process(RecordPaymentPending(order_id=order_id, payment_id="p", payment_method="cc"))
            .process(RecordPaymentSuccess(order_id=order_id, payment_id="p", amount=50.0, payment_method="cc"))
            .process(RecordShipment(order_id=order_id, shipment_id="s", carrier="c", tracking_number="t"))
        )
        result = result.process(CancelOrder(order_id=order_id, reason="Too late", cancelled_by="Customer"))
        assert result.rejected

    def test_cannot_cancel_from_delivered(self):
        result, order_id = _created_result()
        result = (
            result.process(ConfirmOrder(order_id=order_id))
            .process(RecordPaymentPending(order_id=order_id, payment_id="p", payment_method="cc"))
            .process(RecordPaymentSuccess(order_id=order_id, payment_id="p", amount=50.0, payment_method="cc"))
            .process(RecordShipment(order_id=order_id, shipment_id="s", carrier="c", tracking_number="t"))
            .process(RecordDelivery(order_id=order_id))
        )
        result = result.process(CancelOrder(order_id=order_id, reason="Too late", cancelled_by="Customer"))
        assert result.rejected


class TestRefundOrder:
    def test_refund_cancelled_order(self):
        result, order_id = _created_result()
        result = result.process(CancelOrder(order_id=order_id, reason="Test", cancelled_by="System")).process(
            RefundOrder(order_id=order_id)
        )
        assert result.status == OrderStatus.REFUNDED.value

    def test_refund_uses_grand_total_by_default(self):
        result, order_id = _created_result()
        result = result.process(CancelOrder(order_id=order_id, reason="Test", cancelled_by="System")).process(
            RefundOrder(order_id=order_id)
        )
        event = result.events[OrderRefunded]
        assert event.refund_amount == 50.0

    def test_refund_with_custom_amount(self):
        result, order_id = _created_result()
        result = result.process(CancelOrder(order_id=order_id, reason="Test", cancelled_by="System")).process(
            RefundOrder(order_id=order_id, refund_amount=25.0)
        )
        event = result.events[OrderRefunded]
        assert event.refund_amount == 25.0

    def test_refund_raises_event(self):
        result, order_id = _created_result()
        result = result.process(CancelOrder(order_id=order_id, reason="Test", cancelled_by="System")).process(
            RefundOrder(order_id=order_id)
        )
        assert len(result.events) == 1
        assert OrderRefunded in result.events

    def test_cannot_refund_paid_order(self):
        result, order_id = _created_result()
        result = (
            result.process(ConfirmOrder(order_id=order_id))
            .process(RecordPaymentPending(order_id=order_id, payment_id="p", payment_method="cc"))
            .process(RecordPaymentSuccess(order_id=order_id, payment_id="p", amount=50.0, payment_method="cc"))
        )
        result = result.process(RefundOrder(order_id=order_id))
        assert result.rejected

    def test_refunded_is_idempotent(self):
        result, order_id = _created_result()
        result = (
            result.process(CancelOrder(order_id=order_id, reason="Test", cancelled_by="System"))
            .process(RefundOrder(order_id=order_id))
            .process(RefundOrder(order_id=order_id))  # Idempotent — self-transition allowed
        )
        assert result.status == OrderStatus.REFUNDED.value
