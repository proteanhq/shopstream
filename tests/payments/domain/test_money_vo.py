"""Tests for Money value object."""

from decimal import Decimal

import pytest
from protean.exceptions import ValidationError

from payments.payment.payment import Money


class TestMoney:
    def test_default_currency(self):
        money = Money(value=Decimal("50"))
        assert money.currency == "USD"

    def test_default_value(self):
        money = Money(currency="EUR")
        assert money.value == Decimal("0")
        assert isinstance(money.value, Decimal)

    def test_custom_values(self):
        money = Money(currency="GBP", value=Decimal("99.99"))
        assert money.currency == "GBP"
        assert money.value == Decimal("99.99")

    def test_zero_amount(self):
        money = Money(currency="USD", value=Decimal("0"))
        assert money.value == Decimal("0")

    def test_more_than_four_decimal_places_rejected(self):
        with pytest.raises(ValidationError):
            Money(value=Decimal("0.12345"))
