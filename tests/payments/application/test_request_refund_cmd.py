"""Application tests for refund request command."""

from payments.payment.initiation import InitiatePayment
from payments.payment.payment import Payment
from payments.payment.refund import RequestRefund
from payments.payment.webhook import ProcessPaymentWebhook
from protean import current_domain


def _create_succeeded_payment():
    payment_id = current_domain.process(
        InitiatePayment(
            order_id="ord-001",
            customer_id="cust-001",
            amount=100.00,
            currency="USD",
            payment_method_type="credit_card",
            last4="4242",
            idempotency_key="idem-ref-001",
        ),
        asynchronous=False,
    )
    current_domain.process(
        ProcessPaymentWebhook(
            payment_id=payment_id,
            gateway_transaction_id="txn-123",
            gateway_status="succeeded",
        ),
        asynchronous=False,
    )
    return payment_id


class TestRequestRefundFlow:
    def test_request_refund_adds_refund(self):
        payment_id = _create_succeeded_payment()
        current_domain.process(
            RequestRefund(
                payment_id=payment_id,
                amount=50.00,
                reason="Defective item",
            ),
            asynchronous=False,
        )
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert len(payment.refunds) == 1
        assert payment.refunds[0].amount == 50.00
