"""Tests for the SKU value object."""

import pytest
from catalogue.shared.sku import SKU
from protean.exceptions import ValidationError
from protean.utils.reflection import declared_fields


class TestSKUConstruction:
    def test_element_type(self):
        from protean.utils import DomainObjects

        assert SKU.element_type == DomainObjects.VALUE_OBJECT

    def test_declared_fields(self):
        fields = declared_fields(SKU)
        assert "code" in fields

    @pytest.mark.parametrize(
        "code",
        [
            "ELEC-PHN-001",
            "SHOE-RUN-BLK-42",
            "ABC",
            "A1B",
            "PRODUCT123",
            "a-b-c",
            "simple",
            "X" * 50,
        ],
        ids=[
            "standard-sku",
            "four-segment",
            "min-length",
            "mixed-alphanum",
            "no-hyphens",
            "lowercase",
            "alpha-only",
            "max-length",
        ],
    )
    def test_valid_sku_formats(self, code):
        sku = SKU(code=code)
        assert sku.code == code


class TestSKUInvariants:
    def test_missing_code_rejected(self):
        with pytest.raises(ValidationError):
            SKU()

    def test_too_short_rejected(self):
        with pytest.raises(ValidationError):
            SKU(code="AB")

    def test_too_long_rejected(self):
        with pytest.raises(ValidationError):
            SKU(code="X" * 51)

    def test_leading_hyphen_rejected(self):
        with pytest.raises(ValidationError) as exc:
            SKU(code="-ABC-123")
        assert "must not start or end with a hyphen" in str(exc.value)

    def test_trailing_hyphen_rejected(self):
        with pytest.raises(ValidationError) as exc:
            SKU(code="ABC-123-")
        assert "must not start or end with a hyphen" in str(exc.value)

    def test_consecutive_hyphens_rejected(self):
        with pytest.raises(ValidationError) as exc:
            SKU(code="ABC--123")
        assert "consecutive hyphens" in str(exc.value)

    @pytest.mark.parametrize(
        "code",
        ["ABC 123", "ABC.123", "ABC_123", "ABC@123", "ABC#123", "ABC!123"],
        ids=["space", "dot", "underscore", "at-sign", "hash", "exclamation"],
    )
    def test_special_characters_rejected(self, code):
        with pytest.raises(ValidationError) as exc:
            SKU(code=code)
        assert "alphanumeric" in str(exc.value)
