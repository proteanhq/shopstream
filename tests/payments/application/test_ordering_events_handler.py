"""Application tests for OrderingPaymentEventHandler — Payments reacts to Ordering events.

Covers:
- on_order_returned with no payment: logs, no error
- on_order_returned with succeeded payment: initiates refund
- on_order_returned with failed payment: no refund initiated
"""

from datetime import UTC, datetime

from payments.payment.initiation import InitiatePayment
from payments.payment.ordering_events import OrderingPaymentEventHandler
from payments.payment.payment import Payment
from payments.payment.webhook import ProcessPaymentWebhook
from payments.projections.payment_status import PaymentStatusView
from protean import current_domain
from shared.events.ordering import OrderReturned


def _create_succeeded_payment(order_id, **overrides):
    """Create a payment and simulate gateway success."""
    defaults = {
        "order_id": order_id,
        "customer_id": "cust-001",
        "amount": 99.99,
        "currency": "USD",
        "payment_method_type": "credit_card",
        "last4": "4242",
        "idempotency_key": f"idem-{order_id}",
    }
    defaults.update(overrides)
    payment_id = current_domain.process(
        InitiatePayment(**defaults),
        asynchronous=False,
    )
    current_domain.process(
        ProcessPaymentWebhook(
            payment_id=payment_id,
            gateway_transaction_id=f"gw-txn-{order_id}",
            gateway_status="succeeded",
        ),
        asynchronous=False,
    )
    return payment_id


class TestOrderReturnedHandler:
    def test_no_payment_found_is_noop(self):
        """When no succeeded payment exists for the order, handler logs and returns."""
        handler = OrderingPaymentEventHandler()
        # Should not raise
        handler.on_order_returned(
            OrderReturned(
                order_id="ord-no-payment",
                customer_id="cust-001",
                returned_at=datetime.now(UTC),
            )
        )

    def test_initiates_refund_for_succeeded_payment(self):
        """When a succeeded payment exists, handler should initiate a refund."""
        order_id = "ord-refund-001"
        payment_id = _create_succeeded_payment(order_id)

        # Verify payment is succeeded
        payment_view = current_domain.repository_for(PaymentStatusView).get(payment_id)
        assert payment_view.status == "Succeeded"

        # Handle the order returned event
        handler = OrderingPaymentEventHandler()
        handler.on_order_returned(
            OrderReturned(
                order_id=order_id,
                customer_id="cust-001",
                returned_at=datetime.now(UTC),
            )
        )

        # Verify that a refund was initiated
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert len(payment.refunds) == 1
        refund = payment.refunds[0]
        assert refund.reason == f"Order returned: {order_id}"

    def test_no_refund_for_failed_payment(self):
        """When the payment for the order has failed, no refund should be initiated."""
        order_id = "ord-failed-pay"

        # Create a payment that fails
        payment_id = current_domain.process(
            InitiatePayment(
                order_id=order_id,
                customer_id="cust-failed-001",
                amount=50.0,
                currency="USD",
                payment_method_type="credit_card",
                last4="1111",
                idempotency_key="idem-failed-001",
            ),
            asynchronous=False,
        )

        # Simulate gateway webhook reporting failure
        current_domain.process(
            ProcessPaymentWebhook(
                payment_id=payment_id,
                gateway_transaction_id="gw-txn-fail",
                gateway_status="failed",
                failure_reason="Insufficient funds",
            ),
            asynchronous=False,
        )

        # Handle order returned — no succeeded payment, so no refund
        handler = OrderingPaymentEventHandler()
        handler.on_order_returned(
            OrderReturned(
                order_id=order_id,
                customer_id="cust-failed-001",
                returned_at=datetime.now(UTC),
            )
        )

        # Payment should have no refunds
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert len(payment.refunds) == 0
