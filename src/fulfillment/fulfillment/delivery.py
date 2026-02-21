"""Fulfillment delivery — commands and handler.

Records delivery confirmation and delivery exceptions from the carrier.
"""

from protean import handle
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment


@fulfillment.command(part_of="Fulfillment")
class RecordDeliveryConfirmation:
    """Record confirmed delivery from the carrier."""

    fulfillment_id = Identifier(required=True)


@fulfillment.command(part_of="Fulfillment")
class RecordDeliveryException:
    """Record a delivery exception from the carrier."""

    fulfillment_id = Identifier(required=True)
    reason = String(required=True, max_length=500)
    location = String(max_length=200)


@fulfillment.command_handler(part_of=Fulfillment)
class DeliveryHandler:
    @handle(RecordDeliveryConfirmation)
    def record_delivery(self, command):
        repo = current_domain.repository_for(Fulfillment)
        ff = repo.get(command.fulfillment_id)
        ff.record_delivery()
        repo.add(ff)

    @handle(RecordDeliveryException)
    def record_exception(self, command):
        repo = current_domain.repository_for(Fulfillment)
        ff = repo.get(command.fulfillment_id)
        ff.record_exception(
            reason=command.reason,
            location=command.location,
        )
        repo.add(ff)
