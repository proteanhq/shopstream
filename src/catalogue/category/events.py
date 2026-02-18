"""Domain events for the Category aggregate."""

from protean.fields import DateTime, Identifier, Integer, String, Text

from catalogue.domain import catalogue


@catalogue.event(part_of="Category")
class CategoryCreated:
    """A new product category was added to the catalogue hierarchy."""

    __version__ = "v1"

    category_id: Identifier(required=True)
    name: String(required=True)
    parent_category_id: Identifier()
    level: Integer(required=True)


@catalogue.event(part_of="Category")
class CategoryDetailsUpdated:
    """A category's name or attributes were changed."""

    __version__ = "v1"

    category_id: Identifier(required=True)
    name: String(required=True)
    attributes: Text()


@catalogue.event(part_of="Category")
class CategoryReordered:
    """A category's display position was changed."""

    __version__ = "v1"

    category_id: Identifier(required=True)
    previous_order: Integer(required=True)
    new_order: Integer(required=True)


@catalogue.event(part_of="Category")
class CategoryDeactivated:
    """A category was deactivated and hidden from the storefront."""

    __version__ = "v1"

    category_id: Identifier(required=True)
    deactivated_at: DateTime(required=True)
