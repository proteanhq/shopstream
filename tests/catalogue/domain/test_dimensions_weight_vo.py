"""Tests for Dimensions and Weight value objects."""

import pytest
from catalogue.product.product import Dimensions, Weight
from protean.exceptions import ValidationError


class TestDimensionsConstruction:
    def test_element_type(self):
        from protean.utils import DomainObjects

        assert Dimensions.element_type == DomainObjects.VALUE_OBJECT

    def test_valid_dimensions_defaults(self):
        dims = Dimensions(length=10.0, width=5.0, height=3.0)
        assert dims.length == 10.0
        assert dims.width == 5.0
        assert dims.height == 3.0
        assert dims.unit == "cm"

    def test_valid_dimensions_inches(self):
        dims = Dimensions(length=4.0, width=2.0, height=1.0, unit="in")
        assert dims.unit == "in"

    def test_zero_dimensions_valid(self):
        dims = Dimensions(length=0.0, width=0.0, height=0.0)
        assert dims.length == 0.0


class TestDimensionsInvariants:
    def test_invalid_unit_rejected(self):
        with pytest.raises(ValidationError) as exc:
            Dimensions(length=10.0, width=5.0, height=3.0, unit="ft")
        assert "must be 'cm' or 'in'" in str(exc.value)

    def test_negative_length_rejected(self):
        with pytest.raises(ValidationError):
            Dimensions(length=-1.0, width=5.0, height=3.0)

    def test_negative_width_rejected(self):
        with pytest.raises(ValidationError):
            Dimensions(length=10.0, width=-1.0, height=3.0)

    def test_negative_height_rejected(self):
        with pytest.raises(ValidationError):
            Dimensions(length=10.0, width=5.0, height=-1.0)


class TestWeightConstruction:
    def test_element_type(self):
        from protean.utils import DomainObjects

        assert Weight.element_type == DomainObjects.VALUE_OBJECT

    def test_valid_weight_defaults(self):
        w = Weight(value=1.5)
        assert w.value == 1.5
        assert w.unit == "kg"

    @pytest.mark.parametrize("unit", ["kg", "lb", "g", "oz"])
    def test_valid_units(self, unit):
        w = Weight(value=1.0, unit=unit)
        assert w.unit == unit

    def test_zero_weight_valid(self):
        w = Weight(value=0.0)
        assert w.value == 0.0


class TestWeightInvariants:
    def test_invalid_unit_rejected(self):
        with pytest.raises(ValidationError) as exc:
            Weight(value=1.0, unit="st")
        assert "must be 'kg', 'lb', 'g', or 'oz'" in str(exc.value)

    def test_negative_weight_rejected(self):
        with pytest.raises(ValidationError):
            Weight(value=-0.1)
