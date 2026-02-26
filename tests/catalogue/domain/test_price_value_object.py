"""Tests for the Price value object."""

import pytest
from protean.exceptions import ValidationError

from catalogue.product.product import Price


class TestPriceConstruction:
    def test_element_type(self):
        from protean.utils import DomainObjects

        assert Price.element_type == DomainObjects.VALUE_OBJECT

    def test_valid_price_with_defaults(self):
        price = Price(base_price=99.99)
        assert price.base_price == 99.99
        assert price.currency == "USD"
        assert price.tier_prices == {}

    def test_valid_price_with_explicit_currency(self):
        price = Price(base_price=49.99, currency="EUR")
        assert price.base_price == 49.99
        assert price.currency == "EUR"

    def test_valid_price_with_tier_prices(self):
        tiers = {"Silver": 89.99, "Gold": 79.99, "Platinum": 69.99}
        price = Price(base_price=99.99, tier_prices=tiers)
        assert price.base_price == 99.99
        assert price.tier_prices["Silver"] == 89.99


class TestPriceInvariants:
    def test_zero_base_price_rejected(self):
        with pytest.raises(ValidationError):
            Price(base_price=0.0)

    def test_negative_base_price_rejected(self):
        with pytest.raises(ValidationError):
            Price(base_price=-1.0)

    def test_missing_base_price_rejected(self):
        with pytest.raises(ValidationError):
            Price(currency="USD")

    def test_tier_price_equal_to_base_rejected(self):
        tiers = {"Silver": 99.99}
        with pytest.raises(ValidationError) as exc:
            Price(base_price=99.99, tier_prices=tiers)
        assert "must be less than base price" in str(exc.value)

    def test_tier_price_greater_than_base_rejected(self):
        tiers = {"Silver": 109.99}
        with pytest.raises(ValidationError) as exc:
            Price(base_price=99.99, tier_prices=tiers)
        assert "must be less than base price" in str(exc.value)

    def test_tier_price_negative_rejected(self):
        tiers = {"Silver": -10.0}
        with pytest.raises(ValidationError) as exc:
            Price(base_price=99.99, tier_prices=tiers)
        assert "must be a positive number" in str(exc.value)

    def test_tier_price_zero_rejected(self):
        tiers = {"Silver": 0}
        with pytest.raises(ValidationError) as exc:
            Price(base_price=99.99, tier_prices=tiers)
        assert "must be a positive number" in str(exc.value)

    def test_invalid_tier_prices_type(self):
        with pytest.raises(ValidationError) as exc:
            Price(base_price=99.99, tier_prices="not-json")
        assert "Invalid value" in str(exc.value) or "valid dictionary" in str(exc.value)

    def test_tier_prices_must_be_dict(self):
        tiers = [89.99, 79.99]
        with pytest.raises(ValidationError) as exc:
            Price(base_price=99.99, tier_prices=tiers)
        assert "must be a JSON object" in str(exc.value) or "Invalid value" in str(exc.value)

    def test_tier_price_string_value_rejected(self):
        tiers = {"Silver": "free"}
        with pytest.raises(ValidationError) as exc:
            Price(base_price=99.99, tier_prices=tiers)
        assert "must be a positive number" in str(exc.value)
