"""Application tests for refund webhook processing command."""

from payments.payment.initiation import InitiatePayment
from payments.payment.payment import Payment, PaymentStatus, RefundStatus
from payments.payment.refund import ProcessRefundWebhook, RequestRefund
from payments.payment.webhook import ProcessPaymentWebhook
from protean import current_domain


def _create_payment_with_refund():
    payment_id = current_domain.process(
        InitiatePayment(
            order_id="ord-001",
            customer_id="cust-001",
            amount=100.00,
            currency="USD",
            payment_method_type="credit_card",
            last4="4242",
            idempotency_key="idem-refwh-001",
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
    current_domain.process(
        RequestRefund(
            payment_id=payment_id,
            amount=100.00,
            reason="Full refund",
        ),
        asynchronous=False,
    )
    payment = current_domain.repository_for(Payment).get(payment_id)
    refund_id = str(payment.refunds[0].id)
    return payment_id, refund_id


class TestRefundWebhookFlow:
    def test_complete_refund_sets_status(self):
        payment_id, refund_id = _create_payment_with_refund()
        current_domain.process(
            ProcessRefundWebhook(
                payment_id=payment_id,
                refund_id=refund_id,
                gateway_refund_id="gw-ref-001",
            ),
            asynchronous=False,
        )
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert payment.status == PaymentStatus.REFUNDED.value

    def test_complete_refund_updates_refund_entity(self):
        payment_id, refund_id = _create_payment_with_refund()
        current_domain.process(
            ProcessRefundWebhook(
                payment_id=payment_id,
                refund_id=refund_id,
                gateway_refund_id="gw-ref-001",
            ),
            asynchronous=False,
        )
        payment = current_domain.repository_for(Payment).get(payment_id)
        refund = payment.refunds[0]
        assert refund.status == RefundStatus.COMPLETED.value
        assert refund.gateway_refund_id == "gw-ref-001"
