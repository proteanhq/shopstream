"""Tests for the Category aggregate root."""

import json

from catalogue.category.category import Category
from protean.utils.reflection import declared_fields


class TestCategoryConstruction:
    def test_element_type(self):
        from protean.utils import DomainObjects

        assert Category.element_type == DomainObjects.AGGREGATE

    def test_declared_fields(self):
        fields = declared_fields(Category)
        assert "name" in fields
        assert "parent_category_id" in fields
        assert "level" in fields
        assert "attributes" in fields
        assert "is_active" in fields
        assert "display_order" in fields
        assert "created_at" in fields
        assert "updated_at" in fields

    def test_create_root_category(self):
        category = Category.create(name="Electronics")
        assert category.name == "Electronics"
        assert category.parent_category_id is None
        assert category.level == 0
        assert category.is_active is True
        assert category.display_order == 0
        assert category.created_at is not None
        assert category.updated_at is not None

    def test_create_child_category(self):
        category = Category.create(
            name="Phones",
            parent_category_id="parent-123",
            level=1,
        )
        assert category.name == "Phones"
        assert category.parent_category_id == "parent-123"
        assert category.level == 1

    def test_create_category_with_attributes(self):
        attrs = {"filterable": ["brand", "screen_size"]}
        category = Category.create(name="Phones", attributes=attrs)
        assert json.loads(category.attributes) == attrs

    def test_create_category_raises_event(self):
        category = Category.create(name="Electronics")
        assert len(category._events) == 1
        event = category._events[0]
        from catalogue.category.events import CategoryCreated

        assert isinstance(event, CategoryCreated)
        assert event.name == "Electronics"
        assert event.level == 0


class TestCategoryMethods:
    def test_update_details_name(self):
        category = Category.create(name="Old Name")
        category._events.clear()

        category.update_details(name="New Name")
        assert category.name == "New Name"
        assert len(category._events) == 1

        from catalogue.category.events import CategoryDetailsUpdated

        assert isinstance(category._events[0], CategoryDetailsUpdated)

    def test_update_details_attributes(self):
        category = Category.create(name="Electronics")
        category._events.clear()

        new_attrs = {"filterable": ["brand", "color"]}
        category.update_details(attributes=new_attrs)
        assert json.loads(category.attributes) == new_attrs

    def test_reorder(self):
        category = Category.create(name="Electronics")
        category._events.clear()

        category.reorder(5)
        assert category.display_order == 5
        assert len(category._events) == 1

        from catalogue.category.events import CategoryReordered

        event = category._events[0]
        assert isinstance(event, CategoryReordered)
        assert event.previous_order == 0
        assert event.new_order == 5

    def test_deactivate(self):
        category = Category.create(name="Electronics")
        category._events.clear()

        category.deactivate()
        assert category.is_active is False
        assert len(category._events) == 1

        from catalogue.category.events import CategoryDeactivated

        assert isinstance(category._events[0], CategoryDeactivated)
