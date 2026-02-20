"""Refund report — finance reconciliation view."""

from protean.core.projector import on
from protean.fields import DateTime, Float, Identifier, String
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.payment.events import RefundCompleted, RefundRequested
from payments.payment.payment import Payment


@payments.projection
class RefundReport:
    refund_id = Identifier(identifier=True, required=True)
    payment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    amount = Float(required=True)
    reason = String()
    status = String(required=True)  # requested, completed
    gateway_refund_id = String()
    requested_at = DateTime()
    completed_at = DateTime()


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
