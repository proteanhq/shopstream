"""Tests for converting float, int and None amounts to 4-place decimals."""

from decimal import Decimal

from shared.money import to_money


class TestToMoney:
    def test_float_converts_through_its_string_form(self):
        # Decimal(0.1) would be 0.1000000000000000055511151231257827...
        assert to_money(0.1) == Decimal("0.1")

    def test_sum_of_converted_tenths_is_exact(self):
        assert to_money(0.1) + to_money(0.2) == Decimal("0.3")

    def test_float_artifacts_round_to_four_places(self):
        assert to_money(3 * 19.99) == Decimal("59.97")

    def test_result_has_four_places(self):
        assert str(to_money(10)) == "10.0000"
        assert str(to_money(Decimal("0.3"))) == "0.3000"

    def test_none_is_zero(self):
        assert to_money(None) == Decimal("0")
        assert str(to_money(None)) == "0.0000"
