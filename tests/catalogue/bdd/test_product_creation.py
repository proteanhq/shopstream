"""BDD tests for product creation."""

from catalogue.product.product import Product
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/product_creation.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(
    parsers.cfparse('a product is created with SKU "{sku}" and title "{title}"'),
    target_fixture="product",
)
def create_product(sku, title):
    return Product.create(sku=sku, title=title)


@when(
    parsers.cfparse(
        'a product is created with SKU "{sku}" title "{title}" seller "{seller_id}" category "{category_id}" brand "{brand}"'
    ),
    target_fixture="product",
)
def create_product_full(sku, title, seller_id, category_id, brand):
    return Product.create(
        sku=sku,
        title=title,
        seller_id=seller_id,
        category_id=category_id,
        brand=brand,
    )


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the product visibility is "{visibility}"'))
def product_visibility_is(product, visibility):
    assert product.visibility == visibility


@then(parsers.cfparse("the product has {count:d} variants"))
def product_has_n_variants(product, count):
    assert len(product.variants) == count


@then(parsers.cfparse("the product has {count:d} images"))
def product_has_n_images(product, count):
    assert len(product.images) == count


@then(parsers.cfparse('the product brand is "{brand}"'))
def product_brand_is(product, brand):
    assert product.brand == brand


@then("the product has a created_at timestamp")
def product_has_created_at(product):
    assert product.created_at is not None


@then("the product has an updated_at timestamp")
def product_has_updated_at(product):
    assert product.updated_at is not None
