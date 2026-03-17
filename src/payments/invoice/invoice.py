"""Invoice aggregate (CQRS) — billing and invoicing.

The Invoice aggregate uses standard CQRS (not event-sourced) since invoices
don't require the full audit trail that payments need. Invoices are generated
after payment succeeds and follow a simple Draft → Issued → Paid lifecycle.

State Machine:
    DRAFT → ISSUED → PAID
    DRAFT → VOIDED
    ISSUED → VOIDED
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from protean.fields import DateTime, Float, HasMany, Identifier, Status, String

from payments.domain import payments
from payments.invoice.events import (
    InvoiceGenerated,
    InvoiceIssued,
    InvoicePaid,
    InvoiceVoided,
)


class InvoiceStatus(Enum):
    DRAFT = "Draft"
    ISSUED = "Issued"
    PAID = "Paid"
    VOIDED = "Voided"


@payments.entity(part_of="Invoice")
class InvoiceLineItem:
    """A line item on an invoice."""

    description = String(required=True, max_length=500)
    quantity = Float(required=True)
    unit_price = Float(required=True)
    total = Float(required=True)


@payments.aggregate
class Invoice:
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    invoice_number = String(required=True, max_length=50)
    line_items = HasMany(InvoiceLineItem)
    subtotal = Float(default=0.0)
    tax = Float(default=0.0)
    total = Float(default=0.0)
    status = Status(
        InvoiceStatus,
        default=InvoiceStatus.DRAFT.value,
        transitions={
            InvoiceStatus.DRAFT: [InvoiceStatus.ISSUED, InvoiceStatus.VOIDED],
            InvoiceStatus.ISSUED: [InvoiceStatus.PAID, InvoiceStatus.VOIDED],
        },
    )
    issued_at = DateTime()
    paid_at = DateTime()
    created_at = DateTime()
    updated_at = DateTime()

    @classmethod
    def create(
        cls,
        order_id: str,
        customer_id: str,
        line_items_data: list[dict],
        tax: float = 0.0,
    ):
        """Create a new invoice for an order."""
        now = datetime.now(UTC)
        invoice_number = f"INV-{uuid4().hex[:8].upper()}"

        items = []
        subtotal = 0.0
        for item_data in line_items_data:
            item_total = item_data["quantity"] * item_data["unit_price"]
            items.append(
                InvoiceLineItem(
                    description=item_data["description"],
                    quantity=item_data["quantity"],
                    unit_price=item_data["unit_price"],
                    total=item_total,
                )
            )
            subtotal += item_total

        total = subtotal + tax

        invoice = cls(
            order_id=order_id,
            customer_id=customer_id,
            invoice_number=invoice_number,
            subtotal=subtotal,
            tax=tax,
            total=total,
            created_at=now,
            updated_at=now,
        )
        for item in items:
            invoice.add_line_items(item)

        invoice.raise_(
            InvoiceGenerated(
                invoice_id=str(invoice.id),
                order_id=order_id,
                customer_id=customer_id,
                invoice_number=invoice_number,
                total=total,
                generated_at=now,
            )
        )
        return invoice

    def issue(self) -> None:
        """Issue the invoice to the customer."""
        now = datetime.now(UTC)
        self.status = InvoiceStatus.ISSUED.value
        self.issued_at = now
        self.updated_at = now
        self.raise_(
            InvoiceIssued(
                invoice_id=str(self.id),
                order_id=str(self.order_id),
                invoice_number=self.invoice_number,
                issued_at=now,
            )
        )

    def mark_paid(self) -> None:
        """Mark the invoice as paid."""
        now = datetime.now(UTC)
        self.status = InvoiceStatus.PAID.value
        self.paid_at = now
        self.updated_at = now
        self.raise_(
            InvoicePaid(
                invoice_id=str(self.id),
                order_id=str(self.order_id),
                paid_at=now,
            )
        )

    def void(self, reason: str) -> None:
        """Void the invoice."""
        now = datetime.now(UTC)
        self.status = InvoiceStatus.VOIDED.value
        self.updated_at = now
        self.raise_(
            InvoiceVoided(
                invoice_id=str(self.id),
                order_id=str(self.order_id),
                reason=reason,
                voided_at=now,
            )
        )
