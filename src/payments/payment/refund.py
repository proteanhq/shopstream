"""Payment refund — commands and handler.

Handles refund requests and gateway refund confirmations.
"""

from protean import handle
from protean.fields import Float, Identifier, String
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.payment.payment import Payment


@payments.command(part_of="Payment")
class RequestRefund:
    """Request a refund for a payment."""

    payment_id: str = Identifier(required=True)
    amount: float = Float(required=True)
    reason: str = String(required=True, max_length=500)


@payments.command(part_of="Payment")
class ProcessRefundWebhook:
    """Process a refund confirmation from the gateway."""

    payment_id: str = Identifier(required=True)
    refund_id: str = Identifier(required=True)
    gateway_refund_id: str = String(required=True, max_length=255)


@payments.command_handler(part_of=Payment)
class RefundHandler:
    @handle(RequestRefund)
    def request_refund(self, command: RequestRefund) -> str:
        repo = current_domain.repository_for(Payment)
        payment = repo.get(command.payment_id)
        refund_id: str = payment.request_refund(
            amount=command.amount,
            reason=command.reason,
        )
        repo.add(payment)
        return refund_id

    @handle(ProcessRefundWebhook)
    def process_refund_webhook(self, command: ProcessRefundWebhook) -> None:
        repo = current_domain.repository_for(Payment)
        payment = repo.get(command.payment_id)
        payment.complete_refund(
            refund_id=command.refund_id,
            gateway_refund_id=command.gateway_refund_id,
        )
        repo.add(payment)
