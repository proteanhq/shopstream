"""Tests for Product image management."""

import pytest
from catalogue.product.events import ProductImageAdded, ProductImageRemoved
from catalogue.product.product import Product
from protean.exceptions import ValidationError


def _make_product(**overrides):
    defaults = {"sku": "PROD-001", "title": "Test Product"}
    defaults.update(overrides)
    return Product.create(**defaults)


class TestAddImage:
    def test_add_first_image_becomes_primary(self):
        product = _make_product()
        product._events.clear()

        image = product.add_image(url="https://cdn.example.com/img1.jpg")
        assert image.is_primary is True
        assert len(product.images) == 1

    def test_add_second_image_not_primary(self):
        product = _make_product()
        product.add_image(url="https://cdn.example.com/img1.jpg")
        product._events.clear()

        image = product.add_image(url="https://cdn.example.com/img2.jpg")
        assert image.is_primary is False
        assert len(product.images) == 2

    def test_add_image_with_primary_flag(self):
        product = _make_product()
        product.add_image(url="https://cdn.example.com/img1.jpg")  # primary
        product._events.clear()

        image = product.add_image(url="https://cdn.example.com/img2.jpg", is_primary=True)
        assert image.is_primary is True
        # Previous primary should be unset
        assert product.images[0].is_primary is False

    def test_add_image_with_alt_text(self):
        product = _make_product()
        product._events.clear()

        image = product.add_image(
            url="https://cdn.example.com/img1.jpg",
            alt_text="Product front view",
        )
        assert image.alt_text == "Product front view"

    def test_add_image_raises_event(self):
        product = _make_product()
        product._events.clear()

        product.add_image(url="https://cdn.example.com/img1.jpg")
        assert len(product._events) == 1
        event = product._events[0]
        assert isinstance(event, ProductImageAdded)
        assert event.url == "https://cdn.example.com/img1.jpg"
        assert event.is_primary == "True"

    def test_add_image_display_order(self):
        product = _make_product()
        product.add_image(url="https://cdn.example.com/img1.jpg")
        product.add_image(url="https://cdn.example.com/img2.jpg")
        product.add_image(url="https://cdn.example.com/img3.jpg")

        assert product.images[0].display_order == 0
        assert product.images[1].display_order == 1
        assert product.images[2].display_order == 2


class TestRemoveImage:
    def test_remove_non_primary_image(self):
        product = _make_product()
        product.add_image(url="https://cdn.example.com/img1.jpg")  # primary
        img2 = product.add_image(url="https://cdn.example.com/img2.jpg")
        product._events.clear()

        product.remove_image(img2.id)
        assert len(product.images) == 1
        assert len(product._events) == 1
        event = product._events[0]
        assert isinstance(event, ProductImageRemoved)

    def test_remove_primary_reassigns(self):
        product = _make_product()
        img1 = product.add_image(url="https://cdn.example.com/img1.jpg")  # primary
        product.add_image(url="https://cdn.example.com/img2.jpg")
        product._events.clear()

        product.remove_image(img1.id)
        assert len(product.images) == 1
        # Remaining image should become primary
        assert product.images[0].is_primary is True

    def test_remove_last_image(self):
        product = _make_product()
        img = product.add_image(url="https://cdn.example.com/img1.jpg")
        product._events.clear()

        product.remove_image(img.id)
        assert len(product.images) == 0

    def test_remove_nonexistent_image_raises_error(self):
        product = _make_product()
        with pytest.raises(ValidationError) as exc:
            product.remove_image("nonexistent-id")
        assert "not found" in str(exc.value)
