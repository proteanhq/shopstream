"""Category products projection — products grouped by category for browse pages.

Maintains a denormalized view of products per category, updated as products
are created, activated, discontinued, or archived.
"""

import json

from protean.core.projector import on
from protean.exceptions import ObjectNotFoundError
from protean.fields import DateTime, Identifier, Integer, String, Text
from protean.utils.globals import current_domain

from catalogue.category.category import Category
from catalogue.category.events import CategoryCreated
from catalogue.domain import catalogue
from catalogue.product.events import (
    ProductActivated,
    ProductArchived,
    ProductCreated,
    ProductDetailsUpdated,
    ProductDiscontinued,
)
from catalogue.product.product import Product


@catalogue.projection
class CategoryProducts:
    category_id = Identifier(identifier=True, required=True)
    category_name = String(required=True, max_length=255)
    product_count = Integer(default=0)
    products = Text(default="[]")  # JSON list of product summaries
    updated_at = DateTime()


@catalogue.projector(projector_for=CategoryProducts, aggregates=[Product, Category])
class CategoryProductsProjector:
    @on(CategoryCreated)
    def on_category_created(self, event):
        current_domain.repository_for(CategoryProducts).add(
            CategoryProducts(
                category_id=event.category_id,
                category_name=event.name,
                product_count=0,
                products="[]",
            )
        )

    @on(ProductCreated)
    def on_product_created(self, event):
        if not event.category_id:
            return
        repo = current_domain.repository_for(CategoryProducts)
        try:
            view = repo.get(str(event.category_id))
        except ObjectNotFoundError:
            return

        products = json.loads(view.products) if isinstance(view.products, str) else (view.products or [])
        products.append(
            {
                "product_id": str(event.product_id),
                "title": event.title,
                "sku": event.sku,
                "status": event.status,
            }
        )
        view.products = json.dumps(products)
        view.product_count = len(products)
        view.updated_at = event.created_at
        repo.add(view)

    @on(ProductDetailsUpdated)
    def on_product_details_updated(self, event):
        # Update the product title in all category views containing it
        repo = current_domain.repository_for(CategoryProducts)
        all_categories = repo._dao.query.all().items

        for view in all_categories:
            products = json.loads(view.products) if isinstance(view.products, str) else (view.products or [])
            updated = False
            for p in products:
                if p.get("product_id") == str(event.product_id):
                    p["title"] = event.title
                    updated = True
            if updated:
                view.products = json.dumps(products)
                repo.add(view)

    @on(ProductActivated)
    def on_product_activated(self, event):
        self._update_product_status(str(event.product_id), "active", event.activated_at)

    @on(ProductDiscontinued)
    def on_product_discontinued(self, event):
        self._update_product_status(str(event.product_id), "discontinued", event.discontinued_at)

    @on(ProductArchived)
    def on_product_archived(self, event):
        self._update_product_status(str(event.product_id), "archived", event.archived_at)

    def _update_product_status(self, product_id, new_status, timestamp):
        repo = current_domain.repository_for(CategoryProducts)
        all_categories = repo._dao.query.all().items

        for view in all_categories:
            products = json.loads(view.products) if isinstance(view.products, str) else (view.products or [])
            updated = False
            for p in products:
                if p.get("product_id") == product_id:
                    p["status"] = new_status
                    updated = True
            if updated:
                view.products = json.dumps(products)
                view.updated_at = timestamp
                repo.add(view)
