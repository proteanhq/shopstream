"""Failed payments — operations monitoring dashboard."""

from datetime import datetime
from decimal import Decimal as D

from protean.core.projector import on
from protean.fields import DateTime, Decimal, Identifier, Integer, String
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.payment.events import (
    PaymentFailed,
    PaymentRetryInitiated,
    PaymentSucceeded,
)
from payments.payment.payment import Payment


@payments.projection
class FailedPayment:
    payment_id: str = Identifier(identifier=True, required=True)
    order_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    amount: D | None = Decimal(precision=19, scale=4)
    reason: str | None = String()
    attempt_number: int | None = Integer()
    status: str = String(required=True)  # failed, retrying, recovered
    failed_at: datetime | None = DateTime()
    updated_at: datetime | None = DateTime()


@payments.projector(projector_for=FailedPayment, aggregates=[Payment])
class FailedPaymentProjector:
    @on(PaymentFailed)
    def on_payment_failed(self, event: PaymentFailed) -> None:
        repo = current_domain.repository_for(FailedPayment)

        record = repo.get_or_none(event.payment_id)
        if record is None:
            record = FailedPayment(
                payment_id=event.payment_id,
                order_id=event.order_id,
                customer_id=event.customer_id,
                status="failed",
            )

        record.amount = event.amount if hasattr(event, "amount") else record.amount
        record.reason = event.reason
        record.attempt_number = event.attempt_number
        record.status = "failed"
        record.failed_at = event.failed_at
        record.updated_at = event.failed_at
        repo.add(record)

    @on(PaymentRetryInitiated)
    def on_payment_retry_initiated(self, event: PaymentRetryInitiated) -> None:
        repo = current_domain.repository_for(FailedPayment)
        record = repo.get_or_none(event.payment_id)
        if record is None:
            return  # No failed record to update
        record.status = "retrying"
        record.attempt_number = event.attempt_number
        record.updated_at = event.retried_at
        repo.add(record)

    @on(PaymentSucceeded)
    def on_payment_succeeded(self, event: PaymentSucceeded) -> None:
        repo = current_domain.repository_for(FailedPayment)
        record = repo.get_or_none(event.payment_id)
        if record is None:
            return  # Not a previously failed payment
        record.status = "recovered"
        record.updated_at = event.succeeded_at
        repo.add(record)
