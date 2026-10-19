"""Invoice status — real-time invoice state view."""

from datetime import datetime

from protean.core.projector import on
from protean.fields import DateTime, Float, Identifier, String
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.invoice.events import (
    InvoiceGenerated,
    InvoiceIssued,
    InvoicePaid,
    InvoiceVoided,
)
from payments.invoice.invoice import Invoice


@payments.projection
class InvoiceStatusView:
    invoice_id: str = Identifier(identifier=True, required=True)
    order_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    invoice_number: str = String(required=True)
    total: float | None = Float()
    status: str = String(required=True)
    issued_at: datetime | None = DateTime()
    paid_at: datetime | None = DateTime()
    voided_reason: str | None = String()
    created_at: datetime | None = DateTime()
    updated_at: datetime | None = DateTime()


@payments.projector(projector_for=InvoiceStatusView, aggregates=[Invoice])
class InvoiceStatusProjector:
    @on(InvoiceGenerated)
    def on_invoice_generated(self, event):
        current_domain.repository_for(InvoiceStatusView).add(
            InvoiceStatusView(
                invoice_id=event.invoice_id,
                order_id=event.order_id,
                customer_id=event.customer_id,
                invoice_number=event.invoice_number,
                total=event.total,
                status="Draft",
                created_at=event.generated_at,
                updated_at=event.generated_at,
            )
        )

    @on(InvoiceIssued)
    def on_invoice_issued(self, event):
        repo = current_domain.repository_for(InvoiceStatusView)
        view = repo.get(event.invoice_id)
        view.status = "Issued"
        view.issued_at = event.issued_at
        view.updated_at = event.issued_at
        repo.add(view)

    @on(InvoicePaid)
    def on_invoice_paid(self, event):
        repo = current_domain.repository_for(InvoiceStatusView)
        view = repo.get(event.invoice_id)
        view.status = "Paid"
        view.paid_at = event.paid_at
        view.updated_at = event.paid_at
        repo.add(view)

    @on(InvoiceVoided)
    def on_invoice_voided(self, event):
        repo = current_domain.repository_for(InvoiceStatusView)
        view = repo.get(event.invoice_id)
        view.status = "Voided"
        view.voided_reason = event.reason
        view.updated_at = event.voided_at
        repo.add(view)
