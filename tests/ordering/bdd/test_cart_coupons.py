"""BDD tests for cart coupon management."""

from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, when

scenarios("features/cart_coupons.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(parsers.cfparse('a coupon "{code}" is applied to the cart'))
def apply_coupon_to_cart(cart, code, error):
    try:
        cart.apply_coupon(code)
    except ValidationError as exc:
        error["exc"] = exc
