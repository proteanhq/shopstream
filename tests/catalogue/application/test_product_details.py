"""Application tests for product details update handler."""

from catalogue.product.creation import CreateProduct
from catalogue.product.details import UpdateProductDetails
from catalogue.product.product import Product
from protean.utils.globals import current_domain


def _create_product(**overrides):
    defaults = {"sku": "PROD-001", "title": "Test Product"}
    defaults.update(overrides)
    command = CreateProduct(**defaults)
    return current_domain.process(command, asynchronous=False)


class TestUpdateProductDetailsHandler:
    def test_update_title(self):
        product_id = _create_product()
        command = UpdateProductDetails(product_id=product_id, title="Updated Title")
        current_domain.process(command, asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        assert product.title == "Updated Title"

    def test_update_description(self):
        product_id = _create_product()
        command = UpdateProductDetails(product_id=product_id, description="New description")
        current_domain.process(command, asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        assert product.description == "New description"

    def test_update_brand(self):
        product_id = _create_product()
        command = UpdateProductDetails(product_id=product_id, brand="NewBrand")
        current_domain.process(command, asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        assert product.brand == "NewBrand"

    def test_update_seo(self):
        product_id = _create_product()
        command = UpdateProductDetails(
            product_id=product_id,
            slug="updated-slug",
            meta_title="Updated Title",
            meta_description="Updated description",
        )
        current_domain.process(command, asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        assert product.seo.slug == "updated-slug"
        assert product.seo.meta_title == "Updated Title"

    def test_update_multiple_fields(self):
        product_id = _create_product()
        command = UpdateProductDetails(
            product_id=product_id,
            title="New Title",
            brand="NewBrand",
            description="New desc",
        )
        current_domain.process(command, asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        assert product.title == "New Title"
        assert product.brand == "NewBrand"
        assert product.description == "New desc"
