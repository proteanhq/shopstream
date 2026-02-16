"""Integration tests for product aggregate persistence round-trip."""

import json

from catalogue.product.creation import CreateProduct
from catalogue.product.details import UpdateProductDetails
from catalogue.product.images import AddProductImage
from catalogue.product.product import Product
from catalogue.product.variants import AddVariant
from protean.utils.globals import current_domain


def _create_product(**overrides):
    defaults = {"sku": "PROD-001", "title": "Test Product", "seller_id": "seller-abc"}
    defaults.update(overrides)
    command = CreateProduct(**defaults)
    return current_domain.process(command, asynchronous=False)


class TestProductPersistence:
    def test_create_and_retrieve(self):
        product_id = _create_product()
        product = current_domain.repository_for(Product).get(product_id)

        assert product.sku.code == "PROD-001"
        assert product.title == "Test Product"
        assert product.seller_id == "seller-abc"
        assert product.status == "Draft"

    def test_update_details_persists(self):
        product_id = _create_product()
        current_domain.process(
            UpdateProductDetails(
                product_id=product_id,
                title="Updated Title",
                brand="BrandX",
                description="Updated description",
            ),
            asynchronous=False,
        )

        product = current_domain.repository_for(Product).get(product_id)
        assert product.title == "Updated Title"
        assert product.brand == "BrandX"
        assert product.description == "Updated description"

    def test_variants_persist(self):
        product_id = _create_product()
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="VAR-001", base_price=29.99),
            asynchronous=False,
        )
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="VAR-002", base_price=39.99),
            asynchronous=False,
        )

        product = current_domain.repository_for(Product).get(product_id)
        assert len(product.variants) == 2
        skus = {v.variant_sku.code for v in product.variants}
        assert skus == {"VAR-001", "VAR-002"}

    def test_variant_with_weight_persists(self):
        product_id = _create_product()
        current_domain.process(
            AddVariant(
                product_id=product_id,
                variant_sku="VAR-W",
                base_price=49.99,
                weight_value=1.5,
                weight_unit="kg",
            ),
            asynchronous=False,
        )

        product = current_domain.repository_for(Product).get(product_id)
        assert product.variants[0].weight.value == 1.5
        assert product.variants[0].weight.unit == "kg"

    def test_variant_with_dimensions_persists(self):
        product_id = _create_product()
        current_domain.process(
            AddVariant(
                product_id=product_id,
                variant_sku="VAR-D",
                base_price=59.99,
                length=10.0,
                width=5.0,
                height=3.0,
                dimension_unit="cm",
            ),
            asynchronous=False,
        )

        product = current_domain.repository_for(Product).get(product_id)
        assert product.variants[0].dimensions.length == 10.0
        assert product.variants[0].dimensions.unit == "cm"

    def test_variant_with_attributes_persists(self):
        product_id = _create_product()
        attrs = json.dumps({"size": "XL", "color": "Red"})
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="VAR-A", base_price=29.99, attributes=attrs),
            asynchronous=False,
        )

        product = current_domain.repository_for(Product).get(product_id)
        parsed = json.loads(product.variants[0].attributes)
        assert parsed["size"] == "XL"

    def test_images_persist(self):
        product_id = _create_product()
        current_domain.process(
            AddProductImage(product_id=product_id, url="https://cdn.example.com/img1.jpg"),
            asynchronous=False,
        )
        current_domain.process(
            AddProductImage(product_id=product_id, url="https://cdn.example.com/img2.jpg"),
            asynchronous=False,
        )

        product = current_domain.repository_for(Product).get(product_id)
        assert len(product.images) == 2
        urls = {i.url for i in product.images}
        assert "https://cdn.example.com/img1.jpg" in urls

    def test_seo_persists(self):
        product_id = _create_product(slug="my-product", meta_title="My Product", meta_description="Description")

        product = current_domain.repository_for(Product).get(product_id)
        assert product.seo.slug == "my-product"
        assert product.seo.meta_title == "My Product"

    def test_full_product_round_trip(self):
        """Full workflow: create, add variants, add images, update details."""
        product_id = _create_product(
            sku="FULL-001",
            title="Full Product",
            seller_id="seller-xyz",
            category_id="cat-001",
            brand="TestBrand",
            slug="full-product",
        )

        # Add variants
        current_domain.process(
            AddVariant(
                product_id=product_id, variant_sku="FV-001", base_price=99.99, weight_value=0.5, weight_unit="kg"
            ),
            asynchronous=False,
        )
        current_domain.process(
            AddVariant(product_id=product_id, variant_sku="FV-002", base_price=119.99),
            asynchronous=False,
        )

        # Add images
        current_domain.process(
            AddProductImage(product_id=product_id, url="https://cdn.example.com/front.jpg", alt_text="Front view"),
            asynchronous=False,
        )
        current_domain.process(
            AddProductImage(product_id=product_id, url="https://cdn.example.com/back.jpg", alt_text="Back view"),
            asynchronous=False,
        )

        # Update details
        current_domain.process(
            UpdateProductDetails(product_id=product_id, description="A comprehensive product"),
            asynchronous=False,
        )

        # Verify full state
        product = current_domain.repository_for(Product).get(product_id)
        assert product.title == "Full Product"
        assert product.brand == "TestBrand"
        assert product.description == "A comprehensive product"
        assert len(product.variants) == 2
        assert len(product.images) == 2
        assert product.seo.slug == "full-product"
