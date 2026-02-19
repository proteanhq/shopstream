"""BDD tests for product details management."""

import json

from catalogue.product.product import SEO
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/product_details.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(parsers.cfparse('the product title is updated to "{title}"'))
def update_title(product, title):
    product.update_details(title=title)


@when(parsers.cfparse('the product description is updated to "{description}"'))
def update_description(product, description):
    product.update_details(description=description)


@when(parsers.cfparse('the product brand is updated to "{brand}"'))
def update_brand(product, brand):
    product.update_details(brand=brand)


@when(parsers.cfparse("the product attributes are updated to '{attributes}'"))
def update_attributes(product, attributes):
    product.update_details(attributes=json.loads(attributes))


@when(parsers.cfparse('the product SEO is updated with slug "{slug}"'))
def update_seo(product, slug):
    product.update_details(seo=SEO(slug=slug))


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the product description is "{description}"'))
def product_description_is(product, description):
    assert product.description == description


@then(parsers.cfparse('the product brand is "{brand}"'))
def product_brand_is(product, brand):
    assert product.brand == brand


@then("the product has attributes")
def product_has_attributes(product):
    assert product.attributes is not None


@then(parsers.cfparse('the product SEO slug is "{slug}"'))
def product_seo_slug_is(product, slug):
    assert product.seo.slug == slug
