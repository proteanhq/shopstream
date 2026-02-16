"""Tests for the Product aggregate root."""

from catalogue.product.product import SEO, Product, ProductStatus, ProductVisibility
from catalogue.shared.sku import SKU
from protean.utils.reflection import declared_fields


class TestProductConstruction:
    def test_element_type(self):
        from protean.utils import DomainObjects

        assert Product.element_type == DomainObjects.AGGREGATE

    def test_declared_fields(self):
        fields = declared_fields(Product)
        assert "sku" in fields
        assert "seller_id" in fields
        assert "title" in fields
        assert "description" in fields
        assert "category_id" in fields
        assert "brand" in fields
        assert "attributes" in fields
        assert "variants" in fields
        assert "images" in fields
        assert "status" in fields
        assert "visibility" in fields
        assert "seo" in fields
        assert "created_at" in fields
        assert "updated_at" in fields

    def test_create_product_minimal(self):
        product = Product.create(sku="ELEC-PHN-001", title="Smartphone X")
        assert product.sku.code == "ELEC-PHN-001"
        assert product.title == "Smartphone X"
        assert product.status == ProductStatus.DRAFT.value
        assert product.visibility == ProductVisibility.PUBLIC.value
        assert product.created_at is not None
        assert product.updated_at is not None

    def test_create_product_full(self):
        seo = SEO(meta_title="Best Phone", meta_description="Top rated", slug="smartphone-x")
        product = Product.create(
            sku="ELEC-PHN-001",
            title="Smartphone X",
            seller_id="seller-123",
            category_id="cat-electronics",
            description="A great smartphone",
            brand="TechBrand",
            attributes={"screen_size": "6.5"},
            visibility=ProductVisibility.UNLISTED.value,
            seo=seo,
        )
        assert product.seller_id == "seller-123"
        assert product.category_id == "cat-electronics"
        assert product.description == "A great smartphone"
        assert product.brand == "TechBrand"
        assert product.visibility == ProductVisibility.UNLISTED.value
        assert product.seo.slug == "smartphone-x"


class TestProductStatus:
    def test_all_status_values(self):
        assert ProductStatus.DRAFT.value == "Draft"
        assert ProductStatus.ACTIVE.value == "Active"
        assert ProductStatus.DISCONTINUED.value == "Discontinued"
        assert ProductStatus.ARCHIVED.value == "Archived"


class TestProductVisibility:
    def test_all_visibility_values(self):
        assert ProductVisibility.PUBLIC.value == "Public"
        assert ProductVisibility.UNLISTED.value == "Unlisted"
        assert ProductVisibility.TIER_RESTRICTED.value == "Tier_Restricted"


class TestProductCreation:
    def test_create_raises_event(self):
        product = Product.create(sku="ELEC-PHN-001", title="Smartphone X")
        assert len(product._events) == 1

        from catalogue.product.events import ProductCreated

        event = product._events[0]
        assert isinstance(event, ProductCreated)
        assert event.sku == "ELEC-PHN-001"
        assert event.title == "Smartphone X"
        assert event.status == "Draft"

    def test_create_with_sku_string(self):
        product = Product.create(sku="TEST-SKU-001", title="Test Product")
        assert isinstance(product.sku, SKU)
        assert product.sku.code == "TEST-SKU-001"

    def test_create_with_sku_vo(self):
        sku = SKU(code="TEST-SKU-002")
        product = Product.create(sku=sku, title="Test Product")
        assert product.sku.code == "TEST-SKU-002"
