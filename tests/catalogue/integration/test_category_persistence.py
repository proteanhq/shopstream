"""Integration tests for category aggregate persistence."""

import json

from catalogue.category.category import Category
from catalogue.category.management import CreateCategory, DeactivateCategory, ReorderCategory, UpdateCategory
from protean.utils.globals import current_domain


def _create_category(**overrides):
    defaults = {"name": "Electronics"}
    defaults.update(overrides)
    command = CreateCategory(**defaults)
    return current_domain.process(command, asynchronous=False)


class TestCategoryPersistence:
    def test_create_and_retrieve(self):
        category_id = _create_category()
        category = current_domain.repository_for(Category).get(category_id)

        assert category.name == "Electronics"
        assert category.level == 0
        assert category.is_active is True

    def test_parent_child_persistence(self):
        parent_id = _create_category(name="Electronics")
        child_id = _create_category(name="Phones", parent_category_id=parent_id)

        child = current_domain.repository_for(Category).get(child_id)
        assert child.parent_category_id == parent_id
        assert child.level == 1

    def test_update_persists(self):
        category_id = _create_category()
        attrs = json.dumps({"filterable": ["brand"]})
        current_domain.process(
            UpdateCategory(category_id=category_id, name="Updated Name", attributes=attrs),
            asynchronous=False,
        )

        category = current_domain.repository_for(Category).get(category_id)
        assert category.name == "Updated Name"
        assert json.loads(category.attributes) == {"filterable": ["brand"]}

    def test_reorder_persists(self):
        category_id = _create_category()
        current_domain.process(
            ReorderCategory(category_id=category_id, new_display_order=3),
            asynchronous=False,
        )

        category = current_domain.repository_for(Category).get(category_id)
        assert category.display_order == 3

    def test_deactivate_persists(self):
        category_id = _create_category()
        current_domain.process(
            DeactivateCategory(category_id=category_id),
            asynchronous=False,
        )

        category = current_domain.repository_for(Category).get(category_id)
        assert category.is_active is False

    def test_deep_hierarchy_persistence(self):
        l0 = _create_category(name="Root")
        l1 = _create_category(name="Child", parent_category_id=l0)
        l2 = _create_category(name="GrandChild", parent_category_id=l1)

        gc = current_domain.repository_for(Category).get(l2)
        assert gc.level == 2
        assert gc.parent_category_id == l1
