"""Domain events for the Invoice aggregate.

All events are versioned, immutable facts representing invoice state changes.

v2 of InvoiceGenerated carries ``total`` as ``Decimal(precision=19, scale=4)``.
v1 carried it as a float; ``payments.invoice.upcasters`` converts stored v1
events.
"""

from datetime import datetime
from decimal import Decimal as D

from protean.fields import DateTime, Decimal, Identifier, String

from payments.domain import payments


@payments.event(part_of="Invoice")
class InvoiceGenerated:
    """A new invoice was generated for an order."""

    __version__ = 2

    invoice_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    invoice_number: str = String(required=True)
    total: D = Decimal(precision=19, scale=4, required=True)
    generated_at: datetime = DateTime(required=True)


@payments.event(part_of="Invoice")
class InvoiceIssued:
    """An invoice was sent/issued to the customer."""

    invoice_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    invoice_number: str = String(required=True)
    issued_at: datetime = DateTime(required=True)


@payments.event(part_of="Invoice")
class InvoicePaid:
    """An invoice was marked as paid."""

    invoice_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    paid_at: datetime = DateTime(required=True)


@payments.event(part_of="Invoice")
class InvoiceVoided:
    """An invoice was voided/cancelled."""

    invoice_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    reason: str = String(required=True)
    voided_at: datetime = DateTime(required=True)
