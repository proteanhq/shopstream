"""Tests for payment state machine and amount guard invariants."""

import pytest
from protean.exceptions import ValidationError
from protean.testing import given

from payments.payment.initiation import InitiatePayment
from payments.payment.payment import MAX_PAYMENT_ATTEMPTS, Payment, PaymentStatus
from payments.payment.refund import ProcessRefundWebhook, RequestRefund
from payments.payment.retry import RetryPayment
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


def _succeed(result):
    payment_id = str(result.aggregate.id)
    return result.process(
        ProcessPaymentWebhook(
            payment_id=payment_id,
            gateway_transaction_id="txn-1",
            gateway_status="succeeded",
        )
    )


def _fail(result, reason="Declined"):
    payment_id = str(result.aggregate.id)
    return result.process(
        ProcessPaymentWebhook(
            payment_id=payment_id,
            gateway_status="failed",
            failure_reason=reason,
        )
    )


class TestPaymentStateMachine:
    def test_pending_to_succeeded(self):
        result = _succeed(given(Payment).process(_initiate()))
        assert result.accepted
        assert result.status == PaymentStatus.SUCCEEDED.value

    def test_pending_to_failed(self):
        result = _fail(given(Payment).process(_initiate()))
        assert result.accepted
        assert result.status == PaymentStatus.FAILED.value

    def test_failed_to_pending_via_retry(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = _fail(result)
        result = result.process(RetryPayment(payment_id=payment_id))
        assert result.accepted
        assert result.status == PaymentStatus.PENDING.value

    def test_cannot_succeed_from_failed(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = _fail(result)
        # Trying to succeed from failed state should be rejected
        result = result.process(
            ProcessPaymentWebhook(
                payment_id=payment_id,
                gateway_transaction_id="txn-1",
                gateway_status="succeeded",
            )
        )
        assert result.rejected

    def test_cannot_fail_from_succeeded(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = _succeed(result)
        result = result.process(
            ProcessPaymentWebhook(
                payment_id=payment_id,
                gateway_status="failed",
                failure_reason="Declined",
            )
        )
        assert result.rejected

    def test_cannot_retry_from_pending(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = result.process(RetryPayment(payment_id=payment_id))
        assert result.rejected

    def test_cannot_retry_from_succeeded(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = _succeed(result)
        result = result.process(RetryPayment(payment_id=payment_id))
        assert result.rejected


class TestRetryLimits:
    def test_max_attempts_enforced(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        # Exhaust all retries
        for i in range(MAX_PAYMENT_ATTEMPTS):
            result = _fail(result, reason=f"Attempt {i + 1} failed")
            if i < MAX_PAYMENT_ATTEMPTS - 1:
                result = result.process(RetryPayment(payment_id=payment_id))

        assert result.aggregate.can_retry() is False
        result = result.process(RetryPayment(payment_id=payment_id))
        assert result.rejected
        assert "Maximum retry attempts" in result.rejection_messages[0]

    def test_attempt_count_increments(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        assert result.attempt_count == 1
        result = _fail(result)
        result = result.process(RetryPayment(payment_id=payment_id))
        assert result.attempt_count == 2


class TestRecordProcessing:
    def test_cannot_process_from_succeeded(self):
        result = given(Payment).process(_initiate())
        result = _succeed(result)
        # record_processing is an aggregate method, not a command.
        # We test via assert_invalid on the aggregate directly.
        with pytest.raises(ValidationError, match="Invalid status transition"):
            result.aggregate.record_processing()


class TestCompleteRefundGuards:
    def test_cannot_complete_already_completed_refund(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = _succeed(result)
        result = result.process(RequestRefund(payment_id=payment_id, amount=50.00, reason="Test"))
        # Get refund_id from the event
        refund = result.aggregate.refunds[0]
        refund_id = str(refund.id)
        result = result.process(
            ProcessRefundWebhook(
                payment_id=payment_id,
                refund_id=refund_id,
                gateway_refund_id="ref-1",
            )
        )
        assert result.accepted
        # Trying to complete the same refund again should be rejected
        result = result.process(
            ProcessRefundWebhook(
                payment_id=payment_id,
                refund_id=refund_id,
                gateway_refund_id="ref-2",
            )
        )
        assert result.rejected


class TestRefundAmountGuards:
    def test_refund_cannot_exceed_payment_amount(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = _succeed(result)
        result = result.process(RequestRefund(payment_id=payment_id, amount=150.00, reason="Test"))
        assert result.rejected
        assert "would exceed" in result.rejection_messages[0]

    def test_cumulative_refunds_cannot_exceed_payment(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = _succeed(result)
        result = result.process(RequestRefund(payment_id=payment_id, amount=60.00, reason="First"))
        refund_id = str(result.aggregate.refunds[0].id)
        result = result.process(
            ProcessRefundWebhook(
                payment_id=payment_id,
                refund_id=refund_id,
                gateway_refund_id="ref-1",
            )
        )
        result = result.process(RequestRefund(payment_id=payment_id, amount=50.00, reason="Second"))
        assert result.rejected
        assert "would exceed" in result.rejection_messages[0]

    def test_exact_amount_refund_is_allowed(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = _succeed(result)
        result = result.process(RequestRefund(payment_id=payment_id, amount=100.00, reason="Full refund"))
        assert result.accepted
