"""BDD tests for product image management."""

from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/product_images.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(parsers.cfparse('an image is added with URL "{url}"'))
def add_image(product, url, error):
    try:
        product.add_image(url=url)
    except ValidationError as exc:
        error["exc"] = exc


@when("the non-primary image is removed")
def remove_non_primary_image(product):
    non_primary = next(i for i in product.images if not i.is_primary)
    product.remove_image(non_primary.id)


@when("the primary image is removed")
def remove_primary_image(product):
    primary = next(i for i in product.images if i.is_primary)
    product.remove_image(primary.id)


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse("the product has {count:d} image"))
def product_has_n_images_singular(product, count):
    assert len(product.images) == count


@then(parsers.cfparse("the product has {count:d} images"))
def product_has_n_images(product, count):
    assert len(product.images) == count


@then("the first image is primary")
def first_image_is_primary(product):
    assert product.images[0].is_primary is True


@then("the remaining image is primary")
def remaining_image_is_primary(product):
    assert len(product.images) == 1
    assert product.images[0].is_primary is True
