"""Application tests for payment initiation via domain.process()."""

from payments.payment.initiation import InitiatePayment
from payments.payment.payment import Payment, PaymentStatus
from protean import current_domain


def _initiate_payment(**overrides):
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
    command = InitiatePayment(**defaults)
    return current_domain.process(command, asynchronous=False)


class TestInitiatePaymentFlow:
    def test_initiate_returns_payment_id(self):
        payment_id = _initiate_payment()
        assert payment_id is not None

    def test_initiate_persists_in_event_store(self):
        payment_id = _initiate_payment()
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert str(payment.id) == payment_id

    def test_initiate_sets_order_id(self):
        payment_id = _initiate_payment(order_id="ord-999")
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert str(payment.order_id) == "ord-999"

    def test_initiate_sets_status_pending(self):
        payment_id = _initiate_payment()
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert payment.status == PaymentStatus.PENDING.value

    def test_initiate_stores_events(self):
        _initiate_payment(idempotency_key="idem-evt-test")
        messages = current_domain.event_store.store.read("payments::payment")
        payment_events = [
            m
            for m in messages
            if m.metadata and m.metadata.headers and m.metadata.headers.type == "Payments.PaymentInitiated.v1"
        ]
        assert len(payment_events) >= 1

    def test_initiate_sets_amount(self):
        payment_id = _initiate_payment(amount=199.99)
        payment = current_domain.repository_for(Payment).get(payment_id)
        assert payment.amount.value == 199.99
