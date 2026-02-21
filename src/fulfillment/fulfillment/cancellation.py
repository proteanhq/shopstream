"""Fulfillment cancellation — command and handler.

Cancels a fulfillment that has not yet been shipped.
"""

from protean import handle
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment


@fulfillment.command(part_of="Fulfillment")
class CancelFulfillment:
    """Cancel a fulfillment before it has been shipped."""

    fulfillment_id = Identifier(required=True)
    reason = String(required=True, max_length=500)


@fulfillment.command_handler(part_of=Fulfillment)
class CancelFulfillmentHandler:
    @handle(CancelFulfillment)
    def cancel_fulfillment(self, command):
        repo = current_domain.repository_for(Fulfillment)
        ff = repo.get(command.fulfillment_id)
        ff.cancel(command.reason)
        repo.add(ff)
