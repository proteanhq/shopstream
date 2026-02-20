"""Tests for all 6 payment event classes."""

from datetime import UTC, datetime

from payments.payment.events import (
    PaymentFailed,
    PaymentInitiated,
    PaymentRetryInitiated,
    PaymentSucceeded,
    RefundCompleted,
    RefundRequested,
)


class TestPaymentInitiated:
    def test_construction(self):
        event = PaymentInitiated(
            payment_id="pay-001",
            order_id="ord-001",
            customer_id="cust-001",
            amount=59.99,
            currency="USD",
            payment_method_type="credit_card",
            last4="4242",
            gateway_name="FakeGateway",
            idempotency_key="idem-001",
            initiated_at=datetime.now(UTC),
        )
        assert event.payment_id == "pay-001"
        assert event.amount == 59.99
        assert event.currency == "USD"
        assert event.gateway_name == "FakeGateway"


class TestPaymentSucceeded:
    def test_construction(self):
        event = PaymentSucceeded(
            payment_id="pay-001",
            order_id="ord-001",
            customer_id="cust-001",
            amount=59.99,
            currency="USD",
            gateway_transaction_id="txn-123",
            succeeded_at=datetime.now(UTC),
        )
        assert event.gateway_transaction_id == "txn-123"
        assert event.amount == 59.99


class TestPaymentFailed:
    def test_construction(self):
        event = PaymentFailed(
            payment_id="pay-001",
            order_id="ord-001",
            customer_id="cust-001",
            reason="Card declined",
            attempt_number=1,
            can_retry=True,
            failed_at=datetime.now(UTC),
        )
        assert event.reason == "Card declined"
        assert event.attempt_number == 1
        assert event.can_retry is True


class TestPaymentRetryInitiated:
    def test_construction(self):
        event = PaymentRetryInitiated(
            payment_id="pay-001",
            order_id="ord-001",
            attempt_number=2,
            retried_at=datetime.now(UTC),
        )
        assert event.attempt_number == 2


class TestRefundRequested:
    def test_construction(self):
        event = RefundRequested(
            payment_id="pay-001",
            refund_id="ref-001",
            order_id="ord-001",
            amount=30.00,
            reason="Defective product",
            requested_at=datetime.now(UTC),
        )
        assert event.amount == 30.00
        assert event.reason == "Defective product"


class TestRefundCompleted:
    def test_construction(self):
        event = RefundCompleted(
            payment_id="pay-001",
            refund_id="ref-001",
            order_id="ord-001",
            amount=30.00,
            gateway_refund_id="gw-ref-001",
            completed_at=datetime.now(UTC),
        )
        assert event.gateway_refund_id == "gw-ref-001"
        assert event.amount == 30.00
