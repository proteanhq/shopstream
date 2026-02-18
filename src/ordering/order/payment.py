"""Order payment — commands and handler.

Handles payment lifecycle: pending, success, and failure.
Payment failure returns the order to CONFIRMED state for retry.
"""

from protean import handle
from protean.fields import Float, Identifier, String
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.order import Order


@ordering.command(part_of="Order")
class RecordPaymentPending:
    order_id = Identifier(required=True)
    payment_id = String(required=True, max_length=255)
    payment_method = String(required=True, max_length=50)


@ordering.command(part_of="Order")
class RecordPaymentSuccess:
    order_id = Identifier(required=True)
    payment_id = String(required=True, max_length=255)
    amount = Float(required=True)
    payment_method = String(required=True, max_length=50)


@ordering.command(part_of="Order")
class RecordPaymentFailure:
    order_id = Identifier(required=True)
    payment_id = String(required=True, max_length=255)
    reason = String(required=True, max_length=500)


@ordering.command_handler(part_of=Order)
class RecordPaymentHandler:
    @handle(RecordPaymentPending)
    def record_payment_pending(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.record_payment_pending(
            payment_id=command.payment_id,
            payment_method=command.payment_method,
        )
        repo.add(order)

    @handle(RecordPaymentSuccess)
    def record_payment_success(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.record_payment_success(
            payment_id=command.payment_id,
            amount=command.amount,
            payment_method=command.payment_method,
        )
        repo.add(order)

    @handle(RecordPaymentFailure)
    def record_payment_failure(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.record_payment_failure(
            payment_id=command.payment_id,
            reason=command.reason,
        )
        repo.add(order)
