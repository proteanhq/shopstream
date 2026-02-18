"""Order completion — command and handler."""

from protean import handle
from protean.fields import Identifier
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.order import Order


@ordering.command(part_of="Order")
class CompleteOrder:
    """Finalize a delivered order after the return window has expired."""

    order_id = Identifier(required=True)


@ordering.command_handler(part_of=Order)
class CompleteOrderHandler:
    @handle(CompleteOrder)
    def complete_order(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.complete()
        repo.add(order)
