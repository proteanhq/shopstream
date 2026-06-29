"""Payment initiation — command and handler.

Creates a new Payment aggregate and initiates a charge via the gateway.
"""

from datetime import timedelta

from protean import handle
from protean.fields import Float, Identifier, String
from protean.utils.globals import current_domain
from protean.utils.logging import bind_event_context
from protean.utils.processing import Priority, processing_priority

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


# A payment authorization has a validity window: a stale InitiatePayment that
# sat queued past it (e.g. an abandoned checkout retried much later) must not
# charge the customer. `timeout` declares that window — the command is rejected
# with CommandExpiredError once `created_at + 15min` passes. `retries`/`backoff`
# add transient-failure resilience when this handler runs on the async Engine.
@payments.command_handler(
    part_of=Payment,
    timeout=timedelta(minutes=15),
    retries=3,
    backoff="exponential",
)
class InitiatePaymentHandler:
    @handle(InitiatePayment)
    def initiate_payment(self, command):
        # Enrich this handler's wide event (protean.access) with business
        # dimensions for revenue/fraud observability — these only the
        # application knows, and they flow through to log aggregators.
        bind_event_context(
            order_id=str(command.order_id),
            amount=command.amount,
            currency=command.currency or "USD",
            payment_method=command.payment_method_type,
        )
        with processing_priority(Priority.CRITICAL):
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
