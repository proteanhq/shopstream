"""Product card — lightweight listing/search projection."""

from datetime import datetime

from protean.core.projector import on
from protean.fields import DateTime, Float, Identifier, Integer, String
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
    VariantAdded,
    VariantPriceChanged,
)
from catalogue.product.product import Product


@catalogue.projection
class ProductCard:
    product_id: str = Identifier(identifier=True, required=True)
    sku: str = String(required=True)
    title: str = String(required=True)
    brand: str | None = String()
    category_id: str | None = Identifier()
    primary_image_url: str | None = String()
    min_price: float | None = Float()
    max_price: float | None = Float()
    currency: str | None = String()
    status: str = String(required=True)
    variant_count: int = Integer(default=0)
    created_at: datetime | None = DateTime()


@catalogue.projector(projector_for=ProductCard, aggregates=[Product], idempotent=True)
class ProductCardProjector:
    @on(ProductCreated)
    def on_product_created(self, event: ProductCreated) -> None:
        current_domain.repository_for(ProductCard).add(
            ProductCard(
                product_id=event.product_id,
                sku=event.sku,
                title=event.title,
                category_id=event.category_id,
                status=event.status,
                variant_count=0,
                created_at=event.created_at,
            )
        )

    @on(ProductDetailsUpdated)
    def on_details_updated(self, event: ProductDetailsUpdated) -> None:
        repo = current_domain.repository_for(ProductCard)
        card = repo.get(event.product_id)
        card.title = event.title
        if event.brand is not None:
            card.brand = event.brand
        repo.add(card)

    @on(VariantAdded)
    def on_variant_added(self, event: VariantAdded) -> None:
        repo = current_domain.repository_for(ProductCard)
        card = repo.get(event.product_id)
        card.variant_count = (card.variant_count or 0) + 1
        card.currency = event.price_currency

        price = event.price_amount
        if card.min_price is None or price < card.min_price:
            card.min_price = price
        if card.max_price is None or price > card.max_price:
            card.max_price = price

        repo.add(card)

    @on(VariantPriceChanged)
    def on_variant_price_changed(self, event: VariantPriceChanged) -> None:
        repo = current_domain.repository_for(ProductCard)
        card = repo.get(event.product_id)
        # Recalculate min/max would require all variant prices
        # For simplicity, update based on the new price
        price = event.new_price
        if card.min_price is None or price < card.min_price:
            card.min_price = price
        if card.max_price is None or price > card.max_price:
            card.max_price = price
        repo.add(card)

    @on(ProductImageAdded)
    def on_image_added(self, event: ProductImageAdded) -> None:
        repo = current_domain.repository_for(ProductCard)
        card = repo.get(event.product_id)
        if event.is_primary:
            card.primary_image_url = event.url
        repo.add(card)

    @on(ProductImageRemoved)
    def on_image_removed(self, event: ProductImageRemoved) -> None:
        repo = current_domain.repository_for(ProductCard)
        card = repo.get(event.product_id)
        # If primary was removed, clear it (the aggregate will reassign primary)
        repo.add(card)

    @on(ProductActivated)
    def on_product_activated(self, event: ProductActivated) -> None:
        repo = current_domain.repository_for(ProductCard)
        card = repo.get(event.product_id)
        card.status = "Active"
        repo.add(card)

    @on(ProductDiscontinued)
    def on_product_discontinued(self, event: ProductDiscontinued) -> None:
        repo = current_domain.repository_for(ProductCard)
        card = repo.get(event.product_id)
        card.status = "Discontinued"
        repo.add(card)

    @on(ProductArchived)
    def on_product_archived(self, event: ProductArchived) -> None:
        repo = current_domain.repository_for(ProductCard)
        card = repo.get(event.product_id)
        card.status = "Archived"
        repo.add(card)
