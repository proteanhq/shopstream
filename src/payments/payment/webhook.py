"""Payment webhook processing — command and handler.

Handles gateway webhook callbacks for payment success/failure.
"""

from protean import handle
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.payment.payment import Payment


@payments.command(part_of="Payment")
class ProcessPaymentWebhook:
    """Process a payment gateway webhook callback."""

    payment_id = Identifier(required=True)
    gateway_transaction_id = String(max_length=255)
    gateway_status = String(required=True, max_length=50)  # succeeded, failed
    failure_reason = String(max_length=500)


@payments.command_handler(part_of=Payment)
class ProcessWebhookHandler:
    @handle(ProcessPaymentWebhook)
    def process_webhook(self, command):
        repo = current_domain.repository_for(Payment)
        payment = repo.get(command.payment_id)

        if command.gateway_status == "succeeded":
            payment.record_success(
                gateway_transaction_id=command.gateway_transaction_id,
            )
        else:
            payment.record_failure(
                reason=command.failure_reason or "Unknown failure",
            )

        repo.add(payment)
