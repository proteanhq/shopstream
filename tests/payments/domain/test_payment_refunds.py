"""Tests for payment refund flows."""

import pytest
from payments.payment.events import RefundCompleted, RefundRequested
from payments.payment.payment import Payment, PaymentStatus, RefundStatus
from protean.exceptions import ValidationError


def _make_succeeded_payment():
    payment = Payment.create(
        order_id="ord-001",
        customer_id="cust-001",
        amount=100.00,
        currency="USD",
        payment_method_type="credit_card",
        last4="4242",
        gateway_name="FakeGateway",
        idempotency_key="idem-001",
    )
    payment.record_success(gateway_transaction_id="txn-123")
    payment._events.clear()
    return payment


class TestRequestRefund:
    def test_request_refund_adds_refund_entity(self):
        payment = _make_succeeded_payment()
        payment.request_refund(amount=50.00, reason="Defective product")
        assert len(payment.refunds) == 1
        refund = payment.refunds[0]
        assert refund.amount == 50.00
        assert refund.reason == "Defective product"
        assert refund.status == RefundStatus.REQUESTED.value

    def test_request_refund_raises_event(self):
        payment = _make_succeeded_payment()
        payment.request_refund(amount=50.00, reason="Defective")
        assert len(payment._events) == 1
        event = payment._events[0]
        assert isinstance(event, RefundRequested)
        assert event.amount == 50.00

    def test_request_refund_returns_refund_id(self):
        payment = _make_succeeded_payment()
        refund_id = payment.request_refund(amount=50.00, reason="Test")
        assert refund_id is not None

    def test_cannot_refund_pending_payment(self):
        payment = Payment.create(
            order_id="ord-001",
            customer_id="cust-001",
            amount=100.00,
            currency="USD",
            payment_method_type="credit_card",
            last4="4242",
            gateway_name="FakeGateway",
            idempotency_key="idem-001",
        )
        with pytest.raises(ValidationError):
            payment.request_refund(amount=50.00, reason="Test")

    def test_cannot_refund_more_than_payment_amount(self):
        payment = _make_succeeded_payment()
        with pytest.raises(ValidationError):
            payment.request_refund(amount=150.00, reason="Test")


class TestCompleteRefund:
    def test_complete_refund_updates_refund_status(self):
        payment = _make_succeeded_payment()
        refund_id = payment.request_refund(amount=50.00, reason="Test")
        payment._events.clear()
        payment.complete_refund(refund_id=refund_id, gateway_refund_id="ref-123")
        refund = next(r for r in payment.refunds if str(r.id) == refund_id)
        assert refund.status == RefundStatus.COMPLETED.value
        assert refund.gateway_refund_id == "ref-123"

    def test_complete_refund_raises_event(self):
        payment = _make_succeeded_payment()
        refund_id = payment.request_refund(amount=50.00, reason="Test")
        payment._events.clear()
        payment.complete_refund(refund_id=refund_id, gateway_refund_id="ref-123")
        assert len(payment._events) == 1
        event = payment._events[0]
        assert isinstance(event, RefundCompleted)
        assert event.amount == 50.00

    def test_partial_refund_sets_partially_refunded(self):
        payment = _make_succeeded_payment()
        refund_id = payment.request_refund(amount=50.00, reason="Test")
        payment._events.clear()
        payment.complete_refund(refund_id=refund_id, gateway_refund_id="ref-123")
        assert payment.status == PaymentStatus.PARTIALLY_REFUNDED.value
        assert payment.total_refunded == 50.00

    def test_full_refund_sets_refunded(self):
        payment = _make_succeeded_payment()
        refund_id = payment.request_refund(amount=100.00, reason="Test")
        payment._events.clear()
        payment.complete_refund(refund_id=refund_id, gateway_refund_id="ref-123")
        assert payment.status == PaymentStatus.REFUNDED.value
        assert payment.total_refunded == 100.00

    def test_complete_refund_with_invalid_refund_id(self):
        payment = _make_succeeded_payment()
        with pytest.raises(ValidationError):
            payment.complete_refund(refund_id="nonexistent", gateway_refund_id="ref-123")
