"""BDD tests for stock receiving."""

from inventory.stock.receiving import ReceiveStock
from pytest_bdd import scenarios, when

scenarios("features/stock_receiving.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("stock is received", target_fixture="item")
def _(item, receive_stock):
    return item.process(receive_stock)


@when("zero stock is received", target_fixture="item")
def _(item, inventory_item_id):
    cmd = ReceiveStock(inventory_item_id=inventory_item_id, quantity=0)
    return item.process(cmd)
