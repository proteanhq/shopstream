"""Tests for Product lifecycle state machine."""

import pytest
from catalogue.product.events import ProductActivated, ProductArchived, ProductDiscontinued
from catalogue.product.product import Price, Product
from protean.exceptions import ValidationError


def _make_product(**overrides):
    defaults = {"sku": "PROD-001", "title": "Test Product"}
    defaults.update(overrides)
    return Product.create(**defaults)


def _make_active_product():
    product = _make_product()
    price = Price(base_price=29.99)
    product.add_variant(variant_sku="VAR-001", price=price)
    product.activate()
    product._events.clear()
    return product


class TestActivate:
    def test_activate_draft_product_with_variants(self):
        product = _make_product()
        price = Price(base_price=29.99)
        product.add_variant(variant_sku="VAR-001", price=price)
        product._events.clear()

        product.activate()
        assert product.status == "Active"
        assert len(product._events) == 1

        event = product._events[0]
        assert isinstance(event, ProductActivated)
        assert event.sku == "PROD-001"

    def test_activate_without_variants_raises_error(self):
        product = _make_product()
        with pytest.raises(ValidationError) as exc:
            product.activate()
        assert "must have at least one variant" in str(exc.value)

    def test_activate_non_draft_raises_error(self):
        product = _make_active_product()
        with pytest.raises(ValidationError) as exc:
            product.activate()
        assert "Only draft products" in str(exc.value)


class TestDiscontinue:
    def test_discontinue_active_product(self):
        product = _make_active_product()

        product.discontinue()
        assert product.status == "Discontinued"
        assert len(product._events) == 1

        event = product._events[0]
        assert isinstance(event, ProductDiscontinued)

    def test_discontinue_draft_raises_error(self):
        product = _make_product()
        with pytest.raises(ValidationError) as exc:
            product.discontinue()
        assert "Only active products" in str(exc.value)

    def test_discontinue_discontinued_raises_error(self):
        product = _make_active_product()
        product.discontinue()
        product._events.clear()

        with pytest.raises(ValidationError) as exc:
            product.discontinue()
        assert "Only active products" in str(exc.value)


class TestArchive:
    def test_archive_discontinued_product(self):
        product = _make_active_product()
        product.discontinue()
        product._events.clear()

        product.archive()
        assert product.status == "Archived"
        assert len(product._events) == 1

        event = product._events[0]
        assert isinstance(event, ProductArchived)

    def test_archive_draft_raises_error(self):
        product = _make_product()
        with pytest.raises(ValidationError) as exc:
            product.archive()
        assert "Only discontinued products" in str(exc.value)

    def test_archive_active_raises_error(self):
        product = _make_active_product()
        with pytest.raises(ValidationError) as exc:
            product.archive()
        assert "Only discontinued products" in str(exc.value)


class TestFullLifecycle:
    def test_draft_to_active_to_discontinued_to_archived(self):
        product = _make_product()
        price = Price(base_price=29.99)
        product.add_variant(variant_sku="VAR-001", price=price)

        assert product.status == "Draft"
        product.activate()
        assert product.status == "Active"
        product.discontinue()
        assert product.status == "Discontinued"
        product.archive()
        assert product.status == "Archived"

    def test_discontinued_cannot_be_reactivated(self):
        product = _make_active_product()
        product.discontinue()

        with pytest.raises(ValidationError):
            product.activate()

    def test_archived_cannot_be_reactivated(self):
        product = _make_active_product()
        product.discontinue()
        product.archive()

        with pytest.raises(ValidationError):
            product.activate()
