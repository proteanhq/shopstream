"""Category tree — navigation hierarchy projection."""

import json

from protean.core.projector import on
from protean.fields import Boolean, Identifier, Integer, String, Text
from protean.utils.globals import current_domain

from catalogue.category.category import Category
from catalogue.category.events import (
    CategoryCreated,
    CategoryDeactivated,
    CategoryDetailsUpdated,
    CategoryReordered,
)
from catalogue.domain import catalogue
from catalogue.product.events import ProductCreated
from catalogue.product.product import Product


@catalogue.projection
class CategoryTree:
    category_id: Identifier(identifier=True, required=True)
    name: String(required=True)
    parent_category_id: Identifier()
    level: Integer(required=True)
    is_active: Boolean(default=True)
    display_order: Integer(default=0)
    breadcrumb: Text()
    product_count: Integer(default=0)


@catalogue.projector(projector_for=CategoryTree, aggregates=[Category, Product])
class CategoryTreeProjector:
    def _build_breadcrumb(self, _category_id, name, parent_category_id):
        """Build a breadcrumb trail by walking the parent chain."""
        repo = current_domain.repository_for(CategoryTree)
        crumbs = [name]

        current_parent_id = parent_category_id
        while current_parent_id:
            try:
                parent_node = repo.get(current_parent_id)
                crumbs.insert(0, parent_node.name)
                # Walk up the tree
                current_parent_id = parent_node.parent_category_id
            except Exception:
                break

        return json.dumps(crumbs)

    @on(CategoryCreated)
    def on_category_created(self, event):
        breadcrumb = self._build_breadcrumb(event.category_id, event.name, event.parent_category_id)

        current_domain.repository_for(CategoryTree).add(
            CategoryTree(
                category_id=event.category_id,
                name=event.name,
                parent_category_id=event.parent_category_id,
                level=event.level,
                breadcrumb=breadcrumb,
                product_count=0,
            )
        )

    @on(CategoryDetailsUpdated)
    def on_category_details_updated(self, event):
        repo = current_domain.repository_for(CategoryTree)
        node = repo.get(event.category_id)
        node.name = event.name
        node.breadcrumb = self._build_breadcrumb(event.category_id, event.name, node.parent_category_id)
        repo.add(node)

    @on(CategoryReordered)
    def on_category_reordered(self, event):
        repo = current_domain.repository_for(CategoryTree)
        node = repo.get(event.category_id)
        node.display_order = event.new_order
        repo.add(node)

    @on(CategoryDeactivated)
    def on_category_deactivated(self, event):
        repo = current_domain.repository_for(CategoryTree)
        node = repo.get(event.category_id)
        node.is_active = False
        repo.add(node)

    @on(ProductCreated)
    def on_product_created(self, event):
        if not event.category_id:
            return
        repo = current_domain.repository_for(CategoryTree)
        try:
            node = repo.get(event.category_id)
            node.product_count = (node.product_count or 0) + 1
            repo.add(node)
        except Exception:
            pass
