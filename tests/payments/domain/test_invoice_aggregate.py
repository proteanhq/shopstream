"""Tests for Invoice aggregate creation and lifecycle."""

import pytest
from payments.invoice.events import (
    InvoiceGenerated,
    InvoiceIssued,
    InvoicePaid,
    InvoiceVoided,
)
from payments.invoice.invoice import Invoice, InvoiceStatus
from protean.exceptions import ValidationError


def _make_invoice(**overrides):
    defaults = {
        "order_id": "ord-001",
        "customer_id": "cust-001",
        "line_items_data": [
            {"description": "Black T-Shirt (M)", "quantity": 2, "unit_price": 29.99},
            {"description": "Blue Jeans (32)", "quantity": 1, "unit_price": 49.99},
        ],
        "tax": 8.80,
    }
    defaults.update(overrides)
    return Invoice.create(**defaults)


class TestInvoiceCreation:
    def test_create_sets_order_id(self):
        invoice = _make_invoice()
        assert str(invoice.order_id) == "ord-001"

    def test_create_sets_customer_id(self):
        invoice = _make_invoice()
        assert str(invoice.customer_id) == "cust-001"

    def test_create_generates_invoice_number(self):
        invoice = _make_invoice()
        assert invoice.invoice_number.startswith("INV-")

    def test_create_calculates_subtotal(self):
        invoice = _make_invoice()
        assert invoice.subtotal == pytest.approx(109.97, rel=1e-2)

    def test_create_calculates_total(self):
        invoice = _make_invoice()
        assert invoice.total == pytest.approx(118.77, rel=1e-2)

    def test_create_sets_status_to_draft(self):
        invoice = _make_invoice()
        assert invoice.status == InvoiceStatus.DRAFT.value

    def test_create_populates_line_items(self):
        invoice = _make_invoice()
        assert len(invoice.line_items) == 2

    def test_create_raises_event(self):
        invoice = _make_invoice()
        assert len(invoice._events) == 1
        event = invoice._events[0]
        assert isinstance(event, InvoiceGenerated)


class TestInvoiceIssue:
    def test_issue_sets_status(self):
        invoice = _make_invoice()
        invoice._events.clear()
        invoice.issue()
        assert invoice.status == InvoiceStatus.ISSUED.value

    def test_issue_sets_issued_at(self):
        invoice = _make_invoice()
        invoice.issue()
        assert invoice.issued_at is not None

    def test_issue_raises_event(self):
        invoice = _make_invoice()
        invoice._events.clear()
        invoice.issue()
        assert len(invoice._events) == 1
        assert isinstance(invoice._events[0], InvoiceIssued)

    def test_cannot_issue_paid_invoice(self):
        invoice = _make_invoice()
        invoice.issue()
        invoice.mark_paid()
        with pytest.raises(ValidationError):
            invoice.issue()


class TestInvoiceMarkPaid:
    def test_mark_paid_sets_status(self):
        invoice = _make_invoice()
        invoice.issue()
        invoice._events.clear()
        invoice.mark_paid()
        assert invoice.status == InvoiceStatus.PAID.value

    def test_mark_paid_sets_paid_at(self):
        invoice = _make_invoice()
        invoice.issue()
        invoice.mark_paid()
        assert invoice.paid_at is not None

    def test_mark_paid_raises_event(self):
        invoice = _make_invoice()
        invoice.issue()
        invoice._events.clear()
        invoice.mark_paid()
        assert len(invoice._events) == 1
        assert isinstance(invoice._events[0], InvoicePaid)

    def test_cannot_pay_draft_invoice(self):
        invoice = _make_invoice()
        with pytest.raises(ValidationError):
            invoice.mark_paid()


class TestInvoiceVoid:
    def test_void_draft_invoice(self):
        invoice = _make_invoice()
        invoice._events.clear()
        invoice.void(reason="Cancelled order")
        assert invoice.status == InvoiceStatus.VOIDED.value

    def test_void_issued_invoice(self):
        invoice = _make_invoice()
        invoice.issue()
        invoice._events.clear()
        invoice.void(reason="Cancelled order")
        assert invoice.status == InvoiceStatus.VOIDED.value

    def test_void_raises_event(self):
        invoice = _make_invoice()
        invoice._events.clear()
        invoice.void(reason="Test")
        assert len(invoice._events) == 1
        assert isinstance(invoice._events[0], InvoiceVoided)

    def test_cannot_void_paid_invoice(self):
        invoice = _make_invoice()
        invoice.issue()
        invoice.mark_paid()
        with pytest.raises(ValidationError):
            invoice.void(reason="Too late")
