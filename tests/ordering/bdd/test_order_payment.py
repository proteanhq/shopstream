"""BDD tests for order payment."""

from ordering.order.payment import (
    RecordPaymentFailure,
    RecordPaymentPending,
    RecordPaymentSuccess,
)
from pytest_bdd import parsers, scenarios, when

scenarios("features/order_payment.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(
    parsers.cfparse('payment is initiated with ID "{payment_id}" method "{method}"'),
    target_fixture="order",
)
def _(order, order_id, payment_id, method):
    return order.process(RecordPaymentPending(order_id=order_id, payment_id=payment_id, payment_method=method))


@when(
    parsers.cfparse('payment succeeds with ID "{payment_id}" amount {amount:f} method "{method}"'),
    target_fixture="order",
)
def _(order, order_id, payment_id, amount, method):
    return order.process(
        RecordPaymentSuccess(
            order_id=order_id,
            payment_id=payment_id,
            amount=amount,
            payment_method=method,
        )
    )


@when(
    parsers.cfparse('payment fails with ID "{payment_id}" reason "{reason}"'),
    target_fixture="order",
)
def _(order, order_id, payment_id, reason):
    return order.process(RecordPaymentFailure(order_id=order_id, payment_id=payment_id, reason=reason))
