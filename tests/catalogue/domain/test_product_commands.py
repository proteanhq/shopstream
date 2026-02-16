"""Tests for Product command structure and fields."""

from catalogue.category.management import CreateCategory, DeactivateCategory, ReorderCategory, UpdateCategory
from catalogue.product.creation import CreateProduct
from catalogue.product.details import UpdateProductDetails
from catalogue.product.images import AddProductImage, RemoveProductImage
from catalogue.product.lifecycle import ActivateProduct, ArchiveProduct, DiscontinueProduct
from catalogue.product.variants import AddVariant, SetTierPrice, UpdateVariantPrice
from protean.utils import DomainObjects


class TestCreateProductCommand:
    def test_element_type(self):
        assert CreateProduct.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = CreateProduct(sku="SKU-001", title="Test Product", seller_id="s-1")
        assert cmd.sku == "SKU-001"
        assert cmd.title == "Test Product"
        assert cmd.seller_id == "s-1"

    def test_optional_fields(self):
        cmd = CreateProduct(sku="SKU-001", title="Test")
        assert cmd.description is None
        assert cmd.brand is None
        assert cmd.category_id is None


class TestUpdateProductDetailsCommand:
    def test_element_type(self):
        assert UpdateProductDetails.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = UpdateProductDetails(product_id="p-1", title="Updated", brand="Brand")
        assert cmd.product_id == "p-1"
        assert cmd.title == "Updated"


class TestAddVariantCommand:
    def test_element_type(self):
        assert AddVariant.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = AddVariant(product_id="p-1", variant_sku="VAR-001", base_price=29.99)
        assert cmd.variant_sku == "VAR-001"
        assert cmd.base_price == 29.99


class TestUpdateVariantPriceCommand:
    def test_element_type(self):
        assert UpdateVariantPrice.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = UpdateVariantPrice(product_id="p-1", variant_id="v-1", base_price=39.99)
        assert cmd.base_price == 39.99


class TestSetTierPriceCommand:
    def test_element_type(self):
        assert SetTierPrice.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = SetTierPrice(product_id="p-1", variant_id="v-1", tier="Silver", price=89.99)
        assert cmd.tier == "Silver"
        assert cmd.price == 89.99


class TestAddProductImageCommand:
    def test_element_type(self):
        assert AddProductImage.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = AddProductImage(product_id="p-1", url="https://cdn.example.com/img.jpg")
        assert cmd.url == "https://cdn.example.com/img.jpg"
        assert cmd.is_primary is False


class TestRemoveProductImageCommand:
    def test_element_type(self):
        assert RemoveProductImage.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = RemoveProductImage(product_id="p-1", image_id="i-1")
        assert cmd.image_id == "i-1"


class TestActivateProductCommand:
    def test_element_type(self):
        assert ActivateProduct.element_type == DomainObjects.COMMAND


class TestDiscontinueProductCommand:
    def test_element_type(self):
        assert DiscontinueProduct.element_type == DomainObjects.COMMAND


class TestArchiveProductCommand:
    def test_element_type(self):
        assert ArchiveProduct.element_type == DomainObjects.COMMAND


class TestCreateCategoryCommand:
    def test_element_type(self):
        assert CreateCategory.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = CreateCategory(name="Electronics")
        assert cmd.name == "Electronics"


class TestUpdateCategoryCommand:
    def test_element_type(self):
        assert UpdateCategory.element_type == DomainObjects.COMMAND


class TestReorderCategoryCommand:
    def test_element_type(self):
        assert ReorderCategory.element_type == DomainObjects.COMMAND


class TestDeactivateCategoryCommand:
    def test_element_type(self):
        assert DeactivateCategory.element_type == DomainObjects.COMMAND
