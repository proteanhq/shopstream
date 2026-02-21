"""Fulfillment tracking — command and handler.

Processes carrier webhook updates to record tracking events.
"""

from protean import handle
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment


@fulfillment.command(part_of="Fulfillment")
class UpdateTrackingEvent:
    """Record a tracking event from the carrier webhook."""

    fulfillment_id = Identifier(required=True)
    status = String(required=True, max_length=100)
    location = String(max_length=200)
    description = String(max_length=500)


@fulfillment.command_handler(part_of=Fulfillment)
class TrackingHandler:
    @handle(UpdateTrackingEvent)
    def update_tracking(self, command):
        repo = current_domain.repository_for(Fulfillment)
        ff = repo.get(command.fulfillment_id)
        ff.add_tracking_event(
            status=command.status,
            location=command.location,
            description=command.description,
        )
        repo.add(ff)
