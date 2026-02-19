"""BDD tests for cart lifecycle."""

from ordering.cart.cart import ShoppingCart
from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/cart_lifecycle.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(
    parsers.cfparse('a cart is created for customer "{customer_id}"'),
    target_fixture="cart",
)
def create_customer_cart(customer_id):
    return ShoppingCart.create(customer_id=customer_id)


@when(
    parsers.cfparse('a guest cart is created with session "{session_id}"'),
    target_fixture="cart",
)
def create_guest_cart(session_id):
    return ShoppingCart.create(session_id=session_id)


@when("the cart is converted to an order")
def convert_cart(cart, error):
    try:
        cart.convert_to_order()
    except ValidationError as exc:
        error["exc"] = exc


@when("the cart is abandoned")
def abandon_cart(cart, error):
    try:
        cart.abandon()
    except ValidationError as exc:
        error["exc"] = exc


@when(
    parsers.cfparse('guest cart items are merged with product "{product_id}" variant "{variant_id}" quantity {qty:d}')
)
def merge_guest_cart(cart, product_id, variant_id, qty):
    cart.merge_guest_cart([{"product_id": product_id, "variant_id": variant_id, "quantity": qty}])


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse("the cart has {count:d} item"))
def cart_has_n_items_singular(cart, count):
    assert len(cart.items) == count
