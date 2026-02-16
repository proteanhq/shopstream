"""Product aggregate root with Variant entity, Image entity, and value objects."""

import json
from datetime import datetime
from enum import Enum

from protean import atomic_change, invariant
from protean.exceptions import ValidationError
from protean.fields import (
    Boolean,
    DateTime,
    Float,
    HasMany,
    Identifier,
    Integer,
    String,
    Text,
    ValueObject,
)

from catalogue.domain import catalogue
from catalogue.shared.sku import SKU

# Status transition ordering for state machine
_STATUS_ORDER = {"Draft": 0, "Active": 1, "Discontinued": 2, "Archived": 3}


class ProductStatus(Enum):
    """Enumeration of product lifecycle statuses."""

    DRAFT = "Draft"
    ACTIVE = "Active"
    DISCONTINUED = "Discontinued"
    ARCHIVED = "Archived"


class ProductVisibility(Enum):
    """Enumeration of product visibility levels."""

    PUBLIC = "Public"
    UNLISTED = "Unlisted"
    TIER_RESTRICTED = "Tier_Restricted"


@catalogue.value_object(part_of="Product")
class Price:
    """Value object for product pricing with tier support."""

    base_price: Float(required=True, min_value=0.01)
    currency: String(max_length=3, default="USD")
    tier_prices: Text()

    @invariant.post
    def tier_prices_must_be_valid(self):
        if not self.tier_prices:
            return

        try:
            tiers = json.loads(self.tier_prices)
        except (json.JSONDecodeError, TypeError):
            raise ValidationError({"tier_prices": ["Tier prices must be valid JSON"]}) from None

        if not isinstance(tiers, dict):
            raise ValidationError({"tier_prices": ["Tier prices must be a JSON object"]})

        for tier_name, price in tiers.items():
            if not isinstance(price, int | float) or price <= 0:
                raise ValidationError({"tier_prices": [f"Tier price for '{tier_name}' must be a positive number"]})
            if price >= self.base_price:
                raise ValidationError(
                    {
                        "tier_prices": [
                            f"Tier price for '{tier_name}' ({price}) must be less than base price ({self.base_price})"
                        ]
                    }
                )


@catalogue.value_object(part_of="Product")
class SEO:
    """Value object for SEO metadata."""

    meta_title: String(max_length=70)
    meta_description: String(max_length=160)
    slug: String(max_length=200)

    @invariant.post
    def slug_must_be_url_safe(self):
        slug = self.slug
        if not slug:
            return

        import re

        if not re.match(r"^[a-z0-9-]+$", slug):
            raise ValidationError({"slug": ["Slug must contain only lowercase alphanumeric characters and hyphens"]})

        if slug.startswith("-") or slug.endswith("-"):
            raise ValidationError({"slug": ["Slug must not start or end with a hyphen"]})

        if "--" in slug:
            raise ValidationError({"slug": ["Slug must not contain consecutive hyphens"]})


@catalogue.value_object(part_of="Product")
class Dimensions:
    """Value object for physical dimensions."""

    length: Float(min_value=0.0)
    width: Float(min_value=0.0)
    height: Float(min_value=0.0)
    unit: String(max_length=2, default="cm")

    @invariant.post
    def unit_must_be_valid(self):
        if self.unit not in ("cm", "in"):
            raise ValidationError({"unit": [f"Dimension unit must be 'cm' or 'in', got '{self.unit}'"]})


@catalogue.value_object(part_of="Product")
class Weight:
    """Value object for physical weight."""

    value: Float(min_value=0.0)
    unit: String(max_length=2, default="kg")

    @invariant.post
    def unit_must_be_valid(self):
        if self.unit not in ("kg", "lb", "g", "oz"):
            raise ValidationError({"unit": [f"Weight unit must be 'kg', 'lb', 'g', or 'oz', got '{self.unit}'"]})


@catalogue.entity(part_of="Product")
class Variant:
    """Product variant entity with unique SKU and pricing."""

    variant_sku: ValueObject(SKU, required=True)
    attributes: Text()
    price: ValueObject(Price, required=True)
    weight: ValueObject(Weight)
    dimensions: ValueObject(Dimensions)
    is_active: Boolean(default=True)


@catalogue.entity(part_of="Product")
class Image:
    """Product image entity."""

    url: String(required=True, max_length=500)
    alt_text: String(max_length=255)
    is_primary: Boolean(default=False)
    display_order: Integer(default=0)


@catalogue.aggregate
class Product:
    """Product aggregate root."""

    sku: ValueObject(SKU, required=True)
    seller_id: Identifier()
    title: String(required=True, max_length=255)
    description: Text()
    category_id: Identifier()
    brand: String(max_length=100)
    attributes: Text()
    variants: HasMany(Variant)
    images: HasMany(Image)
    status: String(choices=ProductStatus, default=ProductStatus.DRAFT.value)
    visibility: String(choices=ProductVisibility, default=ProductVisibility.PUBLIC.value)
    seo: ValueObject(SEO)
    created_at: DateTime(default=datetime.now)
    updated_at: DateTime(default=datetime.now)

    @invariant.post
    def images_cannot_exceed_maximum(self):
        if len(self.images) > 10:
            raise ValidationError({"images": ["Cannot have more than 10 images"]})

    @invariant.post
    def exactly_one_primary_image_when_images_exist(self):
        if not self.images:
            return
        primaries = [i for i in self.images if i.is_primary]
        if len(primaries) != 1:
            raise ValidationError({"images": ["Exactly one image must be marked as primary"]})

    @classmethod
    def create(
        cls,
        sku,
        title,
        seller_id=None,
        category_id=None,
        description=None,
        brand=None,
        attributes=None,
        visibility=None,
        seo=None,
    ):
        from catalogue.product.events import ProductCreated

        sku_vo = SKU(code=sku) if isinstance(sku, str) else sku
        now = datetime.now()
        attrs_json = json.dumps(attributes) if attributes and isinstance(attributes, dict) else attributes

        product = cls(
            sku=sku_vo,
            seller_id=seller_id,
            title=title,
            description=description,
            category_id=category_id,
            brand=brand,
            attributes=attrs_json,
            visibility=visibility or ProductVisibility.PUBLIC.value,
            seo=seo,
            created_at=now,
            updated_at=now,
        )
        product.raise_(
            ProductCreated(
                product_id=product.id,
                sku=sku_vo.code,
                seller_id=seller_id,
                title=title,
                category_id=category_id,
                status=ProductStatus.DRAFT.value,
                created_at=now,
            )
        )
        return product

    def update_details(self, title=None, description=None, brand=None, attributes=None, seo=None):
        from catalogue.product.events import ProductDetailsUpdated

        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if brand is not None:
            self.brand = brand
        if attributes is not None:
            self.attributes = json.dumps(attributes) if isinstance(attributes, dict) else attributes
        if seo is not None:
            self.seo = seo

        self.updated_at = datetime.now()

        self.raise_(
            ProductDetailsUpdated(
                product_id=self.id,
                title=self.title,
                description=self.description,
                brand=self.brand,
            )
        )

    def add_variant(self, variant_sku, price, attributes=None, weight=None, dimensions=None):
        from catalogue.product.events import VariantAdded

        sku_vo = SKU(code=variant_sku) if isinstance(variant_sku, str) else variant_sku
        attrs_json = json.dumps(attributes) if attributes and isinstance(attributes, dict) else attributes

        variant = Variant(
            variant_sku=sku_vo,
            attributes=attrs_json,
            price=price,
            weight=weight,
            dimensions=dimensions,
        )
        self.add_variants(variant)
        self.updated_at = datetime.now()

        self.raise_(
            VariantAdded(
                product_id=self.id,
                variant_id=variant.id,
                variant_sku=sku_vo.code,
                price_amount=price.base_price,
                price_currency=price.currency,
                created_at=datetime.now(),
            )
        )
        return variant

    def update_variant_price(self, variant_id, new_price):
        from catalogue.product.events import VariantPriceChanged

        variant = next((v for v in self.variants if v.id == variant_id), None)
        if variant is None:
            raise ValidationError({"variants": [f"Variant {variant_id} not found"]})

        previous_price = variant.price.base_price
        variant.price = new_price
        self.updated_at = datetime.now()

        self.raise_(
            VariantPriceChanged(
                product_id=self.id,
                variant_id=variant_id,
                previous_price=previous_price,
                new_price=new_price.base_price,
                currency=new_price.currency,
            )
        )

    def set_tier_price(self, variant_id, tier, price):
        from catalogue.product.events import TierPriceSet

        variant = next((v for v in self.variants if v.id == variant_id), None)
        if variant is None:
            raise ValidationError({"variants": [f"Variant {variant_id} not found"]})

        existing_tiers = {}
        if variant.price.tier_prices:
            existing_tiers = json.loads(variant.price.tier_prices)

        existing_tiers[tier] = price

        variant.price = Price(
            base_price=variant.price.base_price,
            currency=variant.price.currency,
            tier_prices=json.dumps(existing_tiers),
        )
        self.updated_at = datetime.now()

        self.raise_(
            TierPriceSet(
                product_id=self.id,
                variant_id=variant_id,
                tier=tier,
                price=price,
                currency=variant.price.currency,
            )
        )

    def add_image(self, url, alt_text=None, is_primary=False):
        from catalogue.product.events import ProductImageAdded

        with atomic_change(self):
            # First image is always primary
            if not self.images:
                is_primary = True

            # If this is set as primary, unset all others
            if is_primary:
                for img in self.images:
                    if img.is_primary:
                        img.is_primary = False

            image = Image(
                url=url,
                alt_text=alt_text,
                is_primary=is_primary,
                display_order=len(self.images),
            )
            self.add_images(image)

        self.updated_at = datetime.now()

        self.raise_(
            ProductImageAdded(
                product_id=self.id,
                image_id=image.id,
                url=url,
                is_primary=str(is_primary),
            )
        )
        return image

    def remove_image(self, image_id):
        from catalogue.product.events import ProductImageRemoved

        image = next((i for i in self.images if i.id == image_id), None)
        if image is None:
            raise ValidationError({"images": [f"Image {image_id} not found"]})

        if len(self.images) <= 1:
            # Allow removing the last image
            self.remove_images(image)
            self.updated_at = datetime.now()
            self.raise_(
                ProductImageRemoved(
                    product_id=self.id,
                    image_id=image_id,
                )
            )
            return

        was_primary = image.is_primary

        with atomic_change(self):
            self.remove_images(image)
            if was_primary and self.images:
                self.images[0].is_primary = True

        self.updated_at = datetime.now()

        self.raise_(
            ProductImageRemoved(
                product_id=self.id,
                image_id=image_id,
            )
        )

    def activate(self):
        from catalogue.product.events import ProductActivated

        if self.status != ProductStatus.DRAFT.value:
            raise ValidationError({"status": ["Only draft products can be activated"]})

        if not self.variants:
            raise ValidationError({"variants": ["Product must have at least one variant to be activated"]})

        self.status = ProductStatus.ACTIVE.value
        now = datetime.now()
        self.updated_at = now

        self.raise_(
            ProductActivated(
                product_id=self.id,
                sku=self.sku.code,
                activated_at=now,
            )
        )

    def discontinue(self):
        from catalogue.product.events import ProductDiscontinued

        if self.status != ProductStatus.ACTIVE.value:
            raise ValidationError({"status": ["Only active products can be discontinued"]})

        self.status = ProductStatus.DISCONTINUED.value
        now = datetime.now()
        self.updated_at = now

        self.raise_(
            ProductDiscontinued(
                product_id=self.id,
                sku=self.sku.code,
                discontinued_at=now,
            )
        )

    def archive(self):
        from catalogue.product.events import ProductArchived

        if self.status != ProductStatus.DISCONTINUED.value:
            raise ValidationError({"status": ["Only discontinued products can be archived"]})

        self.status = ProductStatus.ARCHIVED.value
        now = datetime.now()
        self.updated_at = now

        self.raise_(
            ProductArchived(
                product_id=self.id,
                archived_at=now,
            )
        )
