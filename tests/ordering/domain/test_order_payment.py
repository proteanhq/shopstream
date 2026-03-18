"""Tests for order payment lifecycle."""

from protean.testing import given

from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.events import PaymentFailed, PaymentPending, PaymentSucceeded
from ordering.order.order import Order, OrderStatus
from ordering.order.payment import RecordPaymentFailure, RecordPaymentPending, RecordPaymentSuccess

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


def _confirmed_result():
    result = given(Order).process(CreateOrder(**CREATE_ORDER_ARGS))
    order_id = str(result.aggregate.id)
    result = result.process(ConfirmOrder(order_id=order_id))
    return result, order_id


class TestRecordPaymentPending:
    def test_transitions_to_payment_pending(self):
        result, order_id = _confirmed_result()
        result = result.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card")
        )
        assert result.status == OrderStatus.PAYMENT_PENDING.value

    def test_sets_payment_info(self):
        result, order_id = _confirmed_result()
        result = result.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card")
        )
        assert result.aggregate.payment_id == "pay-001"
        assert result.aggregate.payment_method == "credit_card"
        assert result.aggregate.payment_status == "pending"

    def test_raises_event(self):
        result, order_id = _confirmed_result()
        result = result.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card")
        )
        assert len(result.events) == 1
        assert PaymentPending in result.events
        event = result.events[PaymentPending]
        assert event.payment_id == "pay-001"


class TestRecordPaymentSuccess:
    def test_transitions_to_paid(self):
        result, order_id = _confirmed_result()
        result = result.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card")
        ).process(
            RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=50.0, payment_method="credit_card")
        )
        assert result.status == OrderStatus.PAID.value

    def test_sets_payment_status(self):
        result, order_id = _confirmed_result()
        result = result.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card")
        ).process(
            RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=50.0, payment_method="credit_card")
        )
        assert result.aggregate.payment_status == "succeeded"

    def test_raises_event(self):
        result, order_id = _confirmed_result()
        result = result.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="cc")
        ).process(RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=50.0, payment_method="cc"))
        assert len(result.events) == 1
        assert PaymentSucceeded in result.events
        event = result.events[PaymentSucceeded]
        assert event.amount == 50.0

    def test_cannot_pay_from_created(self):
        result = given(Order).process(
            CreateOrder(
                customer_id="cust-001",
                items=[
                    {
                        "product_id": "p1",
                        "variant_id": "v1",
                        "sku": "S1",
                        "title": "T",
                        "quantity": 1,
                        "unit_price": 10.0,
                    }
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
        result = result.process(
            RecordPaymentSuccess(order_id=order_id, payment_id="pay-001", amount=10.0, payment_method="cc")
        )
        assert result.rejected


class TestRecordPaymentFailure:
    def test_returns_to_confirmed(self):
        result, order_id = _confirmed_result()
        result = result.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="cc")
        ).process(RecordPaymentFailure(order_id=order_id, payment_id="pay-001", reason="Card declined"))
        assert result.status == OrderStatus.CONFIRMED.value

    def test_sets_payment_status_to_failed(self):
        result, order_id = _confirmed_result()
        result = result.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="cc")
        ).process(RecordPaymentFailure(order_id=order_id, payment_id="pay-001", reason="Insufficient funds"))
        assert result.aggregate.payment_status == "failed"

    def test_raises_event(self):
        result, order_id = _confirmed_result()
        result = result.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="cc")
        ).process(RecordPaymentFailure(order_id=order_id, payment_id="pay-001", reason="Declined"))
        assert len(result.events) == 1
        assert PaymentFailed in result.events
        event = result.events[PaymentFailed]
        assert event.reason == "Declined"

    def test_can_retry_after_failure(self):
        result, order_id = _confirmed_result()
        result = (
            result.process(RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="cc"))
            .process(RecordPaymentFailure(order_id=order_id, payment_id="pay-001", reason="Declined"))
            # Now at CONFIRMED again — can retry
            .process(RecordPaymentPending(order_id=order_id, payment_id="pay-002", payment_method="debit"))
        )
        assert result.status == OrderStatus.PAYMENT_PENDING.value
