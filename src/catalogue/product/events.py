"""Domain events for the Product aggregate."""

from protean.fields import DateTime, Float, Identifier, String

from catalogue.domain import catalogue

# Cross-cutting events (for future consumers: Inventory, Order, Search)


@catalogue.event(part_of="Product")
class ProductCreated:
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
    __version__ = "v1"

    product_id: Identifier(required=True)
    variant_id: Identifier(required=True)
    variant_sku: String(required=True)
    price_amount: Float(required=True)
    price_currency: String(required=True)
    created_at: DateTime(required=True)


@catalogue.event(part_of="Product")
class VariantPriceChanged:
    __version__ = "v1"

    product_id: Identifier(required=True)
    variant_id: Identifier(required=True)
    previous_price: Float(required=True)
    new_price: Float(required=True)
    currency: String(required=True)


@catalogue.event(part_of="Product")
class TierPriceSet:
    __version__ = "v1"

    product_id: Identifier(required=True)
    variant_id: Identifier(required=True)
    tier: String(required=True)
    price: Float(required=True)
    currency: String(required=True)


@catalogue.event(part_of="Product")
class ProductActivated:
    __version__ = "v1"

    product_id: Identifier(required=True)
    sku: String(required=True)
    activated_at: DateTime(required=True)


@catalogue.event(part_of="Product")
class ProductDiscontinued:
    __version__ = "v1"

    product_id: Identifier(required=True)
    sku: String(required=True)
    discontinued_at: DateTime(required=True)


# Internal events


@catalogue.event(part_of="Product")
class ProductDetailsUpdated:
    __version__ = "v1"

    product_id: Identifier(required=True)
    title: String(required=True)
    description: String()
    brand: String()


@catalogue.event(part_of="Product")
class ProductImageAdded:
    __version__ = "v1"

    product_id: Identifier(required=True)
    image_id: Identifier(required=True)
    url: String(required=True)
    is_primary: String(required=True)


@catalogue.event(part_of="Product")
class ProductImageRemoved:
    __version__ = "v1"

    product_id: Identifier(required=True)
    image_id: Identifier(required=True)


@catalogue.event(part_of="Product")
class ProductArchived:
    __version__ = "v1"

    product_id: Identifier(required=True)
    archived_at: DateTime(required=True)
