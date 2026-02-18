"""Order cancellation and refund — commands and handler."""

from protean import handle
from protean.fields import Float, Identifier, String
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.order import Order


@ordering.command(part_of="Order")
class CancelOrder:
    order_id = Identifier(required=True)
    reason = String(required=True, max_length=500)
    cancelled_by = String(required=True, max_length=50)


@ordering.command(part_of="Order")
class RefundOrder:
    order_id = Identifier(required=True)
    refund_amount = Float()  # Optional — defaults to grand_total


@ordering.command_handler(part_of=Order)
class CancelOrderHandler:
    @handle(CancelOrder)
    def cancel_order(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.cancel(
            reason=command.reason,
            cancelled_by=command.cancelled_by,
        )
        repo.add(order)

    @handle(RefundOrder)
    def refund_order(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.refund(refund_amount=command.refund_amount)
        repo.add(order)
