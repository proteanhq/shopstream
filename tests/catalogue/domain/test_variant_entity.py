"""Tests for the Variant entity."""

from catalogue.product.product import Price, Variant, Weight
from catalogue.shared.sku import SKU
from protean.utils.reflection import declared_fields


class TestVariantConstruction:
    def test_element_type(self):
        from protean.utils import DomainObjects

        assert Variant.element_type == DomainObjects.ENTITY

    def test_declared_fields(self):
        fields = declared_fields(Variant)
        assert "variant_sku" in fields
        assert "attributes" in fields
        assert "price" in fields
        assert "weight" in fields
        assert "dimensions" in fields
        assert "is_active" in fields

    def test_valid_variant(self):
        sku = SKU(code="VAR-001")
        price = Price(base_price=29.99)
        variant = Variant(variant_sku=sku, price=price)

        assert variant.variant_sku.code == "VAR-001"
        assert variant.price.base_price == 29.99
        assert variant.is_active is True

    def test_variant_with_weight(self):
        sku = SKU(code="VAR-002")
        price = Price(base_price=49.99)
        weight = Weight(value=0.5, unit="kg")
        variant = Variant(variant_sku=sku, price=price, weight=weight)

        assert variant.weight.value == 0.5
        assert variant.weight.unit == "kg"

    def test_variant_with_attributes(self):
        import json

        sku = SKU(code="VAR-003")
        price = Price(base_price=39.99)
        attrs = json.dumps({"size": "L", "color": "Blue"})
        variant = Variant(variant_sku=sku, price=price, attributes=attrs)

        parsed = json.loads(variant.attributes)
        assert parsed["size"] == "L"
        assert parsed["color"] == "Blue"
