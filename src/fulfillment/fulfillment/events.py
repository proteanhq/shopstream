"""Fulfillment domain events — immutable facts about fulfillment state changes.

All events are past tense, versioned, and carry sufficient data for
downstream projectors and cross-domain event handlers.
"""

from datetime import datetime
from typing import Any

from protean.fields import DateTime, Dict, Identifier, Integer, List, String

from fulfillment.domain import fulfillment


@fulfillment.event(part_of="Fulfillment")
class FulfillmentCreated:
    """A fulfillment was created for a paid order."""

    fulfillment_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    warehouse_id: str | None = String()
    items: list[dict[str, Any]] = List(Dict(), required=True)
    item_count: int = Integer(required=True)
    created_at: datetime = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class PickerAssigned:
    """A warehouse picker was assigned to a fulfillment."""

    fulfillment_id: str = Identifier(required=True)
    assigned_to: str = String(required=True)
    assigned_at: datetime = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class ItemPicked:
    """A single item was picked from its warehouse location."""

    fulfillment_id: str = Identifier(required=True)
    item_id: str = Identifier(required=True)
    pick_location: str = String(required=True)
    picked_at: datetime = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class PickingCompleted:
    """All items in the pick list have been picked."""

    fulfillment_id: str = Identifier(required=True)
    completed_at: datetime = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class PackingCompleted:
    """Items have been packed into shipping packages."""

    fulfillment_id: str = Identifier(required=True)
    packed_by: str = String(required=True)
    package_count: int = Integer(required=True)
    packed_at: datetime = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class ShippingLabelGenerated:
    """A shipping label was generated for the fulfillment."""

    fulfillment_id: str = Identifier(required=True)
    label_url: str = String(required=True)
    carrier: str = String(required=True)
    service_level: str = String(required=True)
    generated_at: datetime = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment", published=True)
class ShipmentHandedOff:
    """The shipment was handed off to the carrier."""

    fulfillment_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    carrier: str = String(required=True)
    tracking_number: str = String(required=True)
    shipped_item_ids: list[str] = List(String())
    estimated_delivery: datetime | None = DateTime()
    shipped_at: datetime = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class TrackingEventReceived:
    """A tracking event was received from the carrier."""

    fulfillment_id: str = Identifier(required=True)
    status: str = String(required=True)
    location: str | None = String()
    description: str | None = String()
    occurred_at: datetime = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment", published=True)
class DeliveryConfirmed:
    """The carrier confirmed delivery to the customer."""

    fulfillment_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    actual_delivery: datetime = DateTime(required=True)
    delivered_at: datetime = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment", published=True)
class DeliveryException:
    """The carrier reported a delivery exception."""

    fulfillment_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    reason: str = String(required=True)
    location: str | None = String()
    occurred_at: datetime = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class FulfillmentCancelled:
    """The fulfillment was cancelled before shipment."""

    fulfillment_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    reason: str = String(required=True)
    cancelled_at: datetime = DateTime(required=True)
