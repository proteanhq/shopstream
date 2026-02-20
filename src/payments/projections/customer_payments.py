"""Customer payments — payment history by customer."""

from protean.core.projector import on
from protean.fields import DateTime, Float, Identifier, String
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.payment.events import (
    PaymentFailed,
    PaymentInitiated,
    PaymentSucceeded,
    RefundCompleted,
)
from payments.payment.payment import Payment


@payments.projection
class CustomerPayment:
    payment_id = Identifier(identifier=True, required=True)
    customer_id = Identifier(required=True)
    order_id = Identifier(required=True)
    amount = Float()
    currency = String(default="USD")
    status = String(required=True)
    payment_method_type = String()
    created_at = DateTime()
    updated_at = DateTime()


@payments.projector(projector_for=CustomerPayment, aggregates=[Payment])
class CustomerPaymentProjector:
    @on(PaymentInitiated)
    def on_payment_initiated(self, event):
        current_domain.repository_for(CustomerPayment).add(
            CustomerPayment(
                payment_id=event.payment_id,
                customer_id=event.customer_id,
                order_id=event.order_id,
                amount=event.amount,
                currency=event.currency,
                status="Pending",
                payment_method_type=event.payment_method_type,
                created_at=event.initiated_at,
                updated_at=event.initiated_at,
            )
        )

    @on(PaymentSucceeded)
    def on_payment_succeeded(self, event):
        repo = current_domain.repository_for(CustomerPayment)
        view = repo.get(event.payment_id)
        view.status = "Succeeded"
        view.updated_at = event.succeeded_at
        repo.add(view)

    @on(PaymentFailed)
    def on_payment_failed(self, event):
        repo = current_domain.repository_for(CustomerPayment)
        view = repo.get(event.payment_id)
        view.status = "Failed"
        view.updated_at = event.failed_at
        repo.add(view)

    @on(RefundCompleted)
    def on_refund_completed(self, event):
        repo = current_domain.repository_for(CustomerPayment)
        view = repo.get(event.payment_id)
        view.status = "Refunded"
        view.updated_at = event.completed_at
        repo.add(view)
