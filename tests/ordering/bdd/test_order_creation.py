"""BDD tests for order creation."""

from ordering.order.order import Order
from protean.testing import given as given_
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/order_creation.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("a new order is created with one item", target_fixture="order")
def _(create_order):
    return given_(Order).process(create_order)


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the order customer ID is "{customer_id}"'))
def _(order, customer_id):
    assert str(order.customer_id) == customer_id


@then(parsers.cfparse("the order subtotal is {amount:f}"))
def _(order, amount):
    assert order.pricing.subtotal == amount


@then(parsers.cfparse("the order grand total is {amount:f}"))
def _(order, amount):
    assert order.pricing.grand_total == amount


@then(parsers.cfparse("the order has {count:d} item"))
def _(order, count):
    assert len(order.items) == count


@then("the order has a created_at timestamp")
def _(order):
    assert order.created_at is not None
