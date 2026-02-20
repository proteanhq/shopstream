"""Payment status — real-time payment state view."""

from protean.core.projector import on
from protean.fields import DateTime, Float, Identifier, Integer, String
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.payment.events import (
    PaymentFailed,
    PaymentInitiated,
    PaymentRetryInitiated,
    PaymentSucceeded,
    RefundCompleted,
    RefundRequested,
)
from payments.payment.payment import Payment


@payments.projection
class PaymentStatusView:
    payment_id = Identifier(identifier=True, required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    amount = Float()
    currency = String(default="USD")
    status = String(required=True)
    gateway_transaction_id = String()
    attempt_count = Integer(default=1)
    failure_reason = String()
    total_refunded = Float(default=0.0)
    created_at = DateTime()
    updated_at = DateTime()


@payments.projector(projector_for=PaymentStatusView, aggregates=[Payment])
class PaymentStatusProjector:
    @on(PaymentInitiated)
    def on_payment_initiated(self, event):
        current_domain.repository_for(PaymentStatusView).add(
            PaymentStatusView(
                payment_id=event.payment_id,
                order_id=event.order_id,
                customer_id=event.customer_id,
                amount=event.amount,
                currency=event.currency,
                status="Pending",
                attempt_count=1,
                created_at=event.initiated_at,
                updated_at=event.initiated_at,
            )
        )

    @on(PaymentSucceeded)
    def on_payment_succeeded(self, event):
        repo = current_domain.repository_for(PaymentStatusView)
        view = repo.get(event.payment_id)
        view.status = "Succeeded"
        view.gateway_transaction_id = event.gateway_transaction_id
        view.updated_at = event.succeeded_at
        repo.add(view)

    @on(PaymentFailed)
    def on_payment_failed(self, event):
        repo = current_domain.repository_for(PaymentStatusView)
        view = repo.get(event.payment_id)
        view.status = "Failed"
        view.failure_reason = event.reason
        view.attempt_count = event.attempt_number
        view.updated_at = event.failed_at
        repo.add(view)

    @on(PaymentRetryInitiated)
    def on_payment_retry_initiated(self, event):
        repo = current_domain.repository_for(PaymentStatusView)
        view = repo.get(event.payment_id)
        view.status = "Pending"
        view.attempt_count = event.attempt_number
        view.failure_reason = None
        view.updated_at = event.retried_at
        repo.add(view)

    @on(RefundRequested)
    def on_refund_requested(self, event):
        repo = current_domain.repository_for(PaymentStatusView)
        view = repo.get(event.payment_id)
        view.updated_at = event.requested_at
        repo.add(view)

    @on(RefundCompleted)
    def on_refund_completed(self, event):
        repo = current_domain.repository_for(PaymentStatusView)
        view = repo.get(event.payment_id)
        view.total_refunded = (view.total_refunded or 0.0) + event.amount
        if view.total_refunded >= view.amount:
            view.status = "Refunded"
        else:
            view.status = "Partially_Refunded"
        view.updated_at = event.completed_at
        repo.add(view)
