"""Product details management — command and handler."""

from protean import handle
from protean.fields import Identifier, String, Text
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.product.product import SEO, Product


@catalogue.command(part_of="Product")
class UpdateProductDetails:
    product_id: Identifier(required=True)
    title: String(max_length=255)
    description: String()
    brand: String(max_length=100)
    attributes: Text()
    meta_title: String(max_length=70)
    meta_description: String(max_length=160)
    slug: String(max_length=200)


@catalogue.command_handler(part_of=Product)
class ManageProductDetailsHandler:
    @handle(UpdateProductDetails)
    def update_details(self, command):
        repo = current_domain.repository_for(Product)
        product = repo.get(command.product_id)

        seo = None
        if command.slug is not None:
            seo = SEO(
                meta_title=command.meta_title,
                meta_description=command.meta_description,
                slug=command.slug,
            )

        product.update_details(
            title=command.title,
            description=command.description,
            brand=command.brand,
            attributes=command.attributes,
            seo=seo,
        )
        repo.add(product)
