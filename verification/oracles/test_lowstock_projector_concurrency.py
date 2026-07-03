"""LowStockReport projector must survive concurrent LowStockDetected events.

WHAT THIS CHECKS
    `LowStockReport` is keyed by `inventory_item_id`. Every stock movement that
    leaves an item at or below its reorder point raises `LowStockDetected`, and the
    projector upserts the single report row (get → update, else create). Under
    concurrency two commands can both find "no report yet" and both take the CREATE
    path — the second collides ("... is already present."). Because the projector
    runs inline in the command's UnitOfWork (sync event processing), that collision
    aborts an otherwise-valid command.

    Property: N concurrent `LowStockDetected` for the same fresh item must leave
    exactly ONE report row, with no delivery failing because of the race.

    This was first surfaced by the P2 concurrency oracle (`test_no_lost_updates`),
    which now suppresses `LowStockDetected` to isolate the reservation signal; this
    oracle owns the projector-concurrency property.

HOW THE RACE IS MADE DETERMINISTIC
    A reserve-driven reproduction is timing-dependent (optimistic concurrency on
    the aggregate serialises the commits, so the create window rarely opens). Here
    every worker drives the projector for the SAME item at a shared barrier, so
    they all take the create path together. A version-retry loop in the worker
    mimics the framework's handler wrapper, so update-update races are retried the
    way production would — leaving the create-create collision as the thing tested.

WHY REAL POSTGRES, MULTI-PROCESS
    The create-create race only exists across real, isolated transactions. Skipped
    under `--protean-env memory`.

RUN:
    make docker-up && make setup-db
    .venv/bin/python -m pytest \
        verification/oracles/test_lowstock_projector_concurrency.py --protean-env test -q
"""

from __future__ import annotations

import multiprocessing as mp
import os
import uuid
from collections import Counter
from datetime import UTC, datetime

import pytest

from verification.oracles._concurrency_worker import project_low_stock_once

ENV = os.environ.get("PROTEAN_ENV")
pytestmark = pytest.mark.skipif(
    ENV != "test",
    reason="projector create-create race needs real isolated transactions; run with --protean-env test",
)

WORKERS = 12
AVAILABLE = 3  # the low-stock level every worker reports for the shared item


@pytest.fixture(scope="module")
def inventory_domain():
    from inventory.domain import inventory

    inventory.init()
    with inventory.domain_context():
        inventory.setup_database()
    yield inventory


def test_concurrent_low_stock_detected_yields_one_report(inventory_domain):
    from protean import current_domain

    from inventory.projections.low_stock_report import LowStockReport

    item_id = str(uuid.uuid4())
    detected_at = datetime.now(UTC).isoformat()

    ctx = mp.get_context("spawn")
    with ctx.Manager() as manager:
        barrier = manager.Barrier(WORKERS, timeout=90)
        args = [
            (ENV, item_id, str(uuid.uuid4()), str(uuid.uuid4()), "SKU-LS", AVAILABLE, detected_at, barrier)
            for _ in range(WORKERS)
        ]
        with ctx.Pool(WORKERS) as pool:
            tally = Counter(pool.map(project_low_stock_once, args))

    # Every delivery must succeed: no create-create collision may leak out.
    assert set(tally) == {"ok"}, f"projector failed under concurrency: {dict(tally)}"

    # Exactly one report row, reflecting the reported level.
    with inventory_domain.domain_context():
        report = current_domain.repository_for(LowStockReport).get(item_id)
        assert report.current_available == AVAILABLE
        assert report.is_critical == (AVAILABLE == 0)
