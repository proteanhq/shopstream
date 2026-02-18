"""Application tests for the payment flow including failure and retry."""

import json

from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.order import Order, OrderStatus
from ordering.order.payment import (
    RecordPaymentFailure,
    RecordPaymentPending,
    RecordPaymentSuccess,
)
from protean import current_domain


def _create_confirmed_order():
    order_id = current_domain.process(
        CreateOrder(
            customer_id="cust-001",
            items=json.dumps(
                [
                    {
                        "product_id": "p1",
                        "variant_id": "v1",
                        "sku": "S1",
                        "title": "Item",
                        "quantity": 1,
                        "unit_price": 100.0,
                    }
                ]
            ),
            shipping_address=json.dumps(
                {"street": "1 St", "city": "C", "state": "S", "postal_code": "00000", "country": "US"}
            ),
            billing_address=json.dumps(
                {"street": "1 St", "city": "C", "state": "S", "postal_code": "00000", "country": "US"}
            ),
            subtotal=100.0,
            grand_total=110.0,
        ),
        asynchronous=False,
    )
    current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)
    return order_id


class TestPaymentPendingFlow:
    def test_payment_pending_persists(self):
        order_id = _create_confirmed_order()
        current_domain.process(
            RecordPaymentPending(
                order_id=order_id,
                payment_id="pay-001",
                payment_method="credit_card",
            ),
            asynchronous=False,
        )
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PAYMENT_PENDING.value
        assert order.payment_method == "credit_card"


class TestPaymentSuccessFlow:
    def test_payment_success_persists(self):
        order_id = _create_confirmed_order()
        current_domain.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card"),
            asynchronous=False,
        )
        current_domain.process(
            RecordPaymentSuccess(
                order_id=order_id,
                payment_id="pay-001",
                amount=110.0,
                payment_method="credit_card",
            ),
            asynchronous=False,
        )
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PAID.value
        assert order.payment_status == "succeeded"


class TestPaymentFailureAndRetry:
    def test_failure_returns_to_confirmed(self):
        order_id = _create_confirmed_order()
        current_domain.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card"),
            asynchronous=False,
        )
        current_domain.process(
            RecordPaymentFailure(order_id=order_id, payment_id="pay-001", reason="Insufficient funds"),
            asynchronous=False,
        )
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CONFIRMED.value
        assert order.payment_status == "failed"

    def test_retry_after_failure(self):
        order_id = _create_confirmed_order()

        # First attempt — fails
        current_domain.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card"),
            asynchronous=False,
        )
        current_domain.process(
            RecordPaymentFailure(order_id=order_id, payment_id="pay-001", reason="Declined"),
            asynchronous=False,
        )

        # Retry — succeeds
        current_domain.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-002", payment_method="debit_card"),
            asynchronous=False,
        )
        current_domain.process(
            RecordPaymentSuccess(
                order_id=order_id,
                payment_id="pay-002",
                amount=110.0,
                payment_method="debit_card",
            ),
            asynchronous=False,
        )
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PAID.value
        assert order.payment_id == "pay-002"
