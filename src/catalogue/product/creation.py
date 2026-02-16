"""Product creation — command and handler."""

from protean import handle
from protean.fields import Identifier, String, Text
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.product.product import SEO, Product


@catalogue.command(part_of="Product")
class CreateProduct:
    sku: String(required=True, max_length=50)
    seller_id: Identifier()
    title: String(required=True, max_length=255)
    description: String()
    category_id: Identifier()
    brand: String(max_length=100)
    attributes: Text()
    visibility: String(max_length=20)
    meta_title: String(max_length=70)
    meta_description: String(max_length=160)
    slug: String(max_length=200)


@catalogue.command_handler(part_of=Product)
class CreateProductHandler:
    @handle(CreateProduct)
    def create_product(self, command):
        seo = None
        if command.slug:
            seo = SEO(
                meta_title=command.meta_title,
                meta_description=command.meta_description,
                slug=command.slug,
            )

        product = Product.create(
            sku=command.sku,
            seller_id=command.seller_id,
            title=command.title,
            description=command.description,
            category_id=command.category_id,
            brand=command.brand,
            attributes=command.attributes,
            visibility=command.visibility,
            seo=seo,
        )
        current_domain.repository_for(Product).add(product)
        return str(product.id)
