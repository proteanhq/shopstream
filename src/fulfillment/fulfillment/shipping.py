"""Fulfillment shipping — command and handler.

Records the carrier handoff when the shipment leaves the warehouse.
"""

from datetime import datetime

from protean import handle
from protean.fields import DateTime, Identifier, String
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment


@fulfillment.command(part_of="Fulfillment")
class RecordHandoff:
    """Record that the shipment has been handed off to the carrier."""

    fulfillment_id: str = Identifier(required=True)
    tracking_number: str = String(required=True, max_length=255)
    estimated_delivery: datetime | None = DateTime()


@fulfillment.command_handler(part_of=Fulfillment)
class ShippingHandler:
    @handle(RecordHandoff)
    def record_handoff(self, command: RecordHandoff) -> None:
        repo = current_domain.repository_for(Fulfillment)
        ff = repo.get(command.fulfillment_id)
        ff.record_handoff(
            tracking_number=command.tracking_number,
            estimated_delivery=command.estimated_delivery,
        )
        repo.add(ff)
