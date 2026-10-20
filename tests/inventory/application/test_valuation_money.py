"""Inventory money projections keep amounts as 4-place Decimals."""

from decimal import Decimal

import pytest
from protean import current_domain
from protean.utils.reflection import fields

from inventory.projections.inventory_valuation import InventoryValuation
from inventory.projections.shrinkage_report import ShrinkageReport
from inventory.stock.initialization import InitializeStock
from inventory.stock.receiving import ReceiveStock


@pytest.mark.parametrize(
    ("projection", "field_name"),
    [
        (InventoryValuation, "unit_cost"),
        (InventoryValuation, "total_value"),
        (ShrinkageReport, "total_shrinkage_value"),
    ],
)
def test_money_fields_are_numeric_19_4(projection, field_name):
    field = fields(projection)[field_name]
    assert (field.precision, field.scale) == (19, 4)


def test_valuation_multiplies_on_hand_by_unit_cost_exactly():
    item_id = current_domain.process(
        InitializeStock(
            product_id="prod-val-001",
            variant_id="var-val-001",
            warehouse_id="wh-val-001",
            sku="SKU-VAL-001",
            initial_quantity=1,
        ),
        asynchronous=False,
    )
    # No inventory event carries a unit cost, so it is set on the view.
    repo = current_domain.repository_for(InventoryValuation)
    view = repo.get(item_id)
    view.unit_cost = Decimal("0.1")
    repo.add(view)

    current_domain.process(ReceiveStock(inventory_item_id=item_id, quantity=2), asynchronous=False)

    view = repo.get(item_id)
    assert view.on_hand == 3
    # As floats, 3 * 0.1 is 0.30000000000000004.
    assert view.total_value == Decimal("0.3000")
