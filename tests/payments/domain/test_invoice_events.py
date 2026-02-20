"""Tests for all 4 invoice event classes."""

from datetime import UTC, datetime

from payments.invoice.events import (
    InvoiceGenerated,
    InvoiceIssued,
    InvoicePaid,
    InvoiceVoided,
)


class TestInvoiceGenerated:
    def test_construction(self):
        event = InvoiceGenerated(
            invoice_id="inv-001",
            order_id="ord-001",
            customer_id="cust-001",
            invoice_number="INV-ABC12345",
            total=118.77,
            generated_at=datetime.now(UTC),
        )
        assert event.invoice_number == "INV-ABC12345"
        assert event.total == 118.77


class TestInvoiceIssued:
    def test_construction(self):
        event = InvoiceIssued(
            invoice_id="inv-001",
            order_id="ord-001",
            invoice_number="INV-ABC12345",
            issued_at=datetime.now(UTC),
        )
        assert event.invoice_number == "INV-ABC12345"


class TestInvoicePaid:
    def test_construction(self):
        event = InvoicePaid(
            invoice_id="inv-001",
            order_id="ord-001",
            paid_at=datetime.now(UTC),
        )
        assert event.invoice_id == "inv-001"


class TestInvoiceVoided:
    def test_construction(self):
        event = InvoiceVoided(
            invoice_id="inv-001",
            order_id="ord-001",
            reason="Order cancelled",
            voided_at=datetime.now(UTC),
        )
        assert event.reason == "Order cancelled"
