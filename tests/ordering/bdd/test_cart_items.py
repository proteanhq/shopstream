"""BDD tests for cart item management."""

from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/cart_items.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(
    parsers.cfparse('an item is added to the cart with product "{product_id}" variant "{variant_id}" quantity {qty:d}')
)
def add_item_to_cart(cart, product_id, variant_id, qty, error):
    try:
        cart.add_item(product_id=product_id, variant_id=variant_id, quantity=qty)
    except ValidationError as exc:
        error["exc"] = exc


@when(parsers.cfparse("the cart item quantity is updated to {qty:d}"))
def update_cart_item_quantity(cart, qty):
    item = cart.items[0]
    cart.update_item_quantity(str(item.id), qty)


@when("the cart item is removed")
def remove_cart_item(cart):
    item = cart.items[0]
    cart.remove_item(str(item.id))


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse("the cart has {count:d} item"))
def cart_has_n_items_singular(cart, count):
    assert len(cart.items) == count


@then(parsers.cfparse("the cart has {count:d} items"))
def cart_has_n_items(cart, count):
    assert len(cart.items) == count
