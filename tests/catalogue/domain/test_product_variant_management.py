"""Tests for Product variant management."""

import json

import pytest
from catalogue.product.events import TierPriceSet, VariantAdded, VariantPriceChanged
from catalogue.product.product import Dimensions, Price, Product, Weight
from protean.exceptions import ValidationError


def _make_product(**overrides):
    defaults = {"sku": "PROD-001", "title": "Test Product"}
    defaults.update(overrides)
    return Product.create(**defaults)


class TestAddVariant:
    def test_add_variant(self):
        product = _make_product()
        product._events.clear()

        price = Price(base_price=29.99)
        variant = product.add_variant(variant_sku="VAR-001", price=price)

        assert len(product.variants) == 1
        assert variant.variant_sku.code == "VAR-001"
        assert variant.price.base_price == 29.99

    def test_add_variant_with_string_sku(self):
        product = _make_product()
        product._events.clear()

        price = Price(base_price=29.99)
        variant = product.add_variant(variant_sku="VAR-002", price=price)
        assert variant.variant_sku.code == "VAR-002"

    def test_add_variant_with_weight_and_dimensions(self):
        product = _make_product()
        product._events.clear()

        price = Price(base_price=49.99)
        weight = Weight(value=1.2, unit="kg")
        dims = Dimensions(length=10.0, width=5.0, height=3.0, unit="cm")
        variant = product.add_variant(variant_sku="VAR-003", price=price, weight=weight, dimensions=dims)

        assert variant.weight.value == 1.2
        assert variant.dimensions.length == 10.0

    def test_add_variant_with_attributes(self):
        product = _make_product()
        product._events.clear()

        price = Price(base_price=39.99)
        variant = product.add_variant(
            variant_sku="VAR-004",
            price=price,
            attributes={"size": "L", "color": "Blue"},
        )
        parsed = json.loads(variant.attributes)
        assert parsed["size"] == "L"

    def test_add_variant_raises_event(self):
        product = _make_product()
        product._events.clear()

        price = Price(base_price=29.99)
        product.add_variant(variant_sku="VAR-005", price=price)

        assert len(product._events) == 1
        event = product._events[0]
        assert isinstance(event, VariantAdded)
        assert event.variant_sku == "VAR-005"
        assert event.price_amount == 29.99

    def test_add_multiple_variants(self):
        product = _make_product()
        product._events.clear()

        for i in range(3):
            price = Price(base_price=10.0 + i)
            product.add_variant(variant_sku=f"VAR-{i:03d}", price=price)

        assert len(product.variants) == 3


class TestUpdateVariantPrice:
    def test_update_variant_price(self):
        product = _make_product()
        price = Price(base_price=29.99)
        variant = product.add_variant(variant_sku="VAR-001", price=price)
        product._events.clear()

        new_price = Price(base_price=39.99)
        product.update_variant_price(variant.id, new_price)

        assert product.variants[0].price.base_price == 39.99
        assert len(product._events) == 1

        event = product._events[0]
        assert isinstance(event, VariantPriceChanged)
        assert event.previous_price == 29.99
        assert event.new_price == 39.99

    def test_update_nonexistent_variant_raises_error(self):
        product = _make_product()
        new_price = Price(base_price=39.99)
        with pytest.raises(ValidationError) as exc:
            product.update_variant_price("nonexistent-id", new_price)
        assert "not found" in str(exc.value)


class TestSetTierPrice:
    def test_set_tier_price(self):
        product = _make_product()
        price = Price(base_price=99.99)
        variant = product.add_variant(variant_sku="VAR-001", price=price)
        product._events.clear()

        product.set_tier_price(variant.id, "Silver", 89.99)

        tiers = json.loads(product.variants[0].price.tier_prices)
        assert tiers["Silver"] == 89.99
        assert len(product._events) == 1

        event = product._events[0]
        assert isinstance(event, TierPriceSet)
        assert event.tier == "Silver"
        assert event.price == 89.99

    def test_set_multiple_tier_prices(self):
        product = _make_product()
        price = Price(base_price=99.99)
        variant = product.add_variant(variant_sku="VAR-001", price=price)
        product._events.clear()

        product.set_tier_price(variant.id, "Silver", 89.99)
        product.set_tier_price(variant.id, "Gold", 79.99)

        tiers = json.loads(product.variants[0].price.tier_prices)
        assert tiers["Silver"] == 89.99
        assert tiers["Gold"] == 79.99

    def test_set_tier_price_nonexistent_variant_raises_error(self):
        product = _make_product()
        with pytest.raises(ValidationError) as exc:
            product.set_tier_price("nonexistent-id", "Silver", 89.99)
        assert "not found" in str(exc.value)
