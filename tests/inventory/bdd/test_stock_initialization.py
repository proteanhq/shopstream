"""BDD tests for stock initialization."""

from inventory.stock.stock import InventoryItem
from protean.testing import given as given_
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/stock_initialization.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("stock is initialized", target_fixture="item")
def _(initialize_stock):
    return given_(InventoryItem).process(initialize_stock)


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the SKU is "{sku}"'))
def _(item, sku):
    assert item.sku == sku


@then(parsers.cfparse("the reorder point is {qty:d}"))
def _(item, qty):
    assert item.reorder_point == qty


@then(parsers.cfparse("the reorder quantity is {qty:d}"))
def _(item, qty):
    assert item.reorder_quantity == qty
