"""Order fulfillment — commands and handler.

Handles the fulfillment pipeline: processing, shipment (full and partial),
and delivery recording.
"""

import json

from protean import handle
from protean.fields import Identifier, String, Text
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.order import Order


@ordering.command(part_of="Order")
class MarkProcessing:
    """Signal that the warehouse has started picking and packing."""

    order_id = Identifier(required=True)


@ordering.command(part_of="Order")
class RecordShipment:
    """Record that all items have been shipped with a carrier."""

    order_id = Identifier(required=True)
    shipment_id = String(required=True, max_length=255)
    carrier = String(required=True, max_length=100)
    tracking_number = String(required=True, max_length=255)
    shipped_item_ids = Text()  # JSON: list of item ID strings
    estimated_delivery = String(max_length=10)  # ISO date string


@ordering.command(part_of="Order")
class RecordPartialShipment:
    """Record that some (but not all) items have been shipped."""

    order_id = Identifier(required=True)
    shipment_id = String(required=True, max_length=255)
    carrier = String(required=True, max_length=100)
    tracking_number = String(required=True, max_length=255)
    shipped_item_ids = Text(required=True)  # JSON: list of item ID strings


@ordering.command(part_of="Order")
class RecordDelivery:
    """Record that the carrier has confirmed delivery to the customer."""

    order_id = Identifier(required=True)


@ordering.command_handler(part_of=Order)
class RecordFulfillmentHandler:
    @handle(MarkProcessing)
    def mark_processing(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.mark_processing()
        repo.add(order)

    @handle(RecordShipment)
    def record_shipment(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)

        shipped_item_ids = None
        if command.shipped_item_ids:
            shipped_item_ids = (
                json.loads(command.shipped_item_ids)
                if isinstance(command.shipped_item_ids, str)
                else command.shipped_item_ids
            )

        order.record_shipment(
            shipment_id=command.shipment_id,
            carrier=command.carrier,
            tracking_number=command.tracking_number,
            shipped_item_ids=shipped_item_ids,
            estimated_delivery=command.estimated_delivery,
        )
        repo.add(order)

    @handle(RecordPartialShipment)
    def record_partial_shipment(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)

        shipped_item_ids = (
            json.loads(command.shipped_item_ids)
            if isinstance(command.shipped_item_ids, str)
            else command.shipped_item_ids
        )

        order.record_partial_shipment(
            shipment_id=command.shipment_id,
            carrier=command.carrier,
            tracking_number=command.tracking_number,
            shipped_item_ids=shipped_item_ids,
        )
        repo.add(order)

    @handle(RecordDelivery)
    def record_delivery(self, command):
        repo = current_domain.repository_for(Order)
        order = repo.get(command.order_id)
        order.record_delivery()
        repo.add(order)
