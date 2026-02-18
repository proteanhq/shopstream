"""Order confirmation — command and handler."""

from protean import handle
from protean.fields import Identifier
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.order import Order


@ordering.command(part_of="Order")
class ConfirmOrder:
    order_id = Identifier(required=True)


@ordering.command_handler(part_of=Order)
class ConfirmOrderHandler:
    @handle(ConfirmOrder)
    def confirm_order(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.confirm()
        repo.add(order)
