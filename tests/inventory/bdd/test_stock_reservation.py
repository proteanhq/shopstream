"""BDD tests for stock reservation."""

from inventory.stock.reservation import ReserveStock
from pytest_bdd import scenarios, when

scenarios("features/stock_reservation.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("stock is reserved for an order", target_fixture="item")
def _(item, reserve_stock):
    return item.process(reserve_stock)


@when("200 units are reserved", target_fixture="item")
def _(item, inventory_item_id):
    cmd = ReserveStock(inventory_item_id=inventory_item_id, order_id="ord-big", quantity=200)
    return item.process(cmd)


@when("the reservation is released", target_fixture="item")
def _(item, release_reservation):
    return item.process(release_reservation)


@when("the reservation is confirmed", target_fixture="item")
def _(item, confirm_reservation):
    return item.process(confirm_reservation)
