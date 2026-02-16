"""Application tests for variant management handlers."""

import json

from catalogue.product.creation import CreateProduct
from catalogue.product.product import Product
from catalogue.product.variants import AddVariant, SetTierPrice, UpdateVariantPrice
from protean.utils.globals import current_domain


def _create_product(**overrides):
    defaults = {"sku": "PROD-001", "title": "Test Product"}
    defaults.update(overrides)
    command = CreateProduct(**defaults)
    return current_domain.process(command, asynchronous=False)


def _add_variant(product_id, **overrides):
    defaults = {
        "product_id": product_id,
        "variant_sku": "VAR-001",
        "base_price": 29.99,
        "currency": "USD",
    }
    defaults.update(overrides)
    command = AddVariant(**defaults)
    current_domain.process(command, asynchronous=False)


class TestAddVariantHandler:
    def test_add_variant(self):
        product_id = _create_product()
        _add_variant(product_id)

        product = current_domain.repository_for(Product).get(product_id)
        assert len(product.variants) == 1
        assert product.variants[0].variant_sku.code == "VAR-001"
        assert product.variants[0].price.base_price == 29.99

    def test_add_variant_with_weight(self):
        product_id = _create_product()
        _add_variant(product_id, weight_value=1.5, weight_unit="kg")

        product = current_domain.repository_for(Product).get(product_id)
        assert product.variants[0].weight.value == 1.5
        assert product.variants[0].weight.unit == "kg"

    def test_add_variant_with_dimensions(self):
        product_id = _create_product()
        _add_variant(product_id, length=10.0, width=5.0, height=3.0, dimension_unit="cm")

        product = current_domain.repository_for(Product).get(product_id)
        assert product.variants[0].dimensions.length == 10.0

    def test_add_variant_with_attributes(self):
        product_id = _create_product()
        attrs = json.dumps({"size": "L", "color": "Blue"})
        _add_variant(product_id, attributes=attrs)

        product = current_domain.repository_for(Product).get(product_id)
        parsed = json.loads(product.variants[0].attributes)
        assert parsed["size"] == "L"

    def test_add_multiple_variants(self):
        product_id = _create_product()
        _add_variant(product_id, variant_sku="VAR-001", base_price=29.99)
        _add_variant(product_id, variant_sku="VAR-002", base_price=39.99)

        product = current_domain.repository_for(Product).get(product_id)
        assert len(product.variants) == 2


class TestUpdateVariantPriceHandler:
    def test_update_variant_price(self):
        product_id = _create_product()
        _add_variant(product_id)

        product = current_domain.repository_for(Product).get(product_id)
        variant_id = product.variants[0].id

        command = UpdateVariantPrice(
            product_id=product_id,
            variant_id=variant_id,
            base_price=49.99,
            currency="USD",
        )
        current_domain.process(command, asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        assert product.variants[0].price.base_price == 49.99


class TestSetTierPriceHandler:
    def test_set_tier_price(self):
        product_id = _create_product()
        _add_variant(product_id, base_price=99.99)

        product = current_domain.repository_for(Product).get(product_id)
        variant_id = product.variants[0].id

        command = SetTierPrice(
            product_id=product_id,
            variant_id=variant_id,
            tier="Silver",
            price=89.99,
        )
        current_domain.process(command, asynchronous=False)

        product = current_domain.repository_for(Product).get(product_id)
        tiers = json.loads(product.variants[0].price.tier_prices)
        assert tiers["Silver"] == 89.99
