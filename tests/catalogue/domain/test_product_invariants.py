"""Tests for Product aggregate invariants."""

import pytest
from catalogue.product.product import Price, Product
from protean.exceptions import ValidationError


def _make_product(**overrides):
    defaults = {"sku": "PROD-001", "title": "Test Product"}
    defaults.update(overrides)
    return Product.create(**defaults)


class TestMaxImagesInvariant:
    def test_10_images_allowed(self):
        product = _make_product()
        for i in range(10):
            product.add_image(url=f"https://cdn.example.com/img{i}.jpg")
        assert len(product.images) == 10

    def test_11th_image_rejected(self):
        product = _make_product()
        for i in range(10):
            product.add_image(url=f"https://cdn.example.com/img{i}.jpg")

        with pytest.raises(ValidationError) as exc:
            product.add_image(url="https://cdn.example.com/img10.jpg")
        assert "Cannot have more than 10 images" in str(exc.value)


class TestPrimaryImageInvariant:
    def test_first_image_auto_primary(self):
        product = _make_product()
        product.add_image(url="https://cdn.example.com/img1.jpg")
        assert product.images[0].is_primary is True

    def test_single_primary_when_multiple_images(self):
        product = _make_product()
        product.add_image(url="https://cdn.example.com/img1.jpg")
        product.add_image(url="https://cdn.example.com/img2.jpg")
        product.add_image(url="https://cdn.example.com/img3.jpg")

        primaries = [i for i in product.images if i.is_primary]
        assert len(primaries) == 1

    def test_setting_new_primary_unsets_old(self):
        product = _make_product()
        product.add_image(url="https://cdn.example.com/img1.jpg")
        product.add_image(url="https://cdn.example.com/img2.jpg", is_primary=True)

        assert product.images[0].is_primary is False
        assert product.images[1].is_primary is True

    def test_removing_primary_reassigns_to_first(self):
        product = _make_product()
        img1 = product.add_image(url="https://cdn.example.com/img1.jpg")  # primary
        product.add_image(url="https://cdn.example.com/img2.jpg")
        product.add_image(url="https://cdn.example.com/img3.jpg")

        product.remove_image(img1.id)

        assert len(product.images) == 2
        primaries = [i for i in product.images if i.is_primary]
        assert len(primaries) == 1
        assert product.images[0].is_primary is True


class TestActivationRequiresVariants:
    def test_cannot_activate_without_variants(self):
        product = _make_product()
        with pytest.raises(ValidationError) as exc:
            product.activate()
        assert "must have at least one variant" in str(exc.value)

    def test_can_activate_with_variant(self):
        product = _make_product()
        price = Price(base_price=29.99)
        product.add_variant(variant_sku="VAR-001", price=price)
        product.activate()
        assert product.status == "Active"


class TestNoReactivationFromDiscontinued:
    def test_discontinued_cannot_go_back_to_active(self):
        product = _make_product()
        price = Price(base_price=29.99)
        product.add_variant(variant_sku="VAR-001", price=price)
        product.activate()
        product.discontinue()

        with pytest.raises(ValidationError):
            product.activate()

    def test_archived_cannot_go_back(self):
        product = _make_product()
        price = Price(base_price=29.99)
        product.add_variant(variant_sku="VAR-001", price=price)
        product.activate()
        product.discontinue()
        product.archive()

        with pytest.raises(ValidationError):
            product.activate()

        with pytest.raises(ValidationError):
            product.discontinue()
