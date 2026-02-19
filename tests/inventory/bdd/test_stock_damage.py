"""BDD tests for stock damage."""

from inventory.stock.damage import MarkDamaged
from pytest_bdd import scenarios, when

scenarios("features/stock_damage.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("stock is marked as damaged", target_fixture="item")
def _(item, mark_damaged):
    return item.process(mark_damaged)


@when("damaged stock is written off", target_fixture="item")
def _(item, write_off_damaged):
    return item.process(write_off_damaged)


@when("95 units are marked damaged", target_fixture="item")
def _(item, inventory_item_id):
    cmd = MarkDamaged(
        inventory_item_id=inventory_item_id,
        quantity=95,
        reason="Flood",
    )
    return item.process(cmd)
