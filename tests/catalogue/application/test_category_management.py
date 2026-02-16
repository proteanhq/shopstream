"""Application tests for category management handlers."""

import json

import pytest
from catalogue.category.category import Category
from catalogue.category.management import (
    CreateCategory,
    DeactivateCategory,
    ReorderCategory,
    UpdateCategory,
)
from protean.exceptions import ValidationError
from protean.utils.globals import current_domain


def _create_category(**overrides):
    defaults = {"name": "Electronics"}
    defaults.update(overrides)
    command = CreateCategory(**defaults)
    return current_domain.process(command, asynchronous=False)


class TestCreateCategoryHandler:
    def test_create_root_category(self):
        category_id = _create_category()
        assert category_id is not None

        category = current_domain.repository_for(Category).get(category_id)
        assert category.name == "Electronics"
        assert category.level == 0
        assert category.parent_category_id is None

    def test_create_child_category(self):
        parent_id = _create_category(name="Electronics")
        child_id = _create_category(name="Phones", parent_category_id=parent_id)

        child = current_domain.repository_for(Category).get(child_id)
        assert child.name == "Phones"
        assert child.level == 1
        assert child.parent_category_id == parent_id

    def test_create_deep_hierarchy(self):
        level0 = _create_category(name="Level 0")
        level1 = _create_category(name="Level 1", parent_category_id=level0)
        level2 = _create_category(name="Level 2", parent_category_id=level1)
        level3 = _create_category(name="Level 3", parent_category_id=level2)
        level4 = _create_category(name="Level 4", parent_category_id=level3)

        cat = current_domain.repository_for(Category).get(level4)
        assert cat.level == 4

    def test_exceed_max_depth_rejected(self):
        level0 = _create_category(name="Level 0")
        level1 = _create_category(name="Level 1", parent_category_id=level0)
        level2 = _create_category(name="Level 2", parent_category_id=level1)
        level3 = _create_category(name="Level 3", parent_category_id=level2)
        level4 = _create_category(name="Level 4", parent_category_id=level3)

        with pytest.raises(ValidationError) as exc:
            _create_category(name="Level 5", parent_category_id=level4)
        assert "cannot exceed 5 levels" in str(exc.value)

    def test_create_category_with_attributes(self):
        attrs = json.dumps({"filterable": ["brand", "screen_size"]})
        category_id = _create_category(name="Phones", attributes=attrs)

        category = current_domain.repository_for(Category).get(category_id)
        parsed = json.loads(category.attributes)
        assert parsed["filterable"] == ["brand", "screen_size"]


class TestUpdateCategoryHandler:
    def test_update_category_name(self):
        category_id = _create_category()
        command = UpdateCategory(category_id=category_id, name="Updated Electronics")
        current_domain.process(command, asynchronous=False)

        category = current_domain.repository_for(Category).get(category_id)
        assert category.name == "Updated Electronics"

    def test_update_category_attributes(self):
        category_id = _create_category()
        attrs = json.dumps({"filterable": ["brand"]})
        command = UpdateCategory(category_id=category_id, attributes=attrs)
        current_domain.process(command, asynchronous=False)

        category = current_domain.repository_for(Category).get(category_id)
        assert json.loads(category.attributes) == {"filterable": ["brand"]}


class TestReorderCategoryHandler:
    def test_reorder_category(self):
        category_id = _create_category()
        command = ReorderCategory(category_id=category_id, new_display_order=5)
        current_domain.process(command, asynchronous=False)

        category = current_domain.repository_for(Category).get(category_id)
        assert category.display_order == 5


class TestDeactivateCategoryHandler:
    def test_deactivate_category(self):
        category_id = _create_category()
        command = DeactivateCategory(category_id=category_id)
        current_domain.process(command, asynchronous=False)

        category = current_domain.repository_for(Category).get(category_id)
        assert category.is_active is False

    def test_deactivate_already_inactive_rejected(self):
        category_id = _create_category()
        current_domain.process(DeactivateCategory(category_id=category_id), asynchronous=False)

        with pytest.raises(ValidationError):
            current_domain.process(DeactivateCategory(category_id=category_id), asynchronous=False)
