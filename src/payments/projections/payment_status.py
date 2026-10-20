"""Payment status — real-time payment state view."""

from datetime import datetime
from decimal import Decimal as D

from protean.core.projector import on
from protean.fields import DateTime, Decimal, Identifier, Integer, String
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.payment.events import (
    PaymentFailed,
    PaymentInitiated,
    PaymentProcessing,
    PaymentRetryInitiated,
    PaymentSucceeded,
    RefundCompleted,
    RefundRequested,
)
from payments.payment.payment import Payment
from shared.money import to_money


@payments.projection
class PaymentStatusView:
    payment_id: str = Identifier(identifier=True, required=True)
    order_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    amount: D | None = Decimal(precision=19, scale=4)
    currency: str = String(default="USD")
    status: str = String(required=True)
    gateway_transaction_id: str | None = String()
    attempt_count: int = Integer(default=1)
    failure_reason: str | None = String()
    total_refunded: D = Decimal(precision=19, scale=4, default=D("0"))
    created_at: datetime | None = DateTime()
    updated_at: datetime | None = DateTime()


@payments.projector(projector_for=PaymentStatusView, aggregates=[Payment], idempotent=True)
class PaymentStatusProjector:
    @on(PaymentInitiated)
    def on_payment_initiated(self, event: PaymentInitiated) -> None:
        current_domain.repository_for(PaymentStatusView).add(
            PaymentStatusView(
                payment_id=event.payment_id,
                order_id=event.order_id,
                customer_id=event.customer_id,
                amount=to_money(event.amount),
                currency=event.currency,
                status="Pending",
                attempt_count=1,
                created_at=event.initiated_at,
                updated_at=event.initiated_at,
            )
        )

    @on(PaymentProcessing)
    def on_payment_processing(self, event: PaymentProcessing) -> None:
        repo = current_domain.repository_for(PaymentStatusView)
        view = repo.get(event.payment_id)
        view.status = "Processing"
        view.updated_at = event.processing_at
        repo.add(view)

    @on(PaymentSucceeded)
    def on_payment_succeeded(self, event: PaymentSucceeded) -> None:
        repo = current_domain.repository_for(PaymentStatusView)
        view = repo.get(event.payment_id)
        view.status = "Succeeded"
        view.gateway_transaction_id = event.gateway_transaction_id
        view.updated_at = event.succeeded_at
        repo.add(view)

    @on(PaymentFailed)
    def on_payment_failed(self, event: PaymentFailed) -> None:
        repo = current_domain.repository_for(PaymentStatusView)
        view = repo.get(event.payment_id)
        view.status = "Failed"
        view.failure_reason = event.reason
        view.attempt_count = event.attempt_number
        view.updated_at = event.failed_at
        repo.add(view)

    @on(PaymentRetryInitiated)
    def on_payment_retry_initiated(self, event: PaymentRetryInitiated) -> None:
        repo = current_domain.repository_for(PaymentStatusView)
        view = repo.get(event.payment_id)
        view.status = "Pending"
        view.attempt_count = event.attempt_number
        view.failure_reason = None
        view.updated_at = event.retried_at
        repo.add(view)

    @on(RefundRequested)
    def on_refund_requested(self, event: RefundRequested) -> None:
        repo = current_domain.repository_for(PaymentStatusView)
        view = repo.get(event.payment_id)
        view.updated_at = event.requested_at
        repo.add(view)

    @on(RefundCompleted)
    def on_refund_completed(self, event: RefundCompleted) -> None:
        repo = current_domain.repository_for(PaymentStatusView)
        view = repo.get(event.payment_id)
        view.total_refunded = to_money(view.total_refunded) + to_money(event.amount)
        if view.total_refunded >= view.amount:
            view.status = "Refunded"
        else:
            view.status = "Partially_Refunded"
        view.updated_at = event.completed_at
        repo.add(view)
