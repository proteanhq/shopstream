"""BDD tests for product variant management."""

from catalogue.product.product import Price, Weight
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/product_variants.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(parsers.cfparse('a variant is added with SKU "{sku}" and price {price:f}'))
def add_variant(product, sku, price):
    product.add_variant(
        variant_sku=sku,
        price=Price(base_price=price),
    )


@when(parsers.cfparse('a variant is added with SKU "{sku}" price {price:f} and weight {weight:f}'))
def add_variant_with_weight(product, sku, price, weight):
    product.add_variant(
        variant_sku=sku,
        price=Price(base_price=price),
        weight=Weight(value=weight),
    )


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse("the product has {count:d} variant"))
def product_has_n_variants_singular(product, count):
    assert len(product.variants) == count


@then(parsers.cfparse("the product has {count:d} variants"))
def product_has_n_variants(product, count):
    assert len(product.variants) == count


@then(parsers.cfparse('the variant SKU is "{sku}"'))
def variant_sku_is(product, sku):
    assert product.variants[-1].variant_sku.code == sku


@then(parsers.cfparse("the variant weight is {weight:f}"))
def variant_weight_is(product, weight):
    assert product.variants[-1].weight.value == weight
