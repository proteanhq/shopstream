"""Cross-domain event contracts for Fulfillment domain events.

These classes define the event shape for consumption by other domains
(e.g., the Ordering domain to update Order status, the Inventory domain
to commit reserved stock). They are registered as external events via
domain.register_external_event() with matching __type__ strings so
Protean's stream deserialization works correctly.

The source-of-truth events are in src/fulfillment/fulfillment/events.py.
"""

from protean.core.event import BaseEvent
from protean.fields import DateTime, Dict, Identifier, Integer, List, String


class FulfillmentCreated(BaseEvent):
    """A fulfillment was created for a paid order."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    warehouse_id = String()
    items = List(Dict(), required=True)
    item_count = Integer(required=True)
    created_at = DateTime(required=True)


class PickerAssigned(BaseEvent):
    """A warehouse picker was assigned to a fulfillment."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    assigned_to = String(required=True)
    assigned_at = DateTime(required=True)


class ItemPicked(BaseEvent):
    """A single item was picked from its warehouse location."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    item_id = Identifier(required=True)
    pick_location = String(required=True)
    picked_at = DateTime(required=True)


class PickingCompleted(BaseEvent):
    """All items in the pick list have been picked."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    completed_at = DateTime(required=True)


class PackingCompleted(BaseEvent):
    """Items have been packed into shipping packages."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    packed_by = String(required=True)
    package_count = Integer(required=True)
    packed_at = DateTime(required=True)


class ShippingLabelGenerated(BaseEvent):
    """A shipping label was generated for the fulfillment."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    label_url = String(required=True)
    carrier = String(required=True)
    service_level = String(required=True)
    generated_at = DateTime(required=True)


class ShipmentHandedOff(BaseEvent):
    """Shipment was handed off to the carrier."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    carrier = String(required=True)
    tracking_number = String(required=True)
    shipped_item_ids = List(String())
    estimated_delivery = DateTime()
    shipped_at = DateTime(required=True)


class DeliveryConfirmed(BaseEvent):
    """Carrier confirmed delivery to the customer."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    actual_delivery = DateTime(required=True)
    delivered_at = DateTime(required=True)


class DeliveryException(BaseEvent):
    """Carrier reported a delivery exception."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    reason = String(required=True)
    location = String()
    occurred_at = DateTime(required=True)


class TrackingEventReceived(BaseEvent):
    """A tracking event was received from the carrier."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    status = String(required=True)
    location = String()
    description = String()
    occurred_at = DateTime(required=True)


class FulfillmentCancelled(BaseEvent):
    """Fulfillment was cancelled before shipment."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    reason = String(required=True)
    cancelled_at = DateTime(required=True)
