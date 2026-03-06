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

    product_id = Identifier(required=True)
    sku = String(required=True)
    seller_id = Identifier()
    title = String(required=True)
    category_id = Identifier()
    status = String(required=True)
    created_at = DateTime(required=True)


class VariantAdded(BaseEvent):
    """A new purchasable variant was added to a product."""

    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    variant_sku = String(required=True)
    price_amount = Float(required=True)
    price_currency = String(required=True)
    created_at = DateTime(required=True)


class VariantPriceChanged(BaseEvent):
    """A variant's base price was updated."""

    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    previous_price = Float(required=True)
    new_price = Float(required=True)
    currency = String(required=True)


class TierPriceSet(BaseEvent):
    """A loyalty-tier-specific price was set on a variant."""

    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    tier = String(required=True)
    price = Float(required=True)
    currency = String(required=True)


class ProductActivated(BaseEvent):
    """A draft product was activated and made available for sale."""

    product_id = Identifier(required=True)
    sku = String(required=True)
    activated_at = DateTime(required=True)


class ProductDiscontinued(BaseEvent):
    """An active product was discontinued and removed from sale."""

    product_id = Identifier(required=True)
    sku = String(required=True)
    discontinued_at = DateTime(required=True)


class ProductDetailsUpdated(BaseEvent):
    """A product's title, description, brand, or attributes were changed."""

    product_id = Identifier(required=True)
    title = String(required=True)
    description = String()
    brand = String()


class ProductImageAdded(BaseEvent):
    """A new image was uploaded for a product."""

    product_id = Identifier(required=True)
    image_id = Identifier(required=True)
    url = String(required=True)
    is_primary = String(required=True)


class ProductImageRemoved(BaseEvent):
    """An image was removed from a product's gallery."""

    product_id = Identifier(required=True)
    image_id = Identifier(required=True)


class ProductArchived(BaseEvent):
    """A discontinued product was archived for permanent storage."""

    product_id = Identifier(required=True)
    archived_at = DateTime(required=True)
