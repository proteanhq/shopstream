"""Tests for Money value object."""

from payments.payment.payment import Money


class TestMoney:
    def test_default_currency(self):
        money = Money(value=50.0)
        assert money.currency == "USD"

    def test_default_value(self):
        money = Money(currency="EUR")
        assert money.value == 0.0

    def test_custom_values(self):
        money = Money(currency="GBP", value=99.99)
        assert money.currency == "GBP"
        assert money.value == 99.99

    def test_zero_amount(self):
        money = Money(currency="USD", value=0.0)
        assert money.value == 0.0
