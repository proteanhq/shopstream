"""Category management — commands and handlers."""

from protean import handle
from protean.exceptions import ValidationError
from protean.fields import Dict, Identifier, Integer, String

from catalogue.category.category import Category
from catalogue.domain import catalogue


@catalogue.command(part_of="Category")
class CreateCategory:
    """Add a new category to the product hierarchy."""

    name: String(required=True, max_length=100)
    parent_category_id: Identifier()
    attributes: Dict()


@catalogue.command(part_of="Category")
class UpdateCategory:
    """Change a category's name or attributes."""

    category_id: Identifier(required=True)
    name: String(max_length=100)
    attributes: Dict()


@catalogue.command(part_of="Category")
class ReorderCategory:
    """Change a category's display position in the hierarchy."""

    category_id: Identifier(required=True)
    new_display_order: Integer(required=True)


@catalogue.command(part_of="Category")
class DeactivateCategory:
    """Deactivate a category, hiding it from the storefront."""

    category_id: Identifier(required=True)


@catalogue.command_handler(part_of=Category)
class ManageCategoryHandler:
    @handle(CreateCategory)
    def create_category(self, command):
        from protean.utils.globals import current_domain

        level = 0
        parent_id = command.parent_category_id

        if parent_id:
            repo = current_domain.repository_for(Category)
            parent = repo.get(parent_id)
            level = parent.level + 1
            if level > 4:
                raise ValidationError({"level": ["Category hierarchy cannot exceed 5 levels (depth 0-4)"]})

        category = Category.create(
            name=command.name,
            parent_category_id=parent_id,
            level=level,
            attributes=command.attributes,
        )
        current_domain.repository_for(Category).add(category)
        return str(category.id)

    @handle(UpdateCategory)
    def update_category(self, command):
        from protean.utils.globals import current_domain

        repo = current_domain.repository_for(Category)
        category = repo.get(command.category_id)

        category.update_details(
            name=command.name,
            attributes=command.attributes,
        )
        repo.add(category)

    @handle(ReorderCategory)
    def reorder_category(self, command):
        from protean.utils.globals import current_domain

        repo = current_domain.repository_for(Category)
        category = repo.get(command.category_id)
        category.reorder(command.new_display_order)
        repo.add(category)

    @handle(DeactivateCategory)
    def deactivate_category(self, command):
        from protean.utils.globals import current_domain

        repo = current_domain.repository_for(Category)
        category = repo.get(command.category_id)
        category.deactivate()
        repo.add(category)
