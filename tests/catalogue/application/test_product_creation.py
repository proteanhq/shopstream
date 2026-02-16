"""Application tests for product creation command handler."""

from catalogue.product.creation import CreateProduct
from catalogue.product.product import Product
from protean.utils.globals import current_domain


def _create_product(**overrides):
    defaults = {
        "sku": "PROD-001",
        "title": "Test Product",
        "seller_id": "seller-abc",
        "category_id": "cat-123",
    }
    defaults.update(overrides)
    command = CreateProduct(**defaults)
    result = current_domain.process(command, asynchronous=False)
    return result


class TestCreateProductHandler:
    def test_create_product_minimal(self):
        product_id = _create_product()
        assert product_id is not None

        product = current_domain.repository_for(Product).get(product_id)
        assert product.title == "Test Product"
        assert product.sku.code == "PROD-001"
        assert product.status == "Draft"

    def test_create_product_with_all_fields(self):
        product_id = _create_product(
            sku="FULL-001",
            title="Full Product",
            seller_id="seller-xyz",
            category_id="cat-456",
            description="A fully specified product",
            brand="TestBrand",
            visibility="Unlisted",
            slug="full-product",
            meta_title="Full Product Title",
            meta_description="Full product description",
        )
        product = current_domain.repository_for(Product).get(product_id)
        assert product.title == "Full Product"
        assert product.brand == "TestBrand"
        assert product.visibility == "Unlisted"
        assert product.seo.slug == "full-product"

    def test_create_product_without_optional_fields(self):
        command = CreateProduct(sku="MIN-001", title="Minimal Product")
        product_id = current_domain.process(command, asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        assert product.seller_id is None
        assert product.category_id is None
        assert product.description is None
        assert product.brand is None

    def test_create_product_writes_to_event_store(self):
        product_id = _create_product(sku="EVT-001", title="Event Test")

        messages = current_domain.event_store.store.read("catalogue::product")
        product_messages = [
            m
            for m in messages
            if m.metadata.headers.type == "Catalogue.ProductCreated.v1" and m.data.get("product_id") == product_id
        ]
        assert len(product_messages) >= 1
