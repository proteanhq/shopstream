"""BDD tests for order cancellation."""

from pytest_bdd import parsers, scenarios, when

from ordering.order.cancellation import CancelOrder

scenarios("features/order_cancellation.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(
    parsers.cfparse('the order is cancelled with reason "{reason}" by "{actor}"'),
    target_fixture="order",
)
def _(order, order_id, reason, actor):
    return order.process(CancelOrder(order_id=order_id, reason=reason, cancelled_by=actor))


@when("the order is refunded", target_fixture="order")
def _(order, refund_order):
    return order.process(refund_order)
