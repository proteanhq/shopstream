"""Tests for Product domain event structure and fields."""

from datetime import datetime

from catalogue.product.events import (
    ProductActivated,
    ProductArchived,
    ProductCreated,
    ProductDetailsUpdated,
    ProductDiscontinued,
    ProductImageAdded,
    ProductImageRemoved,
    TierPriceSet,
    VariantAdded,
    VariantPriceChanged,
)
from protean.utils import DomainObjects


class TestProductCreatedEvent:
    def test_element_type(self):
        assert ProductCreated.element_type == DomainObjects.EVENT

    def test_version(self):
        event = ProductCreated(product_id="p-1", sku="SKU-001", title="Test", status="Draft", created_at=datetime.now())
        assert event.__version__ == "v1"

    def test_fields(self):
        now = datetime.now()
        event = ProductCreated(
            product_id="p-1",
            sku="SKU-001",
            seller_id="s-1",
            title="Test",
            category_id="c-1",
            status="Draft",
            created_at=now,
        )
        assert event.product_id == "p-1"
        assert event.sku == "SKU-001"
        assert event.seller_id == "s-1"
        assert event.title == "Test"
        assert event.category_id == "c-1"
        assert event.status == "Draft"


class TestVariantAddedEvent:
    def test_element_type(self):
        assert VariantAdded.element_type == DomainObjects.EVENT

    def test_fields(self):
        event = VariantAdded(
            product_id="p-1",
            variant_id="v-1",
            variant_sku="VAR-001",
            price_amount=29.99,
            price_currency="USD",
            created_at=datetime.now(),
        )
        assert event.variant_sku == "VAR-001"
        assert event.price_amount == 29.99


class TestVariantPriceChangedEvent:
    def test_element_type(self):
        assert VariantPriceChanged.element_type == DomainObjects.EVENT

    def test_fields(self):
        event = VariantPriceChanged(
            product_id="p-1",
            variant_id="v-1",
            previous_price=29.99,
            new_price=39.99,
            currency="USD",
        )
        assert event.previous_price == 29.99
        assert event.new_price == 39.99


class TestTierPriceSetEvent:
    def test_element_type(self):
        assert TierPriceSet.element_type == DomainObjects.EVENT

    def test_fields(self):
        event = TierPriceSet(product_id="p-1", variant_id="v-1", tier="Silver", price=89.99, currency="USD")
        assert event.tier == "Silver"
        assert event.price == 89.99


class TestProductActivatedEvent:
    def test_element_type(self):
        assert ProductActivated.element_type == DomainObjects.EVENT

    def test_fields(self):
        now = datetime.now()
        event = ProductActivated(product_id="p-1", sku="SKU-001", activated_at=now)
        assert event.product_id == "p-1"
        assert event.activated_at == now


class TestProductDiscontinuedEvent:
    def test_element_type(self):
        assert ProductDiscontinued.element_type == DomainObjects.EVENT

    def test_fields(self):
        now = datetime.now()
        event = ProductDiscontinued(product_id="p-1", sku="SKU-001", discontinued_at=now)
        assert event.discontinued_at == now


class TestProductDetailsUpdatedEvent:
    def test_element_type(self):
        assert ProductDetailsUpdated.element_type == DomainObjects.EVENT

    def test_fields(self):
        event = ProductDetailsUpdated(product_id="p-1", title="New Title", description="Desc", brand="Brand")
        assert event.title == "New Title"


class TestProductImageAddedEvent:
    def test_element_type(self):
        assert ProductImageAdded.element_type == DomainObjects.EVENT

    def test_fields(self):
        event = ProductImageAdded(
            product_id="p-1", image_id="i-1", url="https://cdn.example.com/img.jpg", is_primary="True"
        )
        assert event.url == "https://cdn.example.com/img.jpg"


class TestProductImageRemovedEvent:
    def test_element_type(self):
        assert ProductImageRemoved.element_type == DomainObjects.EVENT

    def test_fields(self):
        event = ProductImageRemoved(product_id="p-1", image_id="i-1")
        assert event.image_id == "i-1"


class TestProductArchivedEvent:
    def test_element_type(self):
        assert ProductArchived.element_type == DomainObjects.EVENT

    def test_fields(self):
        now = datetime.now()
        event = ProductArchived(product_id="p-1", archived_at=now)
        assert event.archived_at == now
