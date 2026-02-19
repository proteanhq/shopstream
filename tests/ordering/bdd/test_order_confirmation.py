"""BDD tests for order confirmation."""

from pytest_bdd import scenarios, when

scenarios("features/order_confirmation.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("the order is confirmed", target_fixture="order")
def _(order, confirm_order):
    return order.process(confirm_order)
