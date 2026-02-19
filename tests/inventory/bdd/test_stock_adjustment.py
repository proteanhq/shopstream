"""BDD tests for stock adjustment."""

from inventory.stock.adjustment import AdjustStock
from inventory.stock.stock import AdjustmentType
from pytest_bdd import parsers, scenarios, when

scenarios("features/stock_adjustment.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("stock is adjusted down", target_fixture="item")
def _(item, adjust_stock_down):
    return item.process(adjust_stock_down)


@when("stock is adjusted up", target_fixture="item")
def _(item, adjust_stock_up):
    return item.process(adjust_stock_up)


@when("stock is adjusted by -200", target_fixture="item")
def _(item, inventory_item_id):
    cmd = AdjustStock(
        inventory_item_id=inventory_item_id,
        quantity_change=-200,
        adjustment_type=AdjustmentType.CORRECTION.value,
        reason="Bad correction",
        adjusted_by="manager-001",
    )
    return item.process(cmd)


@when(parsers.cfparse("a stock check records {qty:d} units"), target_fixture="item")
def _(item, record_stock_check):
    return item.process(record_stock_check)
