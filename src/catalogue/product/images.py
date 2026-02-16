"""Image management — commands and handler."""

from protean import handle
from protean.fields import Boolean, Identifier, String
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.product.product import Product


@catalogue.command(part_of="Product")
class AddProductImage:
    product_id: Identifier(required=True)
    url: String(required=True, max_length=500)
    alt_text: String(max_length=255)
    is_primary: Boolean(default=False)


@catalogue.command(part_of="Product")
class RemoveProductImage:
    product_id: Identifier(required=True)
    image_id: Identifier(required=True)


@catalogue.command_handler(part_of=Product)
class ManageImagesHandler:
    @handle(AddProductImage)
    def add_image(self, command):
        repo = current_domain.repository_for(Product)
        product = repo.get(command.product_id)
        product.add_image(
            url=command.url,
            alt_text=command.alt_text,
            is_primary=command.is_primary,
        )
        repo.add(product)

    @handle(RemoveProductImage)
    def remove_image(self, command):
        repo = current_domain.repository_for(Product)
        product = repo.get(command.product_id)
        product.remove_image(command.image_id)
        repo.add(product)
