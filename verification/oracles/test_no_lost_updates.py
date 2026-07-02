"""P2 - no lost updates under concurrent writes (the crown-jewel safety property).

WHAT THIS CHECKS
    Fire many concurrent `ReserveStock` commands at ONE inventory aggregate that
    only has N units on hand. `InventoryItem.reserve()` refuses to reserve more
    than is available, so the invariant is hard and independent of the event
    stream:

        you can never reserve more units than exist — no matter how many
        writers race.

    A lost update (two writers both read "1 available", both commit a reserve,
    one silently clobbers the other's version) would show up as OVER-reservation:
    more successes than units, or `available` going negative. Protean prevents
    this with optimistic concurrency — each write asserts the aggregate's
    expected version, and a stale write is rejected with `ExpectedVersionError`.

WHY THIS IS A TYPE-A ORACLE (see VERIFICATION_STRATEGY.md section 2)
    The expected answer (`successes <= N`, `reserved == successes`,
    `available == N - successes`) is computed by hand, independently of anything
    Protean records. It does not fold the event stream and compare it to a
    projection (that would share any versioning bug on both sides). If Protean's
    OCC were broken, THIS check fails; a convergence check would not.

    The falsification test proves the oracle has teeth: with version-retry turned
    OFF, real `ExpectedVersionError`s surface (contention is genuine and OCC is
    doing its job); safety still holds — Protean never corrupts, it only rejects.

WHY REAL POSTGRES + MESSAGE-DB, MULTI-PROCESS
    Optimistic concurrency is only meaningful against a real store that arbitrates
    concurrent writes. In-memory adapters fake transactions, so this check is
    skipped unless run with `--protean-env test`. Workers are separate OS
    processes (not threads) so the database is the only synchronization point.

RUN:
    make docker-up && make setup-db      # once
    .venv/bin/python -m pytest \
        verification/oracles/test_no_lost_updates.py --protean-env test -q
"""

from __future__ import annotations

import multiprocessing as mp
import os
import uuid
from collections import Counter

import pytest

from verification.oracles._concurrency_worker import reserve_once

# Optimistic concurrency needs a real store; in-memory adapters fake it. Only run
# against the dedicated test database (separate from dev data).
ENV = os.environ.get("PROTEAN_ENV")
pytestmark = pytest.mark.skipif(
    ENV != "test",
    reason="P2 concurrency oracle needs real Postgres + Message-DB; run with --protean-env test",
)

ON_HAND = 8  # units seeded on the aggregate
WORKERS = 16  # concurrent writers (> ON_HAND, so contention is guaranteed)

# Generous, fast OCC retries make LIVENESS deterministic: every unit sells rather
# than a loser exhausting the shipped default (max_retries=3) under heavy CI
# contention and surfacing as a version conflict before stock runs out. Safety
# holds regardless of this value.
LIVENESS_RETRY = {
    "enabled": True,
    "max_retries": 40,
    "base_delay_seconds": 0.005,
    "max_delay_seconds": 0.05,
}
RETRY_DISABLED = {"enabled": False}


@pytest.fixture(scope="module")
def inventory_domain():
    from inventory.domain import inventory

    inventory.init()
    with inventory.domain_context():
        inventory.setup_database()
    yield inventory


def _seed_item(inventory, on_hand: int) -> str:
    """Create a fresh InventoryItem with `on_hand` units; return its id."""
    from inventory.stock.stock import InventoryItem

    with inventory.domain_context():
        item = InventoryItem.create(
            product_id=str(uuid.uuid4()),
            variant_id=str(uuid.uuid4()),
            warehouse_id=str(uuid.uuid4()),
            sku=f"SKU-{uuid.uuid4().hex[:8]}",
            initial_quantity=on_hand,
        )
        inventory.repository_for(InventoryItem).add(item)
        return str(item.id)


def _levels(inventory, item_id: str):
    from inventory.stock.stock import InventoryItem

    with inventory.domain_context():
        item = inventory.repository_for(InventoryItem).get(item_id)
        return item.levels, len(list(item.reservations))


def _run_concurrent_reservations(item_id: str, *, retry_config: dict) -> Counter:
    """Spawn WORKERS processes, each firing one reservation at the same aggregate."""
    ctx = mp.get_context("spawn")
    with ctx.Manager() as manager:
        barrier = manager.Barrier(WORKERS, timeout=90)
        args = [(ENV, item_id, str(uuid.uuid4()), barrier, retry_config) for _ in range(WORKERS)]
        with ctx.Pool(WORKERS) as pool:
            outcomes = pool.map(reserve_once, args)
    return Counter(outcomes)


def _assert_safety(tally: Counter, levels, reservation_count: int):
    """The invariant that must hold in EVERY configuration (the release gate)."""
    successes = tally.get("ok", 0)
    unexpected = {k: v for k, v in tally.items() if k not in ("ok", "conflict", "insufficient")}
    assert not unexpected, f"unexpected worker outcomes: {unexpected}"

    # No over-reservation: the lost-update bug this oracle exists to catch.
    assert successes <= ON_HAND, f"OVER-RESERVED: {successes} successes > {ON_HAND} on hand"
    assert levels.available >= 0, f"available went negative: {levels.available}"
    # The read model exactly reflects the successful writes — nothing lost, nothing double-counted.
    assert levels.reserved == successes, f"reserved {levels.reserved} != successes {successes}"
    assert levels.available == ON_HAND - successes
    assert reservation_count == successes, f"{reservation_count} reservations != {successes} successes"
    return successes


def test_concurrent_reservations_never_over_reserve(inventory_domain):
    """Safety + liveness: with OCC retry on, all N units sell and none are over-sold."""
    item_id = _seed_item(inventory_domain, ON_HAND)

    tally = _run_concurrent_reservations(item_id, retry_config=LIVENESS_RETRY)

    levels, reservation_count = _levels(inventory_domain, item_id)
    successes = _assert_safety(tally, levels, reservation_count)

    # Liveness: with generous retries every race is resolved, so every unit sells
    # (the surplus writers fail with "insufficient stock", not a dropped write).
    # We assert the total sold, not the split between conflict/insufficient — how a
    # loser fails depends on retry budget vs. contention and isn't deterministic.
    assert successes == ON_HAND, f"expected all {ON_HAND} units reserved, got {successes} ({dict(tally)})"


def test_version_retry_is_load_bearing(inventory_domain):
    """Falsification: turn OCC retry off → real conflicts surface, safety still holds.

    This proves the oracle isn't vacuous. Without the retry, stale writers lose
    the version race and raise `ExpectedVersionError` instead of being retried —
    so fewer units sell — but Protean still never corrupts state.
    """
    item_id = _seed_item(inventory_domain, ON_HAND)

    tally = _run_concurrent_reservations(item_id, retry_config=RETRY_DISABLED)

    levels, reservation_count = _levels(inventory_domain, item_id)
    successes = _assert_safety(tally, levels, reservation_count)

    # Contention is real and OCC is enforced: at least one writer lost the race.
    assert tally.get("conflict", 0) >= 1, f"expected version conflicts without retry, got {dict(tally)}"
    # And because conflicts aren't retried, not all inventory sells.
    assert successes < ON_HAND, f"expected < {ON_HAND} successes without retry, got {successes}"
