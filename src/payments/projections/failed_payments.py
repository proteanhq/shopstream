"""Failed payments — operations monitoring dashboard."""

from protean.core.projector import on
from protean.fields import DateTime, Float, Identifier, Integer, String
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
    payment_id = Identifier(identifier=True, required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    amount = Float()
    reason = String()
    attempt_number = Integer()
    status = String(required=True)  # failed, retrying, recovered
    failed_at = DateTime()
    updated_at = DateTime()


@payments.projector(projector_for=FailedPayment, aggregates=[Payment])
class FailedPaymentProjector:
    @on(PaymentFailed)
    def on_payment_failed(self, event):
        repo = current_domain.repository_for(FailedPayment)

        try:
            record = repo.get(event.payment_id)
        except Exception:
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
    def on_payment_retry_initiated(self, event):
        repo = current_domain.repository_for(FailedPayment)
        try:
            record = repo.get(event.payment_id)
            record.status = "retrying"
            record.attempt_number = event.attempt_number
            record.updated_at = event.retried_at
            repo.add(record)
        except Exception:
            pass  # No failed record to update

    @on(PaymentSucceeded)
    def on_payment_succeeded(self, event):
        repo = current_domain.repository_for(FailedPayment)
        try:
            record = repo.get(event.payment_id)
            record.status = "recovered"
            record.updated_at = event.succeeded_at
            repo.add(record)
        except Exception:
            pass  # Not a previously failed payment
