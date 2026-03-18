"""Tests for Payment aggregate creation and structure."""

from protean.testing import given

from payments.payment.events import PaymentInitiated
from payments.payment.initiation import InitiatePayment
from payments.payment.payment import (
    GatewayInfo,
    Money,
    Payment,
    PaymentMethod,
    PaymentStatus,
)


def _initiate(**overrides):
    defaults = {
        "order_id": "ord-001",
        "customer_id": "cust-001",
        "amount": 59.99,
        "currency": "USD",
        "payment_method_type": "credit_card",
        "last4": "4242",
        "idempotency_key": "idem-001",
    }
    defaults.update(overrides)
    return InitiatePayment(**defaults)


class TestPaymentCreation:
    def test_create_sets_order_id(self):
        result = given(Payment).process(_initiate())
        assert result.accepted
        assert str(result.order_id) == "ord-001"

    def test_create_sets_customer_id(self):
        result = given(Payment).process(_initiate())
        assert str(result.customer_id) == "cust-001"

    def test_create_sets_amount(self):
        result = given(Payment).process(_initiate())
        assert result.amount.value == 59.99
        assert result.amount.currency == "USD"

    def test_create_sets_status_to_pending(self):
        result = given(Payment).process(_initiate())
        assert result.status == PaymentStatus.PENDING.value

    def test_create_sets_payment_method(self):
        result = given(Payment).process(_initiate())
        assert result.payment_method.method_type == "credit_card"
        assert result.payment_method.last4 == "4242"

    def test_create_sets_gateway_info(self):
        result = given(Payment).process(_initiate())
        assert result.gateway_info.gateway_name == "FakeGateway"

    def test_create_sets_idempotency_key(self):
        result = given(Payment).process(_initiate())
        assert result.idempotency_key == "idem-001"

    def test_create_sets_attempt_count(self):
        result = given(Payment).process(_initiate())
        assert result.attempt_count == 1

    def test_create_sets_total_refunded_to_zero(self):
        result = given(Payment).process(_initiate())
        assert result.total_refunded == 0.0

    def test_create_generates_id(self):
        result = given(Payment).process(_initiate())
        assert result.aggregate.id is not None

    def test_create_sets_timestamps(self):
        result = given(Payment).process(_initiate())
        assert result.created_at is not None
        assert result.updated_at is not None

    def test_create_adds_first_attempt(self):
        result = given(Payment).process(_initiate())
        assert len(result.attempts) == 1
        assert result.attempts[0].status == "processing"

    def test_create_with_no_last4(self):
        result = given(Payment).process(_initiate(last4=None))
        assert result.payment_method.last4 == ""


class TestPaymentCreatedEvent:
    def test_create_raises_payment_initiated_event(self):
        result = given(Payment).process(_initiate())
        assert len(result.events) == 1
        assert PaymentInitiated in result.events

    def test_event_contains_payment_id(self):
        result = given(Payment).process(_initiate())
        assert result.events[PaymentInitiated].payment_id == str(result.aggregate.id)

    def test_event_contains_order_id(self):
        result = given(Payment).process(_initiate())
        assert result.events[PaymentInitiated].order_id == "ord-001"

    def test_event_contains_amount(self):
        result = given(Payment).process(_initiate())
        event = result.events[PaymentInitiated]
        assert event.amount == 59.99
        assert event.currency == "USD"

    def test_event_contains_gateway_name(self):
        result = given(Payment).process(_initiate())
        assert result.events[PaymentInitiated].gateway_name == "FakeGateway"


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
