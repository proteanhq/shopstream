"""Tests for Product creation factory method and event raising."""

from catalogue.product.events import ProductCreated
from catalogue.product.product import SEO, Product


def _make_product(**overrides):
    defaults = {
        "sku": "PROD-001",
        "title": "Test Product",
        "seller_id": "seller-abc",
        "category_id": "cat-123",
    }
    defaults.update(overrides)
    return Product.create(**defaults)


class TestProductCreationFactory:
    def test_factory_creates_product(self):
        product = _make_product()
        assert product.title == "Test Product"
        assert product.seller_id == "seller-abc"
        assert product.status == "Draft"

    def test_factory_raises_product_created_event(self):
        product = _make_product()
        assert len(product._events) == 1
        event = product._events[0]
        assert isinstance(event, ProductCreated)
        assert event.product_id == product.id
        assert event.sku == "PROD-001"
        assert event.seller_id == "seller-abc"
        assert event.category_id == "cat-123"
        assert event.status == "Draft"
        assert event.created_at is not None

    def test_factory_with_seo(self):
        seo = SEO(meta_title="Title", slug="test-product")
        product = _make_product(seo=seo)
        assert product.seo.slug == "test-product"

    def test_factory_with_dict_attributes(self):
        import json

        product = _make_product(attributes={"color": "red"})
        parsed = json.loads(product.attributes)
        assert parsed["color"] == "red"

    def test_factory_without_optional_fields(self):
        product = Product.create(sku="MIN-001", title="Minimal")
        assert product.seller_id is None
        assert product.category_id is None
        assert product.description is None
        assert product.brand is None
        assert product.seo is None


class TestProductUpdateDetails:
    def test_update_title(self):
        product = _make_product()
        product._events.clear()

        product.update_details(title="Updated Title")
        assert product.title == "Updated Title"
        assert len(product._events) == 1

    def test_update_description(self):
        product = _make_product()
        product._events.clear()

        product.update_details(description="New description")
        assert product.description == "New description"

    def test_update_brand(self):
        product = _make_product()
        product._events.clear()

        product.update_details(brand="NewBrand")
        assert product.brand == "NewBrand"

    def test_update_with_dict_attributes(self):
        import json

        product = _make_product()
        product._events.clear()

        product.update_details(attributes={"size": "L", "color": "blue"})
        parsed = json.loads(product.attributes)
        assert parsed["size"] == "L"
        assert parsed["color"] == "blue"

    def test_update_seo(self):
        product = _make_product()
        product._events.clear()

        seo = SEO(slug="updated-slug", meta_title="Updated")
        product.update_details(seo=seo)
        assert product.seo.slug == "updated-slug"

    def test_update_details_raises_event(self):
        product = _make_product()
        product._events.clear()

        product.update_details(title="New Title", brand="NewBrand")

        from catalogue.product.events import ProductDetailsUpdated

        assert len(product._events) == 1
        event = product._events[0]
        assert isinstance(event, ProductDetailsUpdated)
        assert event.title == "New Title"
        assert event.brand == "NewBrand"
