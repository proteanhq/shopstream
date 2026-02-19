"""BDD tests for stock lifecycle."""

from pytest_bdd import scenarios, when

scenarios("features/stock_lifecycle.feature")


# ---------------------------------------------------------------------------
# When steps
# These reuse "stock is reserved for an order" and "items are returned to stock"
# from test_stock_reservation.py and test_stock_returns.py,
# but they are also defined in conftest via given steps.
# For the "When" clause we need the steps here.
# ---------------------------------------------------------------------------
@when("stock is reserved for an order", target_fixture="item")
def _(item, reserve_stock):
    return item.process(reserve_stock)


@when("items are returned to stock", target_fixture="item")
def _(item, return_to_stock):
    return item.process(return_to_stock)
