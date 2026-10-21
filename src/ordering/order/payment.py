"""Order payment — commands and handler.

Handles payment lifecycle: pending, success, and failure.
Payment failure returns the order to CONFIRMED state for retry.
"""

from decimal import Decimal as D

from protean import handle
from protean.fields import Decimal, Identifier, String
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.order import Order


@ordering.command(part_of="Order")
class RecordPaymentPending:
    """Record that payment processing has been initiated."""

    order_id: str = Identifier(required=True)
    payment_id: str = String(required=True, max_length=255)
    payment_method: str = String(required=True, max_length=50)


@ordering.command(part_of="Order")
class RecordPaymentSuccess:
    """Record that payment was successfully captured."""

    order_id: str = Identifier(required=True)
    payment_id: str = String(required=True, max_length=255)
    amount: D = Decimal(precision=19, scale=4, required=True)
    payment_method: str = String(required=True, max_length=50)


@ordering.command(part_of="Order")
class RecordPaymentFailure:
    """Record that payment failed, returning the order to Confirmed for retry."""

    order_id: str = Identifier(required=True)
    payment_id: str = String(required=True, max_length=255)
    reason: str = String(required=True, max_length=500)


@ordering.command_handler(part_of=Order)
class RecordPaymentHandler:
    @handle(RecordPaymentPending)
    def record_payment_pending(self, command: RecordPaymentPending) -> None:
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.record_payment_pending(
            payment_id=command.payment_id,
            payment_method=command.payment_method,
        )
        repo.add(order)

    @handle(RecordPaymentSuccess)
    def record_payment_success(self, command: RecordPaymentSuccess) -> None:
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.record_payment_success(
            payment_id=command.payment_id,
            amount=command.amount,
            payment_method=command.payment_method,
        )
        repo.add(order)

    @handle(RecordPaymentFailure)
    def record_payment_failure(self, command: RecordPaymentFailure) -> None:
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.record_payment_failure(
            payment_id=command.payment_id,
            reason=command.reason,
        )
        repo.add(order)
