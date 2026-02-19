"""BDD tests for stock commitment."""

from pytest_bdd import scenarios, when

scenarios("features/stock_commitment.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("stock is committed", target_fixture="item")
def _(item, commit_stock):
    return item.process(commit_stock)
