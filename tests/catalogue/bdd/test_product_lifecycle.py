"""BDD tests for product lifecycle."""

from protean.exceptions import ValidationError
from pytest_bdd import scenarios, when

scenarios("features/product_lifecycle.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("the product is activated")
def activate_product(product, error):
    try:
        product.activate()
    except ValidationError as exc:
        error["exc"] = exc


@when("the product is discontinued")
def discontinue_product(product, error):
    try:
        product.discontinue()
    except ValidationError as exc:
        error["exc"] = exc


@when("the product is archived")
def archive_product(product, error):
    try:
        product.archive()
    except ValidationError as exc:
        error["exc"] = exc
