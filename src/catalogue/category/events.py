"""Domain events for the Category aggregate."""

from protean.fields import DateTime, Identifier, Integer, String, Text

from catalogue.domain import catalogue


@catalogue.event(part_of="Category")
class CategoryCreated:
    __version__ = "v1"

    category_id: Identifier(required=True)
    name: String(required=True)
    parent_category_id: Identifier()
    level: Integer(required=True)


@catalogue.event(part_of="Category")
class CategoryDetailsUpdated:
    __version__ = "v1"

    category_id: Identifier(required=True)
    name: String(required=True)
    attributes: Text()


@catalogue.event(part_of="Category")
class CategoryReordered:
    __version__ = "v1"

    category_id: Identifier(required=True)
    previous_order: Integer(required=True)
    new_order: Integer(required=True)


@catalogue.event(part_of="Category")
class CategoryDeactivated:
    __version__ = "v1"

    category_id: Identifier(required=True)
    deactivated_at: DateTime(required=True)
