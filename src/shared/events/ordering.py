"""Cross-domain event contracts for Ordering domain events.

These classes define the event shape for consumption by other domains
(e.g., the Fulfillment domain to cancel in-progress fulfillments when
an order is cancelled). They are registered as external events via
domain.register_external_event() with matching __type__ strings so
Protean's stream deserialization works correctly.

The source-of-truth events are in src/ordering/order/events.py.
"""

from protean.core.event import BaseEvent
from protean.fields import DateTime, Float, Identifier, String, Text


class OrderPaid(BaseEvent):
    """Payment was recorded successfully on the order."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    items = Text(required=True)  # JSON list of order items
    shipping_address = Text()  # JSON address
    grand_total = Float(required=True)
    currency = String(default="USD")
    paid_at = DateTime(required=True)


class OrderCancelled(BaseEvent):
    """An order was cancelled."""

    __version__ = "v1"

    order_id = Identifier(required=True)
    reason = String(required=True)
    cancelled_by = String(required=True)
    cancelled_at = DateTime(required=True)


class OrderDelivered(BaseEvent):
    """An order was delivered to the customer.

    Consumed by the Reviews domain to track verified purchases.
    Note: The source event (Ordering.OrderDelivered.v1) only carries
    order_id and delivered_at. This shared contract adds customer_id
    and items for downstream consumers that need them.
    """

    __version__ = "v1"

    order_id = Identifier(required=True)
    customer_id = Identifier()
    items = Text()  # JSON list of {product_id, variant_id}
    delivered_at = DateTime(required=True)
