"""Tests for converting float, int and None amounts to 4-place decimals."""

from decimal import Decimal

import pytest
from pydantic import BaseModel

from shared.api.money import MoneyOut
from shared.money import has_more_than_four_places, money_fields_as_text, parse_money, to_money


class TestToMoney:
    def test_float_converts_through_its_string_form(self):
        # Decimal(0.1) would be 0.1000000000000000055511151231257827...
        assert to_money(0.1) == Decimal("0.1")
        # Decimal(0.00015) is 0.000149999..., which would round to 0.0001.
        assert str(to_money(0.00015)) == "0.0002"

    def test_rounding_is_half_even(self):
        # Half-up would give 10.0001.
        assert str(to_money(10.00005)) == "10.0000"
        assert str(to_money(10.00015)) == "10.0002"

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

    def test_amount_too_large_for_four_places_is_rejected(self):
        with pytest.raises(ValueError, match="too large"):
            to_money(1e30)


class TestHasMoreThanFourPlaces:
    @pytest.mark.parametrize(
        "value",
        [
            0.0,
            10,
            59.99,
            0.0001,
            0.1 + 0.2,
            0.1 + 0.7,
            3 * 0.3333,
            # Subtraction error is relative to the operands, not the result.
            100 - 99.99,
            5000.05 - 5000,
            1e9 + 0.1 - 1e9,
            2000000000.0004,
            999999999999999.9,
        ],
    )
    def test_four_place_amounts_and_float_error_pass(self, value):
        assert has_more_than_four_places(value) is False

    @pytest.mark.parametrize(
        "value",
        [
            10.00004,
            10.00005,
            0.00004,
            10.12345,
            0.33333,
            1234567.00001,
            99999999.00009,
            1000000000.00005,
            1000000000.00015,
        ],
    )
    def test_a_fifth_decimal_place_is_caught(self, value):
        assert has_more_than_four_places(value) is True

    @pytest.mark.parametrize(
        "value",
        [Decimal("49.99"), Decimal("49.9900"), Decimal("0.30000000000000004"), Decimal("0.0500000000001819")],
    )
    def test_decimals_with_four_places_or_float_error_pass(self, value):
        assert has_more_than_four_places(value) is False

    @pytest.mark.parametrize(
        "value",
        [
            Decimal("10.00005"),
            # Within 1e-7 of a 4-place amount, but written with too few digits to be float error.
            Decimal("49.99000001"),
            Decimal("0.00000001"),
            # Above about 3e10, 4 units in the last place of a float exceed 1e-5.
            Decimal("123456789012.12345"),
            Decimal("123456789012.00001"),
            # 15 or more digits, but not the digits of any float.
            Decimal("0.300000000000000041"),
        ],
    )
    def test_a_decimal_with_a_fifth_place_is_caught(self, value):
        assert has_more_than_four_places(value) is True

    @pytest.mark.parametrize("value", [Decimal("1e999999"), Decimal("-9.99999e999999"), Decimal("0E-10")])
    def test_a_decimal_at_the_edge_of_the_exponent_range_has_no_fifth_place(self, value):
        assert has_more_than_four_places(value) is False

    @pytest.mark.parametrize("value", [49.99000001, 1e-9, 123456789012.12345])
    def test_a_short_or_large_float_with_a_fifth_place_is_caught(self, value):
        assert has_more_than_four_places(value) is True


class TestParseMoney:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("49.9900", "49.9900"),
            ("49.99", "49.9900"),
            (" 49.99 ", "49.9900"),
            (49.99, "49.9900"),
            (0.1 + 0.2, "0.3000"),
            (50, "50.0000"),
            (Decimal("10.00005"), "10.0000"),
            (None, "0.0000"),
        ],
    )
    def test_numbers_and_numeric_strings_parse_to_four_places(self, value, expected):
        assert str(parse_money(value)) == expected

    @pytest.mark.parametrize("value", ["abc", "", True, [1], "1_000", "１２", "٣"])
    def test_non_numbers_raise_value_error(self, value):
        with pytest.raises(ValueError):
            parse_money(value)

    @pytest.mark.parametrize("value", ["NaN", "Infinity"])
    def test_non_finite_strings_raise_value_error(self, value):
        with pytest.raises(ValueError, match="finite"):
            parse_money(value)


class TestMoneyFieldsAsText:
    def test_named_fields_become_four_place_strings(self):
        data = {"amount": 3 * 1.1, "tax": "1.5", "note": 0.1}

        result = money_fields_as_text(data, "amount", "tax")

        assert result == {"amount": "3.3000", "tax": "1.5000", "note": 0.1}

    def test_missing_and_none_fields_are_left_alone(self):
        assert money_fields_as_text({"tax": None}, "amount", "tax") == {"tax": None}


class _Response(BaseModel):
    amount: MoneyOut


class TestMoneyOut:
    @pytest.mark.parametrize("value", [Decimal("49.99"), Decimal("49.9900"), Decimal("49.990000")])
    def test_amount_is_sent_as_a_4_place_string(self, value):
        assert _Response(amount=value).model_dump(mode="json") == {"amount": "49.9900"}
