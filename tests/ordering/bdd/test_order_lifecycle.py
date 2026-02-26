"""BDD tests for order lifecycle."""

from pytest_bdd import parsers, scenarios, when

from ordering.order.payment import RecordPaymentFailure

scenarios("features/order_lifecycle.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("the order is completed", target_fixture="order")
def _(order, complete_order):
    return order.process(complete_order)


@when("the order is refunded", target_fixture="order")
def _(order, refund_order):
    return order.process(refund_order)


@when(
    parsers.cfparse('payment fails with ID "{payment_id}" reason "{reason}"'),
    target_fixture="order",
)
def _(order, order_id, payment_id, reason):
    return order.process(RecordPaymentFailure(order_id=order_id, payment_id=payment_id, reason=reason))
