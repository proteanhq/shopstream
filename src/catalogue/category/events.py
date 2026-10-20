"""Domain events for the Category aggregate."""

from datetime import datetime
from typing import Any

from protean.fields import DateTime, Dict, Identifier, Integer, String

from catalogue.domain import catalogue


@catalogue.event(part_of="Category")
class CategoryCreated:
    """A new product category was added to the catalogue hierarchy."""

    category_id: str = Identifier(required=True)
    name: str = String(required=True)
    parent_category_id: str | None = Identifier()
    level: int = Integer(required=True)


@catalogue.event(part_of="Category")
class CategoryDetailsUpdated:
    """A category's name or attributes were changed."""

    category_id: str = Identifier(required=True)
    name: str = String(required=True)
    attributes: dict[str, Any] = Dict()


@catalogue.event(part_of="Category")
class CategoryReordered:
    """A category's display position was changed."""

    category_id: str = Identifier(required=True)
    previous_order: int = Integer(required=True)
    new_order: int = Integer(required=True)


@catalogue.event(part_of="Category")
class CategoryDeactivated:
    """A category was deactivated and hidden from the storefront."""

    category_id: str = Identifier(required=True)
    deactivated_at: datetime = DateTime(required=True)
