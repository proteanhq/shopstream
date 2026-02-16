"""Product lifecycle management — commands and handler."""

from protean import handle
from protean.fields import Identifier
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.product.product import Product


@catalogue.command(part_of="Product")
class ActivateProduct:
    product_id: Identifier(required=True)


@catalogue.command(part_of="Product")
class DiscontinueProduct:
    product_id: Identifier(required=True)


@catalogue.command(part_of="Product")
class ArchiveProduct:
    product_id: Identifier(required=True)


@catalogue.command_handler(part_of=Product)
class ManageLifecycleHandler:
    @handle(ActivateProduct)
    def activate_product(self, command):
        repo = current_domain.repository_for(Product)
        product = repo.get(command.product_id)
        product.activate()
        repo.add(product)

    @handle(DiscontinueProduct)
    def discontinue_product(self, command):
        repo = current_domain.repository_for(Product)
        product = repo.get(command.product_id)
        product.discontinue()
        repo.add(product)

    @handle(ArchiveProduct)
    def archive_product(self, command):
        repo = current_domain.repository_for(Product)
        product = repo.get(command.product_id)
        product.archive()
        repo.add(product)
