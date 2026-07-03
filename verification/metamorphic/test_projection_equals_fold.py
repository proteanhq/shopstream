"""P9 - a projection equals the fold of its aggregate's events.

WHAT THIS CHECKS
    A read model (projection) is built by projectors folding an aggregate's event
    stream. The aggregate itself is ALSO a fold of that same stream (its @apply
    handlers). After the pipeline settles, the two folds must agree: the read
    model must reflect the same state the aggregate replayed to.

    Property P9: projection == fold(events).

    Here the independent "fold of events" is the event-sourced aggregate's own
    replayed state (reconstructed by repository.get). The projector is a SECOND,
    separately-written fold of the same stream. If a projector mishandles an
    event - applies the wrong delta, misses a field, reacts to the wrong event -
    it diverges from the aggregate and this check catches it.

WHY THIS IS WEAKER THAN THE P20 ORACLE (read this before trusting a green run)
    This is a metamorphic check (source B). It compares two folds of the SAME
    event stream, so it only catches bugs where the two folds DISAGREE. A bug
    both folds share - e.g. a duplicate event in the stream that both the
    aggregate and the projector apply - is invisible here: both sides see the
    duplicate and still "agree". That blind spot is exactly why
    verification/oracles/test_p20_projector_idempotency.py exists: it hand-
    computes the expected count independently of the stream, so it catches the
    duplicate this check cannot. Keep P9 as a cheap convergence net, not a
    correctness oracle.

COVERAGE
    Parameterized over a registry of (aggregate build, projection, field map)
    cases. Seeded with InventoryLevel, whose fields mirror the InventoryItem
    aggregate's StockLevels VO one-for-one - the cleanest fold to compare.
    Add a case per projection whose fields map back onto its aggregate's state.

RUN (no Docker):
    .venv/bin/python -m pytest \
        verification/metamorphic/test_projection_equals_fold.py --protean-env memory -q
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from protean import current_domain


@dataclass(frozen=True)
class FoldCase:
    """One (aggregate stream, projection) pair to compare two folds of.

    `build` drives the aggregate through several events and persists it; in a
    sync domain the projectors fire inline during that persist, so the read model
    is populated by the time it returns. It returns the aggregate id. `agg_view`
    and `proj_view` extract the SAME logical fields from the replayed aggregate
    and from the projection row respectively - they must be equal.
    """

    id: str
    bed_fixture: str
    build: Callable[[], Any]  # -> aggregate id
    aggregate: Callable[[], type]  # deferred import of the aggregate class
    projection: Callable[[], type]  # deferred import of the projection class
    agg_view: Callable[[Any], dict]
    proj_view: Callable[[Any], dict]


# --- inventory: InventoryLevel mirrors the StockLevels VO one-for-one ---------


def _build_inventory_item() -> Any:
    from inventory.stock.stock import InventoryItem

    item = InventoryItem.create(
        product_id="prod-p9",
        variant_id="var-p9",
        warehouse_id="wh-p9",
        sku="SKU-P9",
        initial_quantity=20,
    )
    item.receive_stock(quantity=10)  # on_hand 30
    item.reserve(order_id="order-p9a", quantity=5)  # reserved 5
    item.reserve(order_id="order-p9b", quantity=3)  # reserved 8
    item.mark_damaged(quantity=2, reason="dented in transit")  # damaged 2

    current_domain.repository_for(InventoryItem).add(item)  # projectors fire (sync)
    return item.id


def _inventory_agg_view(item) -> dict:
    lv = item.levels
    return {
        "on_hand": lv.on_hand,
        "reserved": lv.reserved,
        "available": lv.available,
        "in_transit": lv.in_transit,
        "damaged": lv.damaged,
        "reorder_point": item.reorder_point,
    }


def _inventory_proj_view(row) -> dict:
    return {
        "on_hand": row.on_hand,
        "reserved": row.reserved,
        "available": row.available,
        "in_transit": row.in_transit,
        "damaged": row.damaged,
        "reorder_point": row.reorder_point,
    }


FOLD_CASES = [
    FoldCase(
        id="inventory_level",
        bed_fixture="inventory_bed",
        build=_build_inventory_item,
        aggregate=lambda: __import__("inventory.stock.stock", fromlist=["InventoryItem"]).InventoryItem,
        projection=lambda: (
            __import__("inventory.projections.inventory_level", fromlist=["InventoryLevel"]).InventoryLevel
        ),
        agg_view=_inventory_agg_view,
        proj_view=_inventory_proj_view,
    ),
]


@pytest.fixture()
def fold_ctx(request):
    case: FoldCase = request.param
    bed = request.getfixturevalue(case.bed_fixture)
    with bed.domain_context():
        yield case


@pytest.mark.parametrize("fold_ctx", FOLD_CASES, ids=[c.id for c in FOLD_CASES], indirect=True)
def test_projection_equals_fold(fold_ctx):
    case = fold_ctx

    aggregate_id = case.build()

    aggregate = current_domain.repository_for(case.aggregate()).get(aggregate_id)
    row = current_domain.repository_for(case.projection()).get(aggregate_id)

    # Both are folds of the same event stream; they must agree field-for-field.
    assert case.proj_view(row) == case.agg_view(aggregate)
