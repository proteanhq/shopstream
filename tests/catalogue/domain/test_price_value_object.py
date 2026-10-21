"""Tests for the Price value object."""

from decimal import Decimal

import pytest
from protean.exceptions import ValidationError

from catalogue.product.product import Price, TierPrice


class TestPriceConstruction:
    def test_element_type(self):
        from protean.utils import DomainObjects

        assert Price.element_type == DomainObjects.VALUE_OBJECT

    def test_valid_price_with_defaults(self):
        price = Price(base_price=99.99)
        assert price.base_price == Decimal("99.99")
        assert price.currency == "USD"
        assert price.tier_prices == {}

    def test_valid_price_with_explicit_currency(self):
        price = Price(base_price=49.99, currency="EUR")
        assert price.base_price == Decimal("49.99")
        assert price.currency == "EUR"

    def test_valid_price_with_tier_prices(self):
        tiers = {"Silver": {"amount": 89.99}, "Gold": {"amount": 79.99}, "Platinum": {"amount": 69.99}}
        price = Price(base_price=99.99, tier_prices=tiers)
        assert price.base_price == Decimal("99.99")
        assert isinstance(price.tier_prices["Silver"], TierPrice)
        assert price.tier_prices["Silver"].amount == Decimal("89.99")

    def test_tier_prices_accept_tier_price_instances(self):
        price = Price(base_price=99.99, tier_prices={"Gold": TierPrice(amount=Decimal("79.99"))})
        assert price.tier_prices["Gold"].amount == Decimal("79.99")


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

    @pytest.mark.parametrize("amount", [99.99, 109.99])
    def test_tier_price_at_or_above_base_rejected(self, amount):
        with pytest.raises(ValidationError) as exc:
            Price(base_price=99.99, tier_prices={"Silver": {"amount": amount}})
        assert "must be less than base price" in str(exc.value)

    def test_tier_price_just_below_base_accepted(self):
        price = Price(base_price=99.99, tier_prices={"Silver": {"amount": 99.9899}})
        assert price.tier_prices["Silver"].amount == Decimal("99.9899")

    @pytest.mark.parametrize("tier_prices", ["not-json", [89.99, 79.99], None])
    def test_tier_prices_must_be_dict(self, tier_prices):
        with pytest.raises(ValidationError) as exc:
            Price(base_price=99.99, tier_prices=tier_prices)
        assert "valid dictionary" in str(exc.value)

    def test_bare_number_tier_value_rejected(self):
        with pytest.raises(ValidationError) as exc:
            Price(base_price=99.99, tier_prices={"Silver": 89.99})
        assert "instance of TierPrice" in str(exc.value)


class TestTierPrice:
    def test_positive_amount(self):
        assert TierPrice(amount=9.99).amount == Decimal("9.99")

    @pytest.mark.parametrize("amount", [-1, 0])
    def test_non_positive_amount_rejected(self, amount):
        with pytest.raises(ValidationError) as exc:
            TierPrice(amount=amount)
        assert exc.value.messages == {"amount": ["Tier price must be a positive number"]}

    def test_missing_amount_rejected(self):
        with pytest.raises(ValidationError) as exc:
            TierPrice()
        assert "amount" in exc.value.messages

    def test_non_positive_amount_inside_price_rejected(self):
        with pytest.raises(ValidationError) as exc:
            Price(base_price=99.99, tier_prices={"Silver": {"amount": 0}})
        assert "Tier price must be a positive number" in str(exc.value)
