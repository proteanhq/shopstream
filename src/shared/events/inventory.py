"""Cross-domain event contracts for Inventory domain events.

These classes define the event shape for consumption by other domains
(e.g., the OrderCheckoutSaga in the ordering domain). They are registered
as external events via domain.register_external_event() with matching
__type__ strings so Protean's stream deserialization works correctly.

The source-of-truth events are in src/inventory/stock/events.py.
"""

from protean.core.event import BaseEvent
from protean.fields import DateTime, Identifier, Integer, String


class StockReserved(BaseEvent):
    """Stock was reserved for an order."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    reservation_id = Identifier(required=True)
    order_id = Identifier(required=True)
    quantity = Integer(required=True)
    previous_available = Integer(required=True)
    new_available = Integer(required=True)
    reserved_at = DateTime(required=True)
    expires_at = DateTime(required=True)


class ReservationReleased(BaseEvent):
    """A stock reservation was released."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    reservation_id = Identifier(required=True)
    order_id = Identifier(required=True)
    quantity = Integer(required=True)
    reason = String(required=True)
    previous_available = Integer(required=True)
    new_available = Integer(required=True)
    released_at = DateTime(required=True)
