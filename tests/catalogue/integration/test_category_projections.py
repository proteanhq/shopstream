"""Integration tests for category projections."""

import json

from catalogue.category.management import (
    CreateCategory,
    DeactivateCategory,
    ReorderCategory,
    UpdateCategory,
)
from catalogue.product.creation import CreateProduct
from catalogue.projections.category_tree import CategoryTree
from protean.utils.globals import current_domain


def _create_category(**overrides):
    defaults = {"name": "Electronics"}
    defaults.update(overrides)
    command = CreateCategory(**defaults)
    return current_domain.process(command, asynchronous=False)


class TestCategoryTreeProjection:
    def test_root_category_projection(self):
        category_id = _create_category()

        node = current_domain.repository_for(CategoryTree).get(category_id)
        assert node.name == "Electronics"
        assert node.level == 0
        assert node.is_active is True
        assert node.product_count == 0

        breadcrumb = json.loads(node.breadcrumb)
        assert breadcrumb == ["Electronics"]

    def test_child_category_breadcrumb(self):
        parent_id = _create_category(name="Electronics")
        child_id = _create_category(name="Phones", parent_category_id=parent_id)

        node = current_domain.repository_for(CategoryTree).get(child_id)
        breadcrumb = json.loads(node.breadcrumb)
        assert breadcrumb == ["Electronics", "Phones"]

    def test_deep_hierarchy_breadcrumb(self):
        l0 = _create_category(name="Electronics")
        l1 = _create_category(name="Phones", parent_category_id=l0)
        l2 = _create_category(name="Smartphones", parent_category_id=l1)

        node = current_domain.repository_for(CategoryTree).get(l2)
        breadcrumb = json.loads(node.breadcrumb)
        assert breadcrumb == ["Electronics", "Phones", "Smartphones"]

    def test_reorder_updates_projection(self):
        category_id = _create_category()
        current_domain.process(
            ReorderCategory(category_id=category_id, new_display_order=5),
            asynchronous=False,
        )

        node = current_domain.repository_for(CategoryTree).get(category_id)
        assert node.display_order == 5

    def test_deactivate_updates_projection(self):
        category_id = _create_category()
        current_domain.process(
            DeactivateCategory(category_id=category_id),
            asynchronous=False,
        )

        node = current_domain.repository_for(CategoryTree).get(category_id)
        assert node.is_active is False

    def test_name_update_updates_projection(self):
        category_id = _create_category()
        current_domain.process(
            UpdateCategory(category_id=category_id, name="Updated Electronics"),
            asynchronous=False,
        )

        node = current_domain.repository_for(CategoryTree).get(category_id)
        assert node.name == "Updated Electronics"
        breadcrumb = json.loads(node.breadcrumb)
        assert breadcrumb == ["Updated Electronics"]

    def test_product_count_incremented(self):
        category_id = _create_category()
        current_domain.process(
            CreateProduct(sku="P-001", title="Product 1", category_id=category_id),
            asynchronous=False,
        )

        node = current_domain.repository_for(CategoryTree).get(category_id)
        assert node.product_count == 1

    def test_product_without_category_no_increment(self):
        category_id = _create_category()
        current_domain.process(
            CreateProduct(sku="P-NOCAT", title="No Category Product"),
            asynchronous=False,
        )

        node = current_domain.repository_for(CategoryTree).get(category_id)
        assert node.product_count == 0
