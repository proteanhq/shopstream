"""Application tests for invoice generation command."""

import json

from payments.invoice.generation import GenerateInvoice
from payments.invoice.invoice import Invoice, InvoiceStatus
from protean import current_domain


def _generate_invoice(**overrides):
    defaults = {
        "order_id": "ord-001",
        "customer_id": "cust-001",
        "line_items": json.dumps(
            [
                {"description": "Widget A", "quantity": 2, "unit_price": 25.00},
                {"description": "Widget B", "quantity": 1, "unit_price": 50.00},
            ]
        ),
        "tax": 8.00,
    }
    defaults.update(overrides)
    command = GenerateInvoice(**defaults)
    return current_domain.process(command, asynchronous=False)


class TestGenerateInvoiceFlow:
    def test_generate_returns_invoice_id(self):
        invoice_id = _generate_invoice()
        assert invoice_id is not None

    def test_generate_persists_invoice(self):
        invoice_id = _generate_invoice()
        invoice = current_domain.repository_for(Invoice).get(invoice_id)
        assert str(invoice.id) == invoice_id

    def test_generate_sets_status_draft(self):
        invoice_id = _generate_invoice()
        invoice = current_domain.repository_for(Invoice).get(invoice_id)
        assert invoice.status == InvoiceStatus.DRAFT.value

    def test_generate_calculates_total(self):
        invoice_id = _generate_invoice()
        invoice = current_domain.repository_for(Invoice).get(invoice_id)
        # 2*25 + 1*50 + 8 tax = 108
        assert invoice.total == 108.00
