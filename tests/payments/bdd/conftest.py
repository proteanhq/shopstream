"""Shared BDD fixtures and step definitions for the Payments domain."""

import pytest
from payments.invoice.invoice import Invoice
from payments.payment.events import (
    PaymentFailed,
    PaymentInitiated,
    PaymentRetryInitiated,
    PaymentSucceeded,
    RefundCompleted,
    RefundRequested,
)
from payments.payment.payment import MAX_PAYMENT_ATTEMPTS, Payment
from protean.exceptions import ValidationError
from pytest_bdd import given, parsers, then, when

# Map event name strings to classes for dynamic lookup
_PAYMENT_EVENT_CLASSES = {
    "PaymentInitiated": PaymentInitiated,
    "PaymentSucceeded": PaymentSucceeded,
    "PaymentFailed": PaymentFailed,
    "PaymentRetryInitiated": PaymentRetryInitiated,
    "RefundRequested": RefundRequested,
    "RefundCompleted": RefundCompleted,
}


# ---------------------------------------------------------------------------
# Payment Given steps
# ---------------------------------------------------------------------------
@given("a new payment is initiated", target_fixture="payment")
def _new_payment():
    payment = Payment.create(
        order_id="ord-001",
        customer_id="cust-001",
        amount=100.00,
        currency="USD",
        payment_method_type="credit_card",
        last4="4242",
        gateway_name="FakeGateway",
        idempotency_key="bdd-idem-001",
    )
    payment._events.clear()
    return payment


@given("the payment has failed", target_fixture="payment")
def _failed_payment(payment):
    payment.record_failure(reason="Card declined")
    payment._events.clear()
    return payment


@given("the payment has exhausted all retries", target_fixture="payment")
def _exhausted_retries(payment):
    payment.record_failure(reason="Declined")
    for _ in range(MAX_PAYMENT_ATTEMPTS - 1):
        payment._events.clear()
        payment.retry()
        payment.record_failure(reason="Declined again")
    payment._events.clear()
    return payment


@given(parsers.cfparse("a succeeded payment of {amount:f}"), target_fixture="payment")
def _succeeded_payment(amount):
    payment = Payment.create(
        order_id="ord-001",
        customer_id="cust-001",
        amount=amount,
        currency="USD",
        payment_method_type="credit_card",
        last4="4242",
        gateway_name="FakeGateway",
        idempotency_key="bdd-idem-002",
    )
    payment.record_success(gateway_transaction_id="txn-bdd-001")
    payment._events.clear()
    return payment


@given(parsers.cfparse("a refund of {amount:f} was requested"), target_fixture="payment")
def _refund_requested(payment, amount):
    payment.request_refund(amount=amount, reason="Test refund")
    payment._events.clear()
    return payment


# ---------------------------------------------------------------------------
# Payment When steps
# ---------------------------------------------------------------------------
@when("a new payment is initiated", target_fixture="payment")
def _initiate_new_payment():
    payment = Payment.create(
        order_id="ord-001",
        customer_id="cust-001",
        amount=100.00,
        currency="USD",
        payment_method_type="credit_card",
        last4="4242",
        gateway_name="FakeGateway",
        idempotency_key="bdd-idem-when-001",
    )
    return payment


@when(parsers.cfparse('the payment succeeds with transaction ID "{txn_id}"'), target_fixture="payment")
def _payment_succeeds(payment, txn_id):
    payment.record_success(gateway_transaction_id=txn_id)
    return payment


@when(parsers.cfparse('the payment fails with reason "{reason}"'), target_fixture="payment")
def _payment_fails(payment, reason):
    payment.record_failure(reason=reason)
    return payment


@when("the payment is retried", target_fixture="payment")
def _payment_retried(payment):
    payment.retry()
    return payment


@when(parsers.cfparse('a refund of {amount:f} is requested for reason "{reason}"'), target_fixture="payment")
def _request_refund(payment, amount, reason):
    payment.request_refund(amount=amount, reason=reason)
    return payment


@when(parsers.cfparse('the refund is completed with gateway ID "{gw_ref_id}"'), target_fixture="payment")
def _complete_refund(payment, gw_ref_id):
    refund_id = str(payment.refunds[0].id)
    payment.complete_refund(refund_id=refund_id, gateway_refund_id=gw_ref_id)
    return payment


# ---------------------------------------------------------------------------
# Payment Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the payment status is "{status}"'))
def _payment_status(payment, status):
    assert payment.status == status


@then(parsers.cfparse("the attempt count is {count:d}"))
def _attempt_count(payment, count):
    assert payment.attempt_count == count


@then(parsers.cfparse("the payment has {count:d} refund"))
def _refund_count(payment, count):
    assert len(payment.refunds) == count


@then("retrying the payment fails with a validation error")
def _retry_fails(payment):
    with pytest.raises(ValidationError):
        payment.retry()


@then(parsers.cfparse("a {event_type} payment event is raised"))
def _payment_event_raised(payment, event_type):
    event_cls = _PAYMENT_EVENT_CLASSES[event_type]
    assert any(
        isinstance(e, event_cls) for e in payment._events
    ), f"No {event_type} event found. Events: {[type(e).__name__ for e in payment._events]}"


# ---------------------------------------------------------------------------
# Invoice Given steps
# ---------------------------------------------------------------------------
@given("a new invoice is generated", target_fixture="invoice")
def _new_invoice():
    invoice = Invoice.create(
        order_id="ord-001",
        customer_id="cust-001",
        line_items_data=[
            {"description": "Widget", "quantity": 2, "unit_price": 25.00},
        ],
        tax=4.00,
    )
    invoice._events.clear()
    return invoice


@given("the invoice was issued", target_fixture="invoice")
def _issued_invoice(invoice):
    invoice.issue()
    invoice._events.clear()
    return invoice


# ---------------------------------------------------------------------------
# Invoice When steps
# ---------------------------------------------------------------------------
@when("the invoice is issued", target_fixture="invoice")
def _issue_invoice(invoice):
    invoice.issue()
    return invoice


@when("the invoice is marked as paid", target_fixture="invoice")
def _mark_paid(invoice):
    invoice.mark_paid()
    return invoice


@when(parsers.cfparse('the invoice is voided with reason "{reason}"'), target_fixture="invoice")
def _void_invoice(invoice, reason):
    invoice.void(reason=reason)
    return invoice


# ---------------------------------------------------------------------------
# Invoice Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the invoice status is "{status}"'))
def _invoice_status(invoice, status):
    assert invoice.status == status


@then(parsers.cfparse('the invoice has a number starting with "{prefix}"'))
def _invoice_number(invoice, prefix):
    assert invoice.invoice_number.startswith(prefix)
