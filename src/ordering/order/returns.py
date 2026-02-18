"""Order returns — commands and handler.

Handles the return lifecycle: request, approval, and recording.
"""

import json

from protean import handle
from protean.fields import Identifier, String, Text
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.order import Order


@ordering.command(part_of="Order")
class RequestReturn:
    """Request a return of a delivered order, providing a reason."""

    order_id = Identifier(required=True)
    reason = String(required=True, max_length=500)


@ordering.command(part_of="Order")
class ApproveReturn:
    """Approve a pending return request."""

    order_id = Identifier(required=True)


@ordering.command(part_of="Order")
class RecordReturn:
    """Record that returned items have been received back from the customer."""

    order_id = Identifier(required=True)
    returned_item_ids = Text()  # JSON: list of item ID strings (optional — all items if omitted)


@ordering.command_handler(part_of=Order)
class ManageReturnsHandler:
    @handle(RequestReturn)
    def request_return(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.request_return(reason=command.reason)
        repo.add(order)

    @handle(ApproveReturn)
    def approve_return(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.approve_return()
        repo.add(order)

    @handle(RecordReturn)
    def record_return(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)

        returned_item_ids = None
        if command.returned_item_ids:
            returned_item_ids = (
                json.loads(command.returned_item_ids)
                if isinstance(command.returned_item_ids, str)
                else command.returned_item_ids
            )

        order.record_return(returned_item_ids=returned_item_ids)
        repo.add(order)
