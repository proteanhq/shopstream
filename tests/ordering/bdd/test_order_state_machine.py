"""BDD tests for order state machine."""

from pytest_bdd import scenarios, when

scenarios("features/order_state_machine.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("the order is confirmed", target_fixture="order")
def _(order, confirm_order):
    return order.process(confirm_order)


@when("the order is completed", target_fixture="order")
def _(order, complete_order):
    return order.process(complete_order)
