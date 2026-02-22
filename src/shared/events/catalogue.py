"""Cross-domain event contracts for Catalogue domain events.

These classes define the event shape for consumption by other domains
(e.g., the Inventory domain to initialize stock records, or the Ordering
domain to handle discontinued products). They are registered as external
events via domain.register_external_event() with matching __type__ strings
so Protean's stream deserialization works correctly.

The source-of-truth events are in src/catalogue/product/events.py.
"""

from protean.core.event import BaseEvent
from protean.fields import DateTime, Float, Identifier, String


class ProductCreated(BaseEvent):
    """A new product was added to the catalogue in Draft status."""

    __version__ = "v1"

    product_id = Identifier(required=True)
    sku = String(required=True)
    seller_id = Identifier()
    title = String(required=True)
    category_id = Identifier()
    status = String(required=True)
    created_at = DateTime(required=True)


class VariantAdded(BaseEvent):
    """A new purchasable variant was added to a product."""

    __version__ = "v1"

    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    variant_sku = String(required=True)
    price_amount = Float(required=True)
    price_currency = String(required=True)
    created_at = DateTime(required=True)


class ProductDiscontinued(BaseEvent):
    """An active product was discontinued and removed from sale."""

    __version__ = "v1"

    product_id = Identifier(required=True)
    sku = String(required=True)
    discontinued_at = DateTime(required=True)
