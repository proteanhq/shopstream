"""Tests for payment state machine and amount guard invariants."""

import pytest
from payments.payment.payment import MAX_PAYMENT_ATTEMPTS, Payment, PaymentStatus
from protean.exceptions import ValidationError


def _make_payment():
    return Payment.create(
        order_id="ord-001",
        customer_id="cust-001",
        amount=100.00,
        currency="USD",
        payment_method_type="credit_card",
        last4="4242",
        gateway_name="FakeGateway",
        idempotency_key="idem-001",
    )


class TestPaymentStateMachine:
    def test_pending_to_succeeded(self):
        payment = _make_payment()
        payment.record_success(gateway_transaction_id="txn-1")
        assert payment.status == PaymentStatus.SUCCEEDED.value

    def test_pending_to_failed(self):
        payment = _make_payment()
        payment.record_failure(reason="Declined")
        assert payment.status == PaymentStatus.FAILED.value

    def test_failed_to_pending_via_retry(self):
        payment = _make_payment()
        payment.record_failure(reason="Declined")
        payment._events.clear()
        payment.retry()
        assert payment.status == PaymentStatus.PENDING.value

    def test_cannot_succeed_from_failed(self):
        payment = _make_payment()
        payment.record_failure(reason="Declined")
        with pytest.raises(ValidationError):
            payment.record_success(gateway_transaction_id="txn-1")

    def test_cannot_fail_from_succeeded(self):
        payment = _make_payment()
        payment.record_success(gateway_transaction_id="txn-1")
        with pytest.raises(ValidationError):
            payment.record_failure(reason="Declined")

    def test_cannot_retry_from_pending(self):
        payment = _make_payment()
        with pytest.raises(ValidationError):
            payment.retry()

    def test_cannot_retry_from_succeeded(self):
        payment = _make_payment()
        payment.record_success(gateway_transaction_id="txn-1")
        with pytest.raises(ValidationError):
            payment.retry()


class TestRetryLimits:
    def test_max_attempts_enforced(self):
        payment = _make_payment()
        # Exhaust all retries
        for i in range(MAX_PAYMENT_ATTEMPTS):
            payment.record_failure(reason=f"Attempt {i + 1} failed")
            if i < MAX_PAYMENT_ATTEMPTS - 1:
                payment._events.clear()
                payment.retry()

        assert payment.can_retry() is False
        with pytest.raises(ValidationError, match="Maximum retry attempts"):
            payment.retry()

    def test_attempt_count_increments(self):
        payment = _make_payment()
        assert payment.attempt_count == 1
        payment.record_failure(reason="Declined")
        payment._events.clear()
        payment.retry()
        assert payment.attempt_count == 2


class TestRecordProcessing:
    def test_pending_to_processing(self):
        payment = _make_payment()
        payment.record_processing()
        # record_processing validates the transition but doesn't raise an event
        # (it's a convenience method — state change would come from an event)

    def test_cannot_process_from_succeeded(self):
        payment = _make_payment()
        payment.record_success(gateway_transaction_id="txn-1")
        with pytest.raises(ValidationError, match="Cannot transition"):
            payment.record_processing()


class TestCompleteRefundGuards:
    def test_cannot_complete_already_completed_refund(self):
        payment = _make_payment()
        payment.record_success(gateway_transaction_id="txn-1")
        payment._events.clear()
        refund_id = payment.request_refund(amount=50.00, reason="Test")
        payment.complete_refund(refund_id=refund_id, gateway_refund_id="ref-1")
        payment._events.clear()
        with pytest.raises(ValidationError, match="not in Requested state"):
            payment.complete_refund(refund_id=refund_id, gateway_refund_id="ref-2")


class TestRefundAmountGuards:
    def test_refund_cannot_exceed_payment_amount(self):
        payment = _make_payment()
        payment.record_success(gateway_transaction_id="txn-1")
        payment._events.clear()
        with pytest.raises(ValidationError, match="would exceed"):
            payment.request_refund(amount=150.00, reason="Test")

    def test_cumulative_refunds_cannot_exceed_payment(self):
        payment = _make_payment()
        payment.record_success(gateway_transaction_id="txn-1")
        payment._events.clear()
        refund_id = payment.request_refund(amount=60.00, reason="First")
        payment.complete_refund(refund_id=refund_id, gateway_refund_id="ref-1")
        payment._events.clear()
        with pytest.raises(ValidationError, match="would exceed"):
            payment.request_refund(amount=50.00, reason="Second")

    def test_exact_amount_refund_is_allowed(self):
        payment = _make_payment()
        payment.record_success(gateway_transaction_id="txn-1")
        payment._events.clear()
        refund_id = payment.request_refund(amount=100.00, reason="Full refund")
        assert refund_id is not None
