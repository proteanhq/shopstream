"""Application tests for image management handlers."""

from catalogue.product.creation import CreateProduct
from catalogue.product.images import AddProductImage, RemoveProductImage
from catalogue.product.product import Product
from protean.utils.globals import current_domain


def _create_product(**overrides):
    defaults = {"sku": "PROD-001", "title": "Test Product"}
    defaults.update(overrides)
    command = CreateProduct(**defaults)
    return current_domain.process(command, asynchronous=False)


def _add_image(product_id, **overrides):
    defaults = {
        "product_id": product_id,
        "url": "https://cdn.example.com/img.jpg",
    }
    defaults.update(overrides)
    command = AddProductImage(**defaults)
    current_domain.process(command, asynchronous=False)


class TestAddImageHandler:
    def test_add_first_image(self):
        product_id = _create_product()
        _add_image(product_id)

        product = current_domain.repository_for(Product).get(product_id)
        assert len(product.images) == 1
        assert product.images[0].is_primary is True

    def test_add_second_image_not_primary(self):
        product_id = _create_product()
        _add_image(product_id, url="https://cdn.example.com/img1.jpg")
        _add_image(product_id, url="https://cdn.example.com/img2.jpg")

        product = current_domain.repository_for(Product).get(product_id)
        assert len(product.images) == 2
        # First image remains primary
        primaries = [i for i in product.images if i.is_primary]
        assert len(primaries) == 1

    def test_add_image_with_alt_text(self):
        product_id = _create_product()
        _add_image(product_id, alt_text="Product front view")

        product = current_domain.repository_for(Product).get(product_id)
        assert product.images[0].alt_text == "Product front view"


class TestRemoveImageHandler:
    def test_remove_non_primary_image(self):
        product_id = _create_product()
        _add_image(product_id, url="https://cdn.example.com/img1.jpg")
        _add_image(product_id, url="https://cdn.example.com/img2.jpg")

        product = current_domain.repository_for(Product).get(product_id)
        non_primary = next(i for i in product.images if not i.is_primary)

        command = RemoveProductImage(product_id=product_id, image_id=non_primary.id)
        current_domain.process(command, asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        assert len(product.images) == 1

    def test_remove_last_image(self):
        product_id = _create_product()
        _add_image(product_id, url="https://cdn.example.com/img1.jpg")

        product = current_domain.repository_for(Product).get(product_id)
        image_id = product.images[0].id

        command = RemoveProductImage(product_id=product_id, image_id=image_id)
        current_domain.process(command, asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        assert len(product.images) == 0
