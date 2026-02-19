"""BDD tests for order modification."""

from ordering.order.modification import AddItem, ApplyCoupon, RemoveItem, UpdateItemQuantity
from pytest_bdd import parsers, scenarios, when

scenarios("features/order_modification.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("an item is added to the order", target_fixture="order")
def _(order, order_id):
    return order.process(
        AddItem(
            order_id=order_id,
            product_id="prod-002",
            variant_id="var-002",
            sku="SKU-002",
            title="Another Product",
            quantity=1,
            unit_price=15.0,
        )
    )


@when("an item is removed from the order", target_fixture="order")
def _(order, order_id):
    return order.process(RemoveItem(order_id=order_id, item_id="item-1"))


@when(
    parsers.cfparse("the item quantity is updated to {qty:d}"),
    target_fixture="order",
)
def _(order, order_id, qty):
    return order.process(UpdateItemQuantity(order_id=order_id, item_id="item-1", new_quantity=qty))


@when(parsers.cfparse('a coupon "{code}" is applied'), target_fixture="order")
def _(order, order_id, code):
    return order.process(ApplyCoupon(order_id=order_id, coupon_code=code))
