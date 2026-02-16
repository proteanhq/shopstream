"""Tests for Category hierarchy and depth validation."""

import pytest
from catalogue.category.category import Category
from protean.exceptions import ValidationError


class TestCategoryHierarchy:
    def test_max_depth_level_4(self):
        """Level 4 is the maximum (0-indexed, 5 levels total)."""
        category = Category.create(name="Deepest", level=4)
        assert category.level == 4

    def test_level_exceeding_4_rejected(self):
        with pytest.raises(ValidationError):
            Category.create(name="Too Deep", level=5)

    def test_level_negative_rejected(self):
        with pytest.raises(ValidationError):
            Category.create(name="Negative", level=-1)

    def test_parent_reference(self):
        parent = Category.create(name="Parent")
        child = Category.create(
            name="Child",
            parent_category_id=parent.id,
            level=1,
        )
        assert child.parent_category_id == parent.id
        assert child.level == 1


class TestCategoryDeactivation:
    def test_deactivate_active_category(self):
        category = Category.create(name="Electronics")
        category._events.clear()

        category.deactivate()
        assert category.is_active is False

    def test_deactivate_already_inactive_raises_error(self):
        category = Category.create(name="Electronics")
        category.deactivate()
        category._events.clear()

        with pytest.raises(ValidationError) as exc:
            category.deactivate()
        assert "already inactive" in str(exc.value)
