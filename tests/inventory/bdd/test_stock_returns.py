"""BDD tests for stock returns."""

from inventory.stock.returns import ReturnToStock
from pytest_bdd import scenarios, when

scenarios("features/stock_returns.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("items are returned to stock", target_fixture="item")
def _(item, return_to_stock):
    return item.process(return_to_stock)


@when("zero items are returned", target_fixture="item")
def _(item, inventory_item_id):
    cmd = ReturnToStock(
        inventory_item_id=inventory_item_id,
        quantity=0,
        order_id="ord-ret-001",
    )
    return item.process(cmd)
