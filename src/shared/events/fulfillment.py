"""Cross-domain event contracts for Fulfillment domain events.

These classes define the event shape for consumption by other domains
(e.g., the Ordering domain to update Order status, the Inventory domain
to commit reserved stock). They are registered as external events via
domain.register_external_event() with matching __type__ strings so
Protean's stream deserialization works correctly.

The source-of-truth events are in src/fulfillment/fulfillment/events.py.
"""

from protean.core.event import BaseEvent
from protean.fields import DateTime, Identifier, String, Text


class ShipmentHandedOff(BaseEvent):
    """Shipment was handed off to the carrier."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    carrier = String(required=True)
    tracking_number = String(required=True)
    shipped_item_ids = Text()  # JSON list of order item ID strings
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


class FulfillmentCancelled(BaseEvent):
    """Fulfillment was cancelled before shipment."""

    __version__ = "v1"

    fulfillment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    reason = String(required=True)
    cancelled_at = DateTime(required=True)
