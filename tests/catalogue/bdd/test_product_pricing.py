"""BDD tests for product pricing."""

import json

from catalogue.product.product import Price
from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/product_pricing.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(parsers.cfparse("the variant price is updated to {price:f}"))
def update_variant_price(product, price):
    variant = product.variants[0]
    product.update_variant_price(variant.id, Price(base_price=price))


@when(parsers.cfparse("the {tier} tier price is set to {price:f}"))
def set_tier_price(product, tier, price, error):
    variant = product.variants[0]
    try:
        product.set_tier_price(variant.id, tier, price)
    except ValidationError as exc:
        error["exc"] = exc


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse("the variant base price is {price:f}"))
def variant_base_price_is(product, price):
    assert product.variants[0].price.base_price == price


@then(parsers.cfparse("the variant has a {tier} tier price of {price:f}"))
def variant_has_tier_price(product, tier, price):
    variant = product.variants[0]
    tiers = json.loads(variant.price.tier_prices)
    assert tiers[tier] == price
