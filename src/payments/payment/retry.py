"""Payment retry — command and handler.

Retries a failed payment (up to MAX_PAYMENT_ATTEMPTS).
"""

from protean import handle
from protean.fields import Identifier
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.payment.payment import Payment


@payments.command(part_of="Payment")
class RetryPayment:
    """Retry a failed payment."""

    payment_id = Identifier(required=True)


@payments.command_handler(part_of=Payment)
class RetryPaymentHandler:
    @handle(RetryPayment)
    def retry_payment(self, command):
        repo = current_domain.repository_for(Payment)
        payment = repo.get(command.payment_id)
        payment.retry()
        repo.add(payment)
