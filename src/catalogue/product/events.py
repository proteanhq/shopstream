"""Domain events for the Product aggregate."""

from protean.fields import DateTime, Float, Identifier, String

from catalogue.domain import catalogue

# Cross-cutting events (for future consumers: Inventory, Order, Search)


@catalogue.event(part_of="Product")
class ProductCreated:
    """A new product was added to the catalogue in Draft status."""

    __version__ = "v1"

    product_id: Identifier(required=True)
    sku: String(required=True)
    seller_id: Identifier()
    title: String(required=True)
    category_id: Identifier()
    status: String(required=True)
    created_at: DateTime(required=True)


@catalogue.event(part_of="Product")
class VariantAdded:
    """A new purchasable variant was added to a product."""

    __version__ = "v1"

    product_id: Identifier(required=True)
    variant_id: Identifier(required=True)
    variant_sku: String(required=True)
    price_amount: Float(required=True)
    price_currency: String(required=True)
    created_at: DateTime(required=True)


@catalogue.event(part_of="Product")
class VariantPriceChanged:
    """A variant's base price was updated."""

    __version__ = "v1"

    product_id: Identifier(required=True)
    variant_id: Identifier(required=True)
    previous_price: Float(required=True)
    new_price: Float(required=True)
    currency: String(required=True)


@catalogue.event(part_of="Product")
class TierPriceSet:
    """A loyalty-tier-specific price was set on a variant."""

    __version__ = "v1"

    product_id: Identifier(required=True)
    variant_id: Identifier(required=True)
    tier: String(required=True)
    price: Float(required=True)
    currency: String(required=True)


@catalogue.event(part_of="Product")
class ProductActivated:
    """A draft product was activated and made available for sale."""

    __version__ = "v1"

    product_id: Identifier(required=True)
    sku: String(required=True)
    activated_at: DateTime(required=True)


@catalogue.event(part_of="Product")
class ProductDiscontinued:
    """An active product was discontinued and removed from sale."""

    __version__ = "v1"

    product_id: Identifier(required=True)
    sku: String(required=True)
    discontinued_at: DateTime(required=True)


# Internal events


@catalogue.event(part_of="Product")
class ProductDetailsUpdated:
    """A product's title, description, brand, or attributes were changed."""

    __version__ = "v1"

    product_id: Identifier(required=True)
    title: String(required=True)
    description: String()
    brand: String()


@catalogue.event(part_of="Product")
class ProductImageAdded:
    """A new image was uploaded for a product."""

    __version__ = "v1"

    product_id: Identifier(required=True)
    image_id: Identifier(required=True)
    url: String(required=True)
    is_primary: String(required=True)


@catalogue.event(part_of="Product")
class ProductImageRemoved:
    """An image was removed from a product's gallery."""

    __version__ = "v1"

    product_id: Identifier(required=True)
    image_id: Identifier(required=True)


@catalogue.event(part_of="Product")
class ProductArchived:
    """A discontinued product was archived for permanent storage."""

    __version__ = "v1"

    product_id: Identifier(required=True)
    archived_at: DateTime(required=True)
