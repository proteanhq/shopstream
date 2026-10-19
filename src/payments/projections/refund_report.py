"""Refund report — finance reconciliation view."""

from datetime import datetime

from protean.core.projector import on
from protean.fields import DateTime, Float, Identifier, String
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.payment.events import RefundCompleted, RefundRequested
from payments.payment.payment import Payment


@payments.projection
class RefundReport:
    refund_id: str = Identifier(identifier=True, required=True)
    payment_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    amount: float = Float(required=True)
    reason: str | None = String()
    status: str = String(required=True)  # requested, completed
    gateway_refund_id: str | None = String()
    requested_at: datetime | None = DateTime()
    completed_at: datetime | None = DateTime()


@payments.projector(projector_for=RefundReport, aggregates=[Payment])
class RefundReportProjector:
    @on(RefundRequested)
    def on_refund_requested(self, event):
        current_domain.repository_for(RefundReport).add(
            RefundReport(
                refund_id=event.refund_id,
                payment_id=event.payment_id,
                order_id=event.order_id,
                amount=event.amount,
                reason=event.reason,
                status="requested",
                requested_at=event.requested_at,
            )
        )

    @on(RefundCompleted)
    def on_refund_completed(self, event):
        repo = current_domain.repository_for(RefundReport)
        record = repo.get(event.refund_id)
        record.status = "completed"
        record.gateway_refund_id = event.gateway_refund_id
        record.completed_at = event.completed_at
        repo.add(record)
