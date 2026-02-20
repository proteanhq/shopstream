"""Application tests for payment webhook processing."""

from payments.payment.initiation import InitiatePayment
from payments.payment.payment import Payment, PaymentStatus
from payments.payment.webhook import ProcessPaymentWebhook
from protean import current_domain


def _create_payment():
    command = InitiatePayment(
        order_id="ord-001",
        customer_id="cust-001",
        amount=59.99,
        currency="USD",
        payment_method_type="credit_card",
        last4="4242",
        idempotency_key="idem-wh-001",
    )
    return current_domain.process(command, asynchronous=False)


class TestWebhookSuccess:
    def test_success_webhook_sets_succeeded(self):
        payment_id = _create_payment()
        command = ProcessPaymentWebhook(
            payment_id=payment_id,
            gateway_transaction_id="txn-123",
            gateway_status="succeeded",
        )
        current_domain.process(command, asynchronous=False)
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert payment.status == PaymentStatus.SUCCEEDED.value

    def test_success_webhook_sets_gateway_info(self):
        payment_id = _create_payment()
        command = ProcessPaymentWebhook(
            payment_id=payment_id,
            gateway_transaction_id="txn-456",
            gateway_status="succeeded",
        )
        current_domain.process(command, asynchronous=False)
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert payment.gateway_info.gateway_transaction_id == "txn-456"


class TestWebhookFailure:
    def test_failure_webhook_sets_failed(self):
        payment_id = _create_payment()
        command = ProcessPaymentWebhook(
            payment_id=payment_id,
            gateway_status="failed",
            failure_reason="Insufficient funds",
        )
        current_domain.process(command, asynchronous=False)
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert payment.status == PaymentStatus.FAILED.value
