"""Application tests for OrderReturnedSubscriber — Payments reacts to Ordering stream.

Tests the subscriber ACL pattern: raw dict payloads are filtered by event type
and translated into RequestRefund commands.
"""

from datetime import UTC, datetime

from protean import current_domain

from payments.payment.initiation import InitiatePayment
from payments.payment.ordering_subscriber import OrderReturnedSubscriber
from payments.payment.payment import Payment
from payments.payment.webhook import ProcessPaymentWebhook
from payments.projections.payment_status import PaymentStatusView


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


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


class TestOrderReturnedSubscriber:
    def test_initiates_refund_for_succeeded_payment(self):
        """When a succeeded payment exists, subscriber should initiate a refund."""
        order_id = "ord-refund-001"
        payment_id = _create_succeeded_payment(order_id)

        # Verify payment is succeeded
        payment_view = current_domain.repository_for(PaymentStatusView).get(payment_id)
        assert payment_view.status == "Succeeded"

        # Handle the order returned message
        payload = _build_message(
            "Ordering.OrderReturned.v1",
            {
                "order_id": order_id,
                "returned_at": datetime.now(UTC).isoformat(),
            },
        )

        subscriber = OrderReturnedSubscriber()
        subscriber(payload)

        # Verify that a refund was initiated
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert len(payment.refunds) == 1
        refund = payment.refunds[0]
        assert refund.reason == f"Order returned: {order_id}"

    def test_no_payment_found_is_noop(self):
        """When no succeeded payment exists for the order, subscriber logs and returns."""
        payload = _build_message(
            "Ordering.OrderReturned.v1",
            {
                "order_id": "ord-no-payment",
                "returned_at": datetime.now(UTC).isoformat(),
            },
        )

        subscriber = OrderReturnedSubscriber()
        # Should not raise
        subscriber(payload)

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
        payload = _build_message(
            "Ordering.OrderReturned.v1",
            {
                "order_id": order_id,
                "returned_at": datetime.now(UTC).isoformat(),
            },
        )

        subscriber = OrderReturnedSubscriber()
        subscriber(payload)

        # Payment should have no refunds
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert len(payment.refunds) == 0

    def test_ignores_non_order_returned_events(self):
        """Non-OrderReturned events on the ordering stream are ignored."""
        order_id = "ord-cancelled-not-returned"
        _create_succeeded_payment(order_id, idempotency_key="idem-cancel-test")

        payload = _build_message(
            "Ordering.OrderCancelled.v1",
            {
                "order_id": order_id,
                "reason": "Customer request",
                "cancelled_by": "customer",
                "cancelled_at": datetime.now(UTC).isoformat(),
            },
        )

        subscriber = OrderReturnedSubscriber()
        subscriber(payload)

        # No refund should have been initiated
        payment_records = (
            current_domain.view_for(PaymentStatusView).query.filter(order_id=order_id, status="Succeeded").all().items
        )
        if payment_records:
            payment = current_domain.repository_for(Payment).get(str(payment_records[0].payment_id))
            assert len(payment.refunds) == 0

    def test_ignores_payload_without_metadata(self):
        """Payloads missing metadata entirely are ignored."""
        order_id = "ord-no-meta"
        _create_succeeded_payment(order_id, idempotency_key="idem-no-meta")

        payload = {
            "data": {
                "order_id": order_id,
                "returned_at": datetime.now(UTC).isoformat(),
            }
        }

        subscriber = OrderReturnedSubscriber()
        subscriber(payload)

        # No refund should have been initiated
        payment_records = (
            current_domain.view_for(PaymentStatusView).query.filter(order_id=order_id, status="Succeeded").all().items
        )
        if payment_records:
            payment = current_domain.repository_for(Payment).get(str(payment_records[0].payment_id))
            assert len(payment.refunds) == 0
