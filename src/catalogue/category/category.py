"""Category aggregate root for product categorization."""

import json
from datetime import datetime

from protean.exceptions import ValidationError
from protean.fields import Boolean, DateTime, Identifier, Integer, String, Text

from catalogue.domain import catalogue


@catalogue.aggregate
class Category:
    """A hierarchical grouping for organizing products in the catalogue.

    Categories form a tree up to 5 levels deep (0-4). Each category can have a
    parent, custom attributes, and a display order for controlling presentation.
    """

    name: String(required=True, max_length=100)
    parent_category_id: Identifier()
    level: Integer(default=0, min_value=0, max_value=4)
    attributes: Text()
    is_active: Boolean(default=True)
    display_order: Integer(default=0)
    created_at: DateTime(default=datetime.now)
    updated_at: DateTime(default=datetime.now)

    @classmethod
    def create(cls, name, parent_category_id=None, level=0, attributes=None):
        from catalogue.category.events import CategoryCreated

        now = datetime.now()
        attrs_json = json.dumps(attributes) if attributes else None

        category = cls(
            name=name,
            parent_category_id=parent_category_id,
            level=level,
            attributes=attrs_json,
            created_at=now,
            updated_at=now,
        )
        category.raise_(
            CategoryCreated(
                category_id=category.id,
                name=name,
                parent_category_id=parent_category_id,
                level=level,
            )
        )
        return category

    def update_details(self, name=None, attributes=None):
        from catalogue.category.events import CategoryDetailsUpdated

        if name is not None:
            self.name = name

        attrs_json = None
        if attributes is not None:
            attrs_json = json.dumps(attributes)
            self.attributes = attrs_json

        self.updated_at = datetime.now()

        self.raise_(
            CategoryDetailsUpdated(
                category_id=self.id,
                name=self.name,
                attributes=attrs_json,
            )
        )

    def reorder(self, new_display_order):
        from catalogue.category.events import CategoryReordered

        previous_order = self.display_order
        self.display_order = new_display_order
        self.updated_at = datetime.now()

        self.raise_(
            CategoryReordered(
                category_id=self.id,
                previous_order=previous_order,
                new_order=new_display_order,
            )
        )

    def deactivate(self):
        from catalogue.category.events import CategoryDeactivated

        if not self.is_active:
            raise ValidationError({"status": ["Category is already inactive"]})

        self.is_active = False
        now = datetime.now()
        self.updated_at = now

        self.raise_(
            CategoryDeactivated(
                category_id=self.id,
                deactivated_at=now,
            )
        )
