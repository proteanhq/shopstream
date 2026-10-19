"""Domain events for the Product aggregate."""

from datetime import datetime

from protean.fields import Boolean, DateTime, Float, Identifier, String

from catalogue.domain import catalogue

# Cross-cutting events (for future consumers: Inventory, Order, Search)


@catalogue.event(part_of="Product", published=True)
class ProductCreated:
    """A new product was added to the catalogue in Draft status."""

    product_id: str = Identifier(required=True)
    sku: str = String(required=True)
    seller_id: str | None = Identifier()
    title: str = String(required=True)
    category_id: str | None = Identifier()
    status: str = String(required=True)
    created_at: datetime = DateTime(required=True)


@catalogue.event(part_of="Product", published=True)
class VariantAdded:
    """A new purchasable variant was added to a product."""

    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    variant_sku: str = String(required=True)
    price_amount: float = Float(required=True)
    price_currency: str = String(required=True)
    created_at: datetime = DateTime(required=True)


@catalogue.event(part_of="Product")
class VariantPriceChanged:
    """A variant's base price was updated."""

    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    previous_price: float = Float(required=True)
    new_price: float = Float(required=True)
    currency: str = String(required=True)


@catalogue.event(part_of="Product")
class TierPriceSet:
    """A loyalty-tier-specific price was set on a variant."""

    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    tier: str = String(required=True)
    price: float = Float(required=True)
    currency: str = String(required=True)


@catalogue.event(part_of="Product")
class ProductActivated:
    """A draft product was activated and made available for sale."""

    product_id: str = Identifier(required=True)
    sku: str = String(required=True)
    activated_at: datetime = DateTime(required=True)


@catalogue.event(part_of="Product", published=True)
class ProductDiscontinued:
    """An active product was discontinued and removed from sale."""

    product_id: str = Identifier(required=True)
    sku: str = String(required=True)
    discontinued_at: datetime = DateTime(required=True)


# Internal events


@catalogue.event(part_of="Product")
class ProductDetailsUpdated:
    """A product's title, description, brand, or attributes were changed."""

    product_id: str = Identifier(required=True)
    title: str = String(required=True)
    description: str | None = String()
    brand: str | None = String()


@catalogue.event(part_of="Product")
class ProductImageAdded:
    """A new image was uploaded for a product."""

    product_id: str = Identifier(required=True)
    image_id: str = Identifier(required=True)
    url: str = String(required=True)
    is_primary: bool = Boolean(required=True)


@catalogue.event(part_of="Product")
class ProductImageRemoved:
    """An image was removed from a product's gallery."""

    product_id: str = Identifier(required=True)
    image_id: str = Identifier(required=True)


@catalogue.event(part_of="Product")
class ProductArchived:
    """A discontinued product was archived for permanent storage."""

    product_id: str = Identifier(required=True)
    archived_at: datetime = DateTime(required=True)
