"""Seller catalogue — seller's product management projection."""

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.product.events import (
    ProductActivated,
    ProductArchived,
    ProductCreated,
    ProductDetailsUpdated,
    ProductDiscontinued,
    VariantAdded,
)
from catalogue.product.product import Product


@catalogue.projection
class SellerCatalogue:
    product_id: Identifier(identifier=True, required=True)
    seller_id: Identifier()
    sku: String(required=True)
    title: String(required=True)
    status: String(required=True)
    variant_count: Integer(default=0)
    created_at: DateTime()
    updated_at: DateTime()


@catalogue.projector(projector_for=SellerCatalogue, aggregates=[Product])
class SellerCatalogueProjector:
    @on(ProductCreated)
    def on_product_created(self, event):
        current_domain.repository_for(SellerCatalogue).add(
            SellerCatalogue(
                product_id=event.product_id,
                seller_id=event.seller_id,
                sku=event.sku,
                title=event.title,
                status=event.status,
                variant_count=0,
                created_at=event.created_at,
                updated_at=event.created_at,
            )
        )

    @on(ProductDetailsUpdated)
    def on_details_updated(self, event):
        repo = current_domain.repository_for(SellerCatalogue)
        record = repo.get(event.product_id)
        record.title = event.title
        repo.add(record)

    @on(VariantAdded)
    def on_variant_added(self, event):
        repo = current_domain.repository_for(SellerCatalogue)
        record = repo.get(event.product_id)
        record.variant_count = (record.variant_count or 0) + 1
        repo.add(record)

    @on(ProductActivated)
    def on_product_activated(self, event):
        repo = current_domain.repository_for(SellerCatalogue)
        record = repo.get(event.product_id)
        record.status = "Active"
        repo.add(record)

    @on(ProductDiscontinued)
    def on_product_discontinued(self, event):
        repo = current_domain.repository_for(SellerCatalogue)
        record = repo.get(event.product_id)
        record.status = "Discontinued"
        repo.add(record)

    @on(ProductArchived)
    def on_product_archived(self, event):
        repo = current_domain.repository_for(SellerCatalogue)
        record = repo.get(event.product_id)
        record.status = "Archived"
        repo.add(record)
