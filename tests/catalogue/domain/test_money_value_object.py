"""Tests for the Money value object."""

from decimal import Decimal

import pytest
from protean.exceptions import ValidationError
from protean.utils.reflection import declared_fields

from catalogue.shared.money import VALID_CURRENCIES, Money


class TestMoneyConstruction:
    def test_element_type(self):
        from protean.utils import DomainObjects

        assert Money.element_type == DomainObjects.VALUE_OBJECT

    def test_declared_fields(self):
        fields = declared_fields(Money)
        assert "amount" in fields
        assert "currency" in fields

    def test_valid_money_with_defaults(self):
        money = Money(amount=10.0)
        assert money.amount == 10.0
        assert money.currency == "USD"

    def test_valid_money_with_explicit_currency(self):
        money = Money(amount=Decimal("99.99"), currency="EUR")
        assert money.amount == Decimal("99.99")
        assert isinstance(money.amount, Decimal)
        assert money.currency == "EUR"

    def test_zero_amount_is_valid(self):
        money = Money(amount=0.0)
        assert money.amount == Decimal("0")
        assert isinstance(money.amount, Decimal)

    def test_large_amount(self):
        money = Money(amount=Decimal("999999.99"), currency="JPY")
        assert money.amount == Decimal("999999.99")

    def test_sum_of_tenths_is_exact(self):
        money = Money(amount=Decimal("0.1") + Decimal("0.2"))
        assert money.amount == Decimal("0.3")


class TestMoneyInvariants:
    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            Money(amount=-0.01)

    def test_more_than_four_decimal_places_rejected(self):
        with pytest.raises(ValidationError):
            Money(amount=Decimal("0.12345"))

    def test_more_than_nineteen_digits_rejected(self):
        with pytest.raises(ValidationError):
            Money(amount=Decimal("1" * 16 + ".0001"))

    def test_missing_amount_rejected(self):
        with pytest.raises(ValidationError):
            Money(currency="USD")

    def test_unsupported_currency_rejected(self):
        with pytest.raises(ValidationError) as exc:
            Money(amount=10.0, currency="XYZ")
        assert "Unsupported currency" in str(exc.value)

    def test_empty_currency_rejected(self):
        with pytest.raises(ValidationError):
            Money(amount=10.0, currency="")

    @pytest.mark.parametrize("currency", sorted(VALID_CURRENCIES))
    def test_all_valid_currencies_accepted(self, currency):
        money = Money(amount=1.0, currency=currency)
        assert money.currency == currency

    @pytest.mark.parametrize(
        "currency",
        ["ABC", "XYZ", "FOO", "xxx", "us", "USDD"],
        ids=["ABC", "XYZ", "FOO", "lowercase", "too-short", "too-long"],
    )
    def test_invalid_currencies_rejected(self, currency):
        with pytest.raises(ValidationError):
            Money(amount=1.0, currency=currency)
