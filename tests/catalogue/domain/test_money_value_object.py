"""Tests for the Money value object."""

import pytest
from catalogue.shared.money import VALID_CURRENCIES, Money
from protean.exceptions import ValidationError
from protean.utils.reflection import declared_fields


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
        money = Money(amount=99.99, currency="EUR")
        assert money.amount == 99.99
        assert money.currency == "EUR"

    def test_zero_amount_is_valid(self):
        money = Money(amount=0.0)
        assert money.amount == 0.0

    def test_large_amount(self):
        money = Money(amount=999999.99, currency="JPY")
        assert money.amount == 999999.99


class TestMoneyInvariants:
    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            Money(amount=-0.01)

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
