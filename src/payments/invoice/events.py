"""Domain events for the Invoice aggregate.

All events are versioned, immutable facts representing invoice state changes.
"""

from protean.fields import DateTime, Float, Identifier, String

from payments.domain import payments


@payments.event(part_of="Invoice")
class InvoiceGenerated:
    """A new invoice was generated for an order."""

    __version__ = "v1"

    invoice_id = Identifier(required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    invoice_number = String(required=True)
    total = Float(required=True)
    generated_at = DateTime(required=True)


@payments.event(part_of="Invoice")
class InvoiceIssued:
    """An invoice was sent/issued to the customer."""

    __version__ = "v1"

    invoice_id = Identifier(required=True)
    order_id = Identifier(required=True)
    invoice_number = String(required=True)
    issued_at = DateTime(required=True)


@payments.event(part_of="Invoice")
class InvoicePaid:
    """An invoice was marked as paid."""

    __version__ = "v1"

    invoice_id = Identifier(required=True)
    order_id = Identifier(required=True)
    paid_at = DateTime(required=True)


@payments.event(part_of="Invoice")
class InvoiceVoided:
    """An invoice was voided/cancelled."""

    __version__ = "v1"

    invoice_id = Identifier(required=True)
    order_id = Identifier(required=True)
    reason = String(required=True)
    voided_at = DateTime(required=True)
