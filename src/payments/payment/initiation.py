"""Payment initiation — command and handler.

Creates a new Payment aggregate and initiates a charge via the gateway.
"""

from protean import handle
from protean.fields import Float, Identifier, String
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.gateway import get_gateway
from payments.payment.payment import Payment


@payments.command(part_of="Payment")
class InitiatePayment:
    """Initiate a new payment for an order."""

    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    amount = Float(required=True)
    currency = String(max_length=3, default="USD")
    payment_method_type = String(required=True, max_length=50)
    last4 = String(max_length=4)
    idempotency_key = String(required=True, max_length=255)


@payments.command_handler(part_of=Payment)
class InitiatePaymentHandler:
    @handle(InitiatePayment)
    def initiate_payment(self, command):
        gateway = get_gateway()

        payment = Payment.create(
            order_id=command.order_id,
            customer_id=command.customer_id,
            amount=command.amount,
            currency=command.currency or "USD",
            payment_method_type=command.payment_method_type,
            last4=command.last4,
            gateway_name=type(gateway).__name__,
            idempotency_key=command.idempotency_key,
        )
        current_domain.repository_for(Payment).add(payment)
        return str(payment.id)
