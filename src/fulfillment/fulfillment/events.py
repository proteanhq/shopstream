"""Fulfillment domain events — immutable facts about fulfillment state changes.

All events are past tense, versioned, and carry sufficient data for
downstream projectors and cross-domain event handlers.
"""

from protean.fields import DateTime, Identifier, Integer, String, Text

from fulfillment.domain import fulfillment


@fulfillment.event(part_of="Fulfillment")
class FulfillmentCreated:
    """A fulfillment was created for a paid order."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    warehouse_id = String()
    items = Text(required=True)  # JSON list of item dicts
    item_count = Integer(required=True)
    created_at = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class PickerAssigned:
    """A warehouse picker was assigned to a fulfillment."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    assigned_to = String(required=True)
    assigned_at = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class ItemPicked:
    """A single item was picked from its warehouse location."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    item_id = Identifier(required=True)
    pick_location = String(required=True)
    picked_at = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class PickingCompleted:
    """All items in the pick list have been picked."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    completed_at = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class PackingCompleted:
    """Items have been packed into shipping packages."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    packed_by = String(required=True)
    package_count = Integer(required=True)
    packed_at = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class ShippingLabelGenerated:
    """A shipping label was generated for the fulfillment."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    label_url = String(required=True)
    carrier = String(required=True)
    service_level = String(required=True)
    generated_at = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class ShipmentHandedOff:
    """The shipment was handed off to the carrier."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    carrier = String(required=True)
    tracking_number = String(required=True)
    shipped_item_ids = Text()  # JSON list of order item ID strings
    estimated_delivery = DateTime()
    shipped_at = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class TrackingEventReceived:
    """A tracking event was received from the carrier."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    status = String(required=True)
    location = String()
    description = String()
    occurred_at = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class DeliveryConfirmed:
    """The carrier confirmed delivery to the customer."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    actual_delivery = DateTime(required=True)
    delivered_at = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class DeliveryException:
    """The carrier reported a delivery exception."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    reason = String(required=True)
    location = String()
    occurred_at = DateTime(required=True)


@fulfillment.event(part_of="Fulfillment")
class FulfillmentCancelled:
    """The fulfillment was cancelled before shipment."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    reason = String(required=True)
    cancelled_at = DateTime(required=True)
