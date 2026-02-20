"""Tests for payment processing, success, and failure flows."""

from payments.payment.events import PaymentFailed, PaymentSucceeded
from payments.payment.payment import Payment, PaymentStatus


def _make_payment(**overrides):
    defaults = {
        "order_id": "ord-001",
        "customer_id": "cust-001",
        "amount": 59.99,
        "currency": "USD",
        "payment_method_type": "credit_card",
        "last4": "4242",
        "gateway_name": "FakeGateway",
        "idempotency_key": "idem-001",
    }
    defaults.update(overrides)
    return Payment.create(**defaults)


class TestPaymentSuccess:
    def test_record_success_transitions_to_succeeded(self):
        payment = _make_payment()
        payment._events.clear()
        payment.record_success(gateway_transaction_id="txn-123")
        assert payment.status == PaymentStatus.SUCCEEDED.value

    def test_record_success_sets_gateway_info(self):
        payment = _make_payment()
        payment._events.clear()
        payment.record_success(gateway_transaction_id="txn-123")
        assert payment.gateway_info.gateway_transaction_id == "txn-123"
        assert payment.gateway_info.gateway_status == "succeeded"

    def test_record_success_raises_event(self):
        payment = _make_payment()
        payment._events.clear()
        payment.record_success(gateway_transaction_id="txn-123")
        assert len(payment._events) == 1
        event = payment._events[0]
        assert isinstance(event, PaymentSucceeded)
        assert event.gateway_transaction_id == "txn-123"

    def test_record_success_updates_latest_attempt(self):
        payment = _make_payment()
        payment._events.clear()
        payment.record_success(gateway_transaction_id="txn-123")
        latest = payment.attempts[-1]
        assert latest.status == "succeeded"
        assert latest.gateway_transaction_id == "txn-123"


class TestPaymentFailure:
    def test_record_failure_transitions_to_failed(self):
        payment = _make_payment()
        payment._events.clear()
        payment.record_failure(reason="Card declined")
        assert payment.status == PaymentStatus.FAILED.value

    def test_record_failure_raises_event(self):
        payment = _make_payment()
        payment._events.clear()
        payment.record_failure(reason="Card declined")
        assert len(payment._events) == 1
        event = payment._events[0]
        assert isinstance(event, PaymentFailed)
        assert event.reason == "Card declined"
        assert event.attempt_number == 1
        assert event.can_retry is True

    def test_record_failure_updates_latest_attempt(self):
        payment = _make_payment()
        payment._events.clear()
        payment.record_failure(reason="Card declined")
        latest = payment.attempts[-1]
        assert latest.status == "failed"
        assert latest.failure_reason == "Card declined"

    def test_can_retry_after_failure(self):
        payment = _make_payment()
        payment.record_failure(reason="Card declined")
        assert payment.can_retry() is True

    def test_cannot_retry_after_max_attempts(self):
        payment = _make_payment()
        payment.record_failure(reason="Declined")
        payment._events.clear()
        payment.retry()
        payment.record_failure(reason="Declined again")
        payment._events.clear()
        payment.retry()
        payment.record_failure(reason="Declined third time")
        assert payment.can_retry() is False
