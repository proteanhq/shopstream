"""Tests for converting float, int and None amounts to 4-place decimals."""

from decimal import Decimal

import pytest

from shared.money import has_more_than_four_places, to_money


class TestToMoney:
    def test_float_converts_through_its_string_form(self):
        # Decimal(0.1) would be 0.1000000000000000055511151231257827...
        assert to_money(0.1) == Decimal("0.1")

    def test_sum_of_converted_tenths_is_exact(self):
        assert to_money(0.1) + to_money(0.2) == Decimal("0.3")

    def test_float_artifacts_round_to_four_places(self):
        # 0.1 + 0.2 is 0.30000000000000004 as a float.
        assert str(to_money(0.1 + 0.2)) == "0.3000"

    def test_a_fifth_decimal_place_is_rounded(self):
        assert str(to_money(10.00006)) == "10.0001"

    def test_result_has_four_places(self):
        assert str(to_money(10)) == "10.0000"
        assert str(to_money(Decimal("0.3"))) == "0.3000"

    def test_none_is_zero(self):
        assert to_money(None) == Decimal("0")
        assert str(to_money(None)) == "0.0000"

    def test_bool_is_rejected(self):
        with pytest.raises(TypeError):
            to_money(True)

    def test_string_is_rejected(self):
        with pytest.raises(TypeError):
            to_money("0.1")

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), Decimal("NaN")])
    def test_non_finite_values_are_rejected(self, value):
        with pytest.raises(ValueError):
            to_money(value)


class TestHasMoreThanFourPlaces:
    @pytest.mark.parametrize("value", [0.0, 10, 59.99, 0.0001, 0.1 + 0.2, 0.1 + 0.7, 3 * 0.3333])
    def test_four_place_amounts_and_float_error_pass(self, value):
        assert has_more_than_four_places(value) is False

    @pytest.mark.parametrize("value", [10.00004, 10.00005, 0.00004, 10.12345, 0.33333])
    def test_a_fifth_decimal_place_is_caught(self, value):
        assert has_more_than_four_places(value) is True
