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
from decimal import Decimal as D
from enum import Enum
from typing import Protocol
from uuid import uuid4

from protean import value_object_from_entity
from protean.fields import DateTime, Decimal, Float, HasMany, Identifier, Status, String

from payments.domain import payments
from payments.invoice.events import (
    InvoiceGenerated,
    InvoiceIssued,
    InvoicePaid,
    InvoiceVoided,
)
from shared.money import to_money


class InvoiceStatus(Enum):
    DRAFT = "Draft"
    ISSUED = "Issued"
    PAID = "Paid"
    VOIDED = "Voided"


@payments.entity(part_of="Invoice")
class InvoiceLineItem:
    """A line item on an invoice."""

    description: str = String(required=True, max_length=500)
    quantity: float = Float(required=True)
    unit_price: D = Decimal(precision=19, scale=4, required=True)
    total: D = Decimal(precision=19, scale=4, required=True)


# Auto-generated input value object mirroring the caller-provided fields of
# InvoiceLineItem (Protean 0.16 `value_object_from_entity`). `total` is excluded
# because the aggregate derives it (quantity x unit_price). Carried by the
# GenerateInvoice command in place of an untyped `List(Dict())`.
InvoiceLineItemInput = value_object_from_entity(InvoiceLineItem, name="InvoiceLineItemInput", exclude={"total"})


# mypy cannot use the runtime-built InvoiceLineItemInput as a type, so this names the fields the code reads.
class InvoiceLineItemData(Protocol):
    @property
    def description(self) -> str: ...
    @property
    def quantity(self) -> float: ...
    @property
    def unit_price(self) -> D: ...


@payments.aggregate
class Invoice:
    order_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    invoice_number: str = String(required=True, max_length=50)
    line_items: list[InvoiceLineItem] = HasMany(InvoiceLineItem)
    subtotal: D = Decimal(precision=19, scale=4, default=D("0"))
    tax: D = Decimal(precision=19, scale=4, default=D("0"))
    total: D = Decimal(precision=19, scale=4, default=D("0"))
    status: str = Status(
        InvoiceStatus,
        default=InvoiceStatus.DRAFT.value,
        transitions={
            InvoiceStatus.DRAFT: [InvoiceStatus.ISSUED, InvoiceStatus.VOIDED],
            InvoiceStatus.ISSUED: [InvoiceStatus.PAID, InvoiceStatus.VOIDED],
        },
    )
    issued_at: datetime | None = DateTime()
    paid_at: datetime | None = DateTime()
    created_at: datetime | None = DateTime()
    updated_at: datetime | None = DateTime()

    @classmethod
    def create(
        cls,
        order_id: str,
        customer_id: str,
        line_items_data: list[InvoiceLineItemData],
        tax: float | D = 0,
    ) -> "Invoice":
        """Create a new invoice for an order.

        ``line_items_data`` is a list of ``InvoiceLineItemInput`` value objects
        (the command coerces incoming dicts into them). The line total is
        derived here, then each input is promoted to an ``InvoiceLineItem``
        entity.
        """
        now = datetime.now(UTC)
        invoice_number = f"INV-{uuid4().hex[:8].upper()}"

        items = []
        subtotal = to_money(0)
        for item_input in line_items_data:
            # quantity is a Float count; it goes through str so a quantity such
            # as 0.1 multiplies as written, not as its binary expansion.
            item_total = to_money(D(str(item_input.quantity)) * to_money(item_input.unit_price))
            items.append(
                InvoiceLineItem(
                    description=item_input.description,
                    quantity=item_input.quantity,
                    unit_price=item_input.unit_price,
                    total=item_total,
                )
            )
            subtotal += item_total

        tax_amount = to_money(tax)
        total = subtotal + tax_amount

        invoice = cls(
            order_id=order_id,
            customer_id=customer_id,
            invoice_number=invoice_number,
            subtotal=subtotal,
            tax=tax_amount,
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
