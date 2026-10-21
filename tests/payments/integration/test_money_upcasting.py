"""Payments events stored as v1, with float money, load as v2 ``Decimal`` events.

Each test writes a raw v1 payload to the event store, the way an event written
before the ``Decimal`` change sits there, then reads it back through
``to_domain_object``, which runs the upcaster chain.
"""

from decimal import Decimal

import pytest
from protean import current_domain

from payments.invoice.events import InvoiceGenerated
from payments.payment.events import PaymentInitiated, PaymentSucceeded, RefundCompleted, RefundRequested

_TIME = "2025-01-01T00:00:00+00:00"


def _load_v1(event_name, aggregate, data):
    stream = f"payments::{aggregate}-{data[f'{aggregate}_id']}"
    type_string = f"Payments.{event_name}.v1"
    current_domain.event_store.store._write(
        stream,
        type_string,
        data,
        {
            "headers": {"id": f"evt-{event_name}", "type": type_string, "time": _TIME, "stream": stream},
            "envelope": {"specversion": "1.0"},
            "domain": {"kind": "EVENT", "stream_category": f"payments::{aggregate}", "version": 1},
        },
    )
    messages = current_domain.event_store.store.read(stream)
    assert len(messages) == 1
    return messages[0].to_domain_object()


def _payment_initiated(amount):
    return {
        "payment_id": "pay-v1",
        "order_id": "ord-v1",
        "customer_id": "cust-v1",
        "amount": amount,
        "currency": "USD",
        "payment_method_type": "card",
        "last4": "4242",
        "gateway_name": "fake",
        "idempotency_key": "idem-v1",
        "attempt_id": "att-v1",
        "initiated_at": _TIME,
    }


class TestPaymentEventsUpcastFromV1:
    @pytest.mark.parametrize(
        ("stored", "expected"),
        [(49.99, Decimal("49.9900")), (3 * 1.1, Decimal("3.3000")), (10.00005, Decimal("10.0000"))],
    )
    def test_payment_initiated_amount_becomes_a_4_place_decimal(self, stored, expected):
        event = _load_v1("PaymentInitiated", "payment", _payment_initiated(stored))
        assert isinstance(event, PaymentInitiated)
        assert event.amount == expected

    def test_payment_succeeded_amount_becomes_a_decimal(self):
        event = _load_v1(
            "PaymentSucceeded",
            "payment",
            {
                "payment_id": "pay-v1",
                "order_id": "ord-v1",
                "customer_id": "cust-v1",
                "amount": 0.1 + 0.2,
                "currency": "USD",
                "gateway_transaction_id": "gtx-v1",
                "succeeded_at": _TIME,
            },
        )
        assert isinstance(event, PaymentSucceeded)
        assert event.amount == Decimal("0.3000")

    def test_refund_requested_amount_becomes_a_decimal(self):
        event = _load_v1(
            "RefundRequested",
            "payment",
            {
                "payment_id": "pay-v1",
                "refund_id": "ref-v1",
                "order_id": "ord-v1",
                "amount": 0.7 + 0.1,
                "reason": "damaged",
                "requested_at": _TIME,
            },
        )
        assert isinstance(event, RefundRequested)
        assert event.amount == Decimal("0.8000")

    def test_refund_completed_amount_becomes_a_decimal(self):
        event = _load_v1(
            "RefundCompleted",
            "payment",
            {
                "payment_id": "pay-v1",
                "refund_id": "ref-v1",
                "order_id": "ord-v1",
                "customer_id": "cust-v1",
                "amount": 100 - 99.99,
                "gateway_refund_id": "gref-v1",
                "completed_at": _TIME,
            },
        )
        assert isinstance(event, RefundCompleted)
        assert event.amount == Decimal("0.0100")


class TestInvoiceEventsUpcastFromV1:
    def test_invoice_generated_total_becomes_a_decimal(self):
        event = _load_v1(
            "InvoiceGenerated",
            "invoice",
            {
                "invoice_id": "inv-v1",
                "order_id": "ord-v1",
                "customer_id": "cust-v1",
                "invoice_number": "INV-0001",
                "total": 118.77000000000001,
                "generated_at": _TIME,
            },
        )
        assert isinstance(event, InvoiceGenerated)
        assert event.total == Decimal("118.7700")
