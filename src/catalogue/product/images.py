"""Image management — commands and handler."""

from protean import handle
from protean.fields import Boolean, Identifier, String
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.product.product import Product


@catalogue.command(part_of="Product")
class AddProductImage:
    """Upload a new image for a product."""

    product_id: str = Identifier(required=True)
    url: str = String(required=True, max_length=500)
    alt_text: str | None = String(max_length=255)
    is_primary: bool = Boolean(default=False)


@catalogue.command(part_of="Product")
class RemoveProductImage:
    """Remove an image from a product's gallery."""

    product_id: str = Identifier(required=True)
    image_id: str = Identifier(required=True)


@catalogue.command_handler(part_of=Product)
class ManageImagesHandler:
    @handle(AddProductImage)
    def add_image(self, command: AddProductImage) -> None:
        repo = current_domain.repository_for(Product)
        product = repo.get(command.product_id)
        product.add_image(
            url=command.url,
            alt_text=command.alt_text,
            is_primary=command.is_primary,
        )
        repo.add(product)

    @handle(RemoveProductImage)
    def remove_image(self, command: RemoveProductImage) -> None:
        repo = current_domain.repository_for(Product)
        product = repo.get(command.product_id)
        product.remove_image(command.image_id)
        repo.add(product)
