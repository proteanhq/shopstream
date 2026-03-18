"""Tests for payment processing, success, and failure flows."""

from protean.testing import given

from payments.payment.events import PaymentFailed, PaymentSucceeded
from payments.payment.initiation import InitiatePayment
from payments.payment.payment import Payment, PaymentStatus
from payments.payment.retry import RetryPayment
from payments.payment.webhook import ProcessPaymentWebhook


def _initiate():
    return InitiatePayment(
        order_id="ord-001",
        customer_id="cust-001",
        amount=59.99,
        currency="USD",
        payment_method_type="credit_card",
        last4="4242",
        idempotency_key="idem-001",
    )


class TestPaymentSuccess:
    def test_record_success_transitions_to_succeeded(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = result.process(
            ProcessPaymentWebhook(
                payment_id=payment_id,
                gateway_transaction_id="txn-123",
                gateway_status="succeeded",
            )
        )
        assert result.accepted
        assert result.status == PaymentStatus.SUCCEEDED.value

    def test_record_success_sets_gateway_info(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = result.process(
            ProcessPaymentWebhook(
                payment_id=payment_id,
                gateway_transaction_id="txn-123",
                gateway_status="succeeded",
            )
        )
        assert result.gateway_info.gateway_transaction_id == "txn-123"
        assert result.gateway_info.gateway_status == "succeeded"

    def test_record_success_raises_event(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = result.process(
            ProcessPaymentWebhook(
                payment_id=payment_id,
                gateway_transaction_id="txn-123",
                gateway_status="succeeded",
            )
        )
        assert len(result.events) == 1
        assert PaymentSucceeded in result.events
        assert result.events[PaymentSucceeded].gateway_transaction_id == "txn-123"

    def test_record_success_updates_latest_attempt(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = result.process(
            ProcessPaymentWebhook(
                payment_id=payment_id,
                gateway_transaction_id="txn-123",
                gateway_status="succeeded",
            )
        )
        latest = result.attempts[-1]
        assert latest.status == "succeeded"
        assert latest.gateway_transaction_id == "txn-123"


class TestPaymentFailure:
    def test_record_failure_transitions_to_failed(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = result.process(
            ProcessPaymentWebhook(
                payment_id=payment_id,
                gateway_status="failed",
                failure_reason="Card declined",
            )
        )
        assert result.accepted
        assert result.status == PaymentStatus.FAILED.value

    def test_record_failure_raises_event(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = result.process(
            ProcessPaymentWebhook(
                payment_id=payment_id,
                gateway_status="failed",
                failure_reason="Card declined",
            )
        )
        assert len(result.events) == 1
        assert PaymentFailed in result.events
        event = result.events[PaymentFailed]
        assert event.reason == "Card declined"
        assert event.attempt_number == 1
        assert event.can_retry is True

    def test_record_failure_updates_latest_attempt(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = result.process(
            ProcessPaymentWebhook(
                payment_id=payment_id,
                gateway_status="failed",
                failure_reason="Card declined",
            )
        )
        latest = result.attempts[-1]
        assert latest.status == "failed"
        assert latest.failure_reason == "Card declined"

    def test_can_retry_after_failure(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        result = result.process(
            ProcessPaymentWebhook(
                payment_id=payment_id,
                gateway_status="failed",
                failure_reason="Card declined",
            )
        )
        assert result.aggregate.can_retry() is True

    def test_cannot_retry_after_max_attempts(self):
        result = given(Payment).process(_initiate())
        payment_id = str(result.aggregate.id)
        # Fail, retry, fail, retry, fail = 3 attempts exhausted
        result = (
            result.process(
                ProcessPaymentWebhook(
                    payment_id=payment_id,
                    gateway_status="failed",
                    failure_reason="Declined",
                )
            )
            .process(RetryPayment(payment_id=payment_id))
            .process(
                ProcessPaymentWebhook(
                    payment_id=payment_id,
                    gateway_status="failed",
                    failure_reason="Declined again",
                )
            )
            .process(RetryPayment(payment_id=payment_id))
            .process(
                ProcessPaymentWebhook(
                    payment_id=payment_id,
                    gateway_status="failed",
                    failure_reason="Declined third time",
                )
            )
        )
        assert result.aggregate.can_retry() is False
