"""Tests for the Image entity."""

from catalogue.product.product import Image
from protean.utils.reflection import declared_fields


class TestImageConstruction:
    def test_element_type(self):
        from protean.utils import DomainObjects

        assert Image.element_type == DomainObjects.ENTITY

    def test_declared_fields(self):
        fields = declared_fields(Image)
        assert "url" in fields
        assert "alt_text" in fields
        assert "is_primary" in fields
        assert "display_order" in fields

    def test_valid_image(self):
        image = Image(url="https://cdn.example.com/product.jpg")
        assert image.url == "https://cdn.example.com/product.jpg"
        assert image.is_primary is False
        assert image.display_order == 0

    def test_image_with_all_fields(self):
        image = Image(
            url="https://cdn.example.com/product.jpg",
            alt_text="Product front view",
            is_primary=True,
            display_order=1,
        )
        assert image.alt_text == "Product front view"
        assert image.is_primary is True
        assert image.display_order == 1

    def test_primary_image_flag(self):
        primary = Image(url="https://cdn.example.com/main.jpg", is_primary=True)
        secondary = Image(url="https://cdn.example.com/alt.jpg", is_primary=False)
        assert primary.is_primary is True
        assert secondary.is_primary is False
