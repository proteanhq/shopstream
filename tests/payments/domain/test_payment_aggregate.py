"""Tests for Payment aggregate creation and structure."""

from payments.payment.events import PaymentInitiated
from payments.payment.payment import (
    GatewayInfo,
    Money,
    Payment,
    PaymentMethod,
    PaymentStatus,
)


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


class TestPaymentCreation:
    def test_create_sets_order_id(self):
        payment = _make_payment()
        assert str(payment.order_id) == "ord-001"

    def test_create_sets_customer_id(self):
        payment = _make_payment()
        assert str(payment.customer_id) == "cust-001"

    def test_create_sets_amount(self):
        payment = _make_payment()
        assert payment.amount.value == 59.99
        assert payment.amount.currency == "USD"

    def test_create_sets_status_to_pending(self):
        payment = _make_payment()
        assert payment.status == PaymentStatus.PENDING.value

    def test_create_sets_payment_method(self):
        payment = _make_payment()
        assert payment.payment_method.method_type == "credit_card"
        assert payment.payment_method.last4 == "4242"

    def test_create_sets_gateway_info(self):
        payment = _make_payment()
        assert payment.gateway_info.gateway_name == "FakeGateway"

    def test_create_sets_idempotency_key(self):
        payment = _make_payment()
        assert payment.idempotency_key == "idem-001"

    def test_create_sets_attempt_count(self):
        payment = _make_payment()
        assert payment.attempt_count == 1

    def test_create_sets_total_refunded_to_zero(self):
        payment = _make_payment()
        assert payment.total_refunded == 0.0

    def test_create_generates_id(self):
        payment = _make_payment()
        assert payment.id is not None

    def test_create_sets_timestamps(self):
        payment = _make_payment()
        assert payment.created_at is not None
        assert payment.updated_at is not None

    def test_create_adds_first_attempt(self):
        payment = _make_payment()
        assert len(payment.attempts) == 1
        assert payment.attempts[0].status == "processing"

    def test_create_with_no_last4(self):
        payment = _make_payment(last4=None)
        assert payment.payment_method.last4 == ""


class TestPaymentCreatedEvent:
    def test_create_raises_payment_initiated_event(self):
        payment = _make_payment()
        assert len(payment._events) == 1
        event = payment._events[0]
        assert isinstance(event, PaymentInitiated)

    def test_event_contains_payment_id(self):
        payment = _make_payment()
        event = payment._events[0]
        assert event.payment_id == str(payment.id)

    def test_event_contains_order_id(self):
        payment = _make_payment()
        event = payment._events[0]
        assert event.order_id == "ord-001"

    def test_event_contains_amount(self):
        payment = _make_payment()
        event = payment._events[0]
        assert event.amount == 59.99
        assert event.currency == "USD"

    def test_event_contains_gateway_name(self):
        payment = _make_payment()
        event = payment._events[0]
        assert event.gateway_name == "FakeGateway"


class TestMoneyVO:
    def test_construction(self):
        money = Money(currency="EUR", value=100.50)
        assert money.currency == "EUR"
        assert money.value == 100.50

    def test_defaults(self):
        money = Money()
        assert money.currency == "USD"
        assert money.value == 0.0


class TestPaymentMethodVO:
    def test_construction(self):
        pm = PaymentMethod(method_type="credit_card", last4="4242")
        assert pm.method_type == "credit_card"
        assert pm.last4 == "4242"


class TestGatewayInfoVO:
    def test_construction(self):
        gi = GatewayInfo(
            gateway_name="FakeGateway",
            gateway_transaction_id="txn-123",
            gateway_status="succeeded",
        )
        assert gi.gateway_name == "FakeGateway"
        assert gi.gateway_transaction_id == "txn-123"
