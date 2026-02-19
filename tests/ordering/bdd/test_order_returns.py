"""BDD tests for order returns."""

from ordering.order.returns import RequestReturn
from pytest_bdd import parsers, scenarios, when

scenarios("features/order_returns.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(
    parsers.cfparse('a return is requested with reason "{reason}"'),
    target_fixture="order",
)
def _(order, order_id, reason):
    return order.process(RequestReturn(order_id=order_id, reason=reason))


@when("the return is approved", target_fixture="order")
def _(order, approve_return):
    return order.process(approve_return)


@when("the return is recorded", target_fixture="order")
def _(order, record_return):
    return order.process(record_return)


@when("the order is refunded", target_fixture="order")
def _(order, refund_order):
    return order.process(refund_order)
