"""Product detail — full PDP (Product Detail Page) projection."""

from datetime import datetime
from typing import Any

from protean.core.projector import on
from protean.fields import DateTime, Dict, Identifier, List, String, Text
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.product.events import (
    ProductActivated,
    ProductArchived,
    ProductCreated,
    ProductDetailsUpdated,
    ProductDiscontinued,
    ProductImageAdded,
    ProductImageRemoved,
    TierPriceSet,
    VariantAdded,
    VariantPriceChanged,
)
from catalogue.product.product import Product


@catalogue.projection
class ProductDetail:
    product_id: str = Identifier(identifier=True, required=True)
    sku: str = String(required=True)
    seller_id: str | None = Identifier()
    title: str = String(required=True)
    description: str | None = Text()
    category_id: str | None = Identifier()
    brand: str | None = String()
    attributes: dict[str, Any] = Dict()
    variants: list[dict[str, Any]] = List(Dict())
    images: list[dict[str, Any]] = List(Dict())
    status: str = String(required=True)
    visibility: str | None = String()
    meta_title: str | None = String()
    meta_description: str | None = String()
    slug: str | None = String()
    created_at: datetime | None = DateTime()
    updated_at: datetime | None = DateTime()


@catalogue.projector(projector_for=ProductDetail, aggregates=[Product], idempotent=True)
class ProductDetailProjector:
    @on(ProductCreated)
    def on_product_created(self, event: ProductCreated) -> None:
        current_domain.repository_for(ProductDetail).add(
            ProductDetail(
                product_id=event.product_id,
                sku=event.sku,
                seller_id=event.seller_id,
                title=event.title,
                category_id=event.category_id,
                status=event.status,
                variants=[],
                images=[],
                created_at=event.created_at,
                updated_at=event.created_at,
            )
        )

    @on(ProductDetailsUpdated)
    def on_details_updated(self, event: ProductDetailsUpdated) -> None:
        repo = current_domain.repository_for(ProductDetail)
        detail = repo.get(event.product_id)
        detail.title = event.title
        if event.description is not None:
            detail.description = event.description
        if event.brand is not None:
            detail.brand = event.brand
        repo.add(detail)

    @on(VariantAdded)
    def on_variant_added(self, event: VariantAdded) -> None:
        repo = current_domain.repository_for(ProductDetail)
        detail = repo.get(event.product_id)
        variants = list(detail.variants or [])
        variants.append(
            {
                "variant_id": event.variant_id,
                "variant_sku": event.variant_sku,
                "price_amount": event.price_amount,
                "price_currency": event.price_currency,
            }
        )
        detail.variants = variants
        repo.add(detail)

    @on(VariantPriceChanged)
    def on_variant_price_changed(self, event: VariantPriceChanged) -> None:
        repo = current_domain.repository_for(ProductDetail)
        detail = repo.get(event.product_id)
        variants = list(detail.variants or [])
        for v in variants:
            if v["variant_id"] == event.variant_id:
                v["price_amount"] = event.new_price
                v["price_currency"] = event.currency
                break
        detail.variants = variants
        repo.add(detail)

    @on(TierPriceSet)
    def on_tier_price_set(self, event: TierPriceSet) -> None:
        repo = current_domain.repository_for(ProductDetail)
        detail = repo.get(event.product_id)
        variants = list(detail.variants or [])
        for v in variants:
            if v["variant_id"] == event.variant_id:
                tier_prices = v.get("tier_prices", {})
                tier_prices[event.tier] = event.price
                v["tier_prices"] = tier_prices
                break
        detail.variants = variants
        repo.add(detail)

    @on(ProductImageAdded)
    def on_image_added(self, event: ProductImageAdded) -> None:
        repo = current_domain.repository_for(ProductDetail)
        detail = repo.get(event.product_id)
        images = list(detail.images or [])
        images.append(
            {
                "image_id": event.image_id,
                "url": event.url,
                "is_primary": event.is_primary,
            }
        )
        detail.images = images
        repo.add(detail)

    @on(ProductImageRemoved)
    def on_image_removed(self, event: ProductImageRemoved) -> None:
        repo = current_domain.repository_for(ProductDetail)
        detail = repo.get(event.product_id)
        images = list(detail.images or [])
        images = [i for i in images if i["image_id"] != event.image_id]
        detail.images = images
        repo.add(detail)

    @on(ProductActivated)
    def on_product_activated(self, event: ProductActivated) -> None:
        repo = current_domain.repository_for(ProductDetail)
        detail = repo.get(event.product_id)
        detail.status = "Active"
        repo.add(detail)

    @on(ProductDiscontinued)
    def on_product_discontinued(self, event: ProductDiscontinued) -> None:
        repo = current_domain.repository_for(ProductDetail)
        detail = repo.get(event.product_id)
        detail.status = "Discontinued"
        repo.add(detail)

    @on(ProductArchived)
    def on_product_archived(self, event: ProductArchived) -> None:
        repo = current_domain.repository_for(ProductDetail)
        detail = repo.get(event.product_id)
        detail.status = "Archived"
        repo.add(detail)
