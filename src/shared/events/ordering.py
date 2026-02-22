"""Cross-domain event contracts for Ordering domain events.

These classes define the event shape for consumption by other domains
(e.g., the Fulfillment domain to cancel in-progress fulfillments when
an order is cancelled, or the Notifications domain to send confirmations).
They are registered as external events via domain.register_external_event()
with matching __type__ strings so Protean's stream deserialization works
correctly.

The source-of-truth events are in src/ordering/order/events.py and
src/ordering/cart/events.py.
"""

from protean.core.event import BaseEvent
from protean.fields import DateTime, Float, Identifier, String, Text


class OrderCreated(BaseEvent):
    """A new order was created from a shopping cart at checkout.

    Consumed by the Notifications domain to send order confirmation emails.
    """

    __version__ = "v1"

    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    items = Text(required=True)  # JSON list of item dicts
    grand_total = Float(required=True)
    currency = String(default="USD")
    created_at = DateTime(required=True)


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


class OrderReturned(BaseEvent):
    """Returned items were received back from the customer.

    Consumed by the Inventory domain to restock items and the Payments
    domain to initiate a refund.
    """

    __version__ = "v1"

    order_id = Identifier(required=True)
    customer_id = Identifier()
    returned_item_ids = Text()  # JSON list of item IDs
    items = Text()  # JSON list of {product_id, variant_id, quantity}
    grand_total = Float()
    returned_at = DateTime(required=True)


class CartAbandoned(BaseEvent):
    """A shopping cart was marked as abandoned due to inactivity.

    Consumed by the Notifications domain to send cart recovery emails
    (scheduled 24 hours after abandonment).
    """

    __version__ = "v1"

    cart_id = Identifier(required=True)
    customer_id = Identifier()
    items = Text()  # JSON list of {product_id, variant_id, quantity}
    abandoned_at = DateTime(required=True)
