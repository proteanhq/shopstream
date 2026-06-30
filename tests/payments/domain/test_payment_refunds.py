"""Tests for payment refund flows."""

from protean.testing import given

from payments.payment.events import RefundCompleted, RefundRequested
from payments.payment.initiation import InitiatePayment
from payments.payment.payment import Payment, PaymentStatus, RefundStatus
from payments.payment.refund import ProcessRefundWebhook, RequestRefund
from payments.payment.webhook import ProcessPaymentWebhook


def _initiate():
    return InitiatePayment(
        order_id="ord-001",
        customer_id="cust-001",
        amount=100.00,
        currency="USD",
        payment_method_type="credit_card",
        last4="4242",
        idempotency_key="idem-001",
    )


def _make_succeeded():
    result = given(Payment).process(_initiate())
    payment_id = str(result.aggregate.id)
    result = result.process(
        ProcessPaymentWebhook(
            payment_id=payment_id,
            gateway_transaction_id="txn-123",
            gateway_status="succeeded",
        )
    )
    return result, payment_id


class TestRequestRefund:
    def test_request_refund_adds_refund_entity(self):
        result, payment_id = _make_succeeded()
        result = result.process(RequestRefund(payment_id=payment_id, amount=50.00, reason="Defective product"))
        assert result.accepted
        assert len(result.aggregate.refunds) == 1
        refund = result.aggregate.refunds[0]
        assert refund.amount == 50.00
        assert refund.reason == "Defective product"
        assert refund.status == RefundStatus.REQUESTED.value

    def test_request_refund_raises_event(self):
        result, payment_id = _make_succeeded()
        result = result.process(RequestRefund(payment_id=payment_id, amount=50.00, reason="Defective"))
        assert len(result.events) == 1
        assert RefundRequested in result.events
        assert result.events[RefundRequested].amount == 50.00

    def test_request_refund_returns_refund_id(self):
        result, payment_id = _make_succeeded()
        result = result.process(RequestRefund(payment_id=payment_id, amount=50.00, reason="Test"))
        assert result.accepted
        assert len(result.aggregate.refunds) == 1
        assert result.aggregate.refunds[0].id is not None

    def test_cannot_refund_pending_payment(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = result.process(RequestRefund(payment_id=payment_id, amount=50.00, reason="Test"))
        assert result.rejected

    def test_cannot_refund_more_than_payment_amount(self):
        result, payment_id = _make_succeeded()
        result = result.process(RequestRefund(payment_id=payment_id, amount=150.00, reason="Test"))
        assert result.rejected


class TestCompleteRefund:
    def test_complete_refund_updates_refund_status(self):
        result, payment_id = _make_succeeded()
        result = result.process(RequestRefund(payment_id=payment_id, amount=50.00, reason="Test"))
        refund_id = str(result.aggregate.refunds[0].id)
        result = result.process(
            ProcessRefundWebhook(
                payment_id=payment_id,
                refund_id=refund_id,
                gateway_refund_id="ref-123",
            )
        )
        assert result.accepted
        refund = next(r for r in result.aggregate.refunds if str(r.id) == refund_id)
        assert refund.status == RefundStatus.COMPLETED.value
        assert refund.gateway_refund_id == "ref-123"

    def test_complete_refund_raises_event(self):
        result, payment_id = _make_succeeded()
        result = result.process(RequestRefund(payment_id=payment_id, amount=50.00, reason="Test"))
        refund_id = str(result.aggregate.refunds[0].id)
        result = result.process(
            ProcessRefundWebhook(
                payment_id=payment_id,
                refund_id=refund_id,
                gateway_refund_id="ref-123",
            )
        )
        assert len(result.events) == 1
        assert RefundCompleted in result.events
        assert result.events[RefundCompleted].amount == 50.00
        # customer_id is carried so downstream contexts (Loyalty clawback, Notifications) can react.
        assert result.events[RefundCompleted].customer_id == "cust-001"

    def test_partial_refund_sets_partially_refunded(self):
        result, payment_id = _make_succeeded()
        result = result.process(RequestRefund(payment_id=payment_id, amount=50.00, reason="Test"))
        refund_id = str(result.aggregate.refunds[0].id)
        result = result.process(
            ProcessRefundWebhook(
                payment_id=payment_id,
                refund_id=refund_id,
                gateway_refund_id="ref-123",
            )
        )
        assert result.status == PaymentStatus.PARTIALLY_REFUNDED.value
        assert result.total_refunded == 50.00

    def test_full_refund_sets_refunded(self):
        result, payment_id = _make_succeeded()
        result = result.process(RequestRefund(payment_id=payment_id, amount=100.00, reason="Test"))
        refund_id = str(result.aggregate.refunds[0].id)
        result = result.process(
            ProcessRefundWebhook(
                payment_id=payment_id,
                refund_id=refund_id,
                gateway_refund_id="ref-123",
            )
        )
        assert result.status == PaymentStatus.REFUNDED.value
        assert result.total_refunded == 100.00

    def test_complete_refund_with_invalid_refund_id(self):
        result, payment_id = _make_succeeded()
        result = result.process(
            ProcessRefundWebhook(
                payment_id=payment_id,
                refund_id="nonexistent",
                gateway_refund_id="ref-123",
            )
        )
        assert result.rejected
