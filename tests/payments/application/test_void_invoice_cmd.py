"""Application tests for invoice voiding command."""

import json

from payments.invoice.generation import GenerateInvoice
from payments.invoice.invoice import Invoice, InvoiceStatus
from payments.invoice.voiding import VoidInvoice
from protean import current_domain


def _create_invoice():
    command = GenerateInvoice(
        order_id="ord-001",
        customer_id="cust-001",
        line_items=json.dumps(
            [
                {"description": "Widget", "quantity": 1, "unit_price": 50.00},
            ]
        ),
        tax=4.00,
    )
    return current_domain.process(command, asynchronous=False)


class TestVoidInvoiceFlow:
    def test_void_sets_status_voided(self):
        invoice_id = _create_invoice()
        current_domain.process(
            VoidInvoice(invoice_id=invoice_id, reason="Order cancelled"),
            asynchronous=False,
        )
        invoice = current_domain.repository_for(Invoice).get(invoice_id)
        assert invoice.status == InvoiceStatus.VOIDED.value
