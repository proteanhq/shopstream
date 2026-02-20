"""Application tests for payment retry command."""

from payments.payment.initiation import InitiatePayment
from payments.payment.payment import Payment, PaymentStatus
from payments.payment.retry import RetryPayment
from payments.payment.webhook import ProcessPaymentWebhook
from protean import current_domain


def _create_failed_payment():
    payment_id = current_domain.process(
        InitiatePayment(
            order_id="ord-001",
            customer_id="cust-001",
            amount=59.99,
            currency="USD",
            payment_method_type="credit_card",
            last4="4242",
            idempotency_key="idem-retry-001",
        ),
        asynchronous=False,
    )
    current_domain.process(
        ProcessPaymentWebhook(
            payment_id=payment_id,
            gateway_status="failed",
            failure_reason="Card declined",
        ),
        asynchronous=False,
    )
    return payment_id


class TestRetryPaymentFlow:
    def test_retry_sets_status_pending(self):
        payment_id = _create_failed_payment()
        current_domain.process(
            RetryPayment(payment_id=payment_id),
            asynchronous=False,
        )
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert payment.status == PaymentStatus.PENDING.value

    def test_retry_increments_attempt_count(self):
        payment_id = _create_failed_payment()
        current_domain.process(
            RetryPayment(payment_id=payment_id),
            asynchronous=False,
        )
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert payment.attempt_count == 2
