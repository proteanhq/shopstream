"""Checkpoints after an event-store restore - `protean recover --verify-checkpoints`.

WHAT THIS CHECKS
    A checkpoint is the stored position up to which an event-store subscription
    has processed a stream category. Positions are `global_position` values, the
    store-wide sequence number Message DB gives every message. A checkpoint is a
    stream named `position-{handler fqn}-{category}` whose newest message holds
    `{"position": <global_position>}`. The head of a category is the
    `global_position` of its newest message.

    A restore from a backup can leave a checkpoint past the restored head. That
    subscription would then skip every event written between the head and its
    stale checkpoint. `protean recover --verify-checkpoints` reports it, and
    `--reset-beyond-head` moves the checkpoint back to the head.

    Every ShopStream handler reads Redis streams (`default_subscription_type =
    "stream"`), so `recover` checks nothing in ShopStream as configured. This
    oracle moves two inventory projectors to event-store subscriptions through
    the test-time domain config only (`server.subscriptions.<HandlerClassName>`,
    the key Protean's `ConfigResolver` reads):

      * `InventoryLevelProjector` gets a checkpoint at g5, the newest of five
        events. The simulated restore then rolls the store back to g3.
      * `InventoryValuationProjector` gets no checkpoint, so it stands for a
        fresh subscription (position `-1`), which must read as consistent.

    The oracle runs the command three times and checks it against the positions
    it read from the store itself:

      1. `--verify-checkpoints --json` exits 1 with `status: fail`, and reports
         checkpoint g5, head g3 and `beyond_head` for the level projector.
      2. adding `--reset-beyond-head` exits 0 and resets exactly that checkpoint
         from g5 to g3.
      3. a plain run again exits 0 with every row consistent.

    The other inventory handlers stay on Redis streams and must not appear.

HOW THE RESTORE IS SIMULATED
    A point-in-time restore removes the newer rows and also rolls back Message
    DB's `global_position` sequence, so new events reuse positions at or below
    the stale checkpoint. As the `postgres` user, the oracle deletes every row
    past g3 and sets the sequence back to g3. Deleting only the item's rows is
    not enough: each `ReceiveStock` command sits in its own command stream
    between two events, and once the sequence is back at g3 the next write
    would collide with a surviving command row. The oracle then writes the
    checkpoint at g5, as if the checkpoint stream came from a later backup than
    the item stream. That is the stale state the command has to find.

STATUS
    Guard. The pinned Protean reports, resets and re-verifies as expected.

WHY POSTGRES + MESSAGE-DB ONLY
    The memory event store has no `global_position` sequence to roll back and no
    SQL table to delete from. Skipped under `--protean-env memory`.

SHARED STORE
    No context has a `[test.event_store]` overlay, so the test env and the dev
    env share one `message_store` database. The test resets it at the start and
    in a `finally`, which also wipes dev events, as the other Message DB oracles
    do. Stop any dev engine first: one writing to the same category would move
    the head.

RUN:
    make docker-up && make setup-db      # once
    .venv/bin/python -m pytest \
        verification/oracles/test_restore_checkpoints.py --protean-env test -q
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from urllib.parse import parse_qsl, urlparse

import pytest

ENV = os.environ.get("PROTEAN_ENV")
pytestmark = pytest.mark.skipif(
    ENV != "test",
    reason="restore oracle needs a real Message DB to roll back; run with --protean-env test",
)

CATEGORY = "inventory::inventory_item"
RESTORED = "InventoryLevelProjector"
FRESH = "InventoryValuationProjector"
RECEIPTS = 4


def _reset_stores(domain):
    """Empty the event store and the relational stores; truncation also restarts the sequence."""
    domain.event_store.store._data_reset()
    for _, provider in domain.providers.items():
        provider._data_reset()


@contextmanager
def _admin_cursor(domain):
    """A cursor on the Message DB as `postgres`, the convention Protean's own truncate uses."""
    import psycopg2

    parsed = urlparse(domain.event_store.store.conn_info["database_uri"])
    conn = psycopg2.connect(
        dbname=parsed.path[1:],
        user="postgres",
        port=parsed.port,
        host=parsed.hostname,
        sslmode=dict(parse_qsl(parsed.query)).get("sslmode", "disable"),
    )
    try:
        with conn.cursor() as cursor:
            yield cursor
        conn.commit()
    finally:
        conn.close()


def _write_checkpoint(domain, handler_cls, position):
    """Write a checkpoint in the record shape `EventStoreSubscription.write_position` uses."""
    from uuid import uuid4

    from protean.utils import fqn
    from protean.utils.eventing import MessageType

    stream = f"position-{fqn(handler_cls)}-{CATEGORY}"
    domain.event_store.store._write(
        stream,
        "Read",
        {"position": position},
        metadata={
            "headers": {
                "id": str(uuid4()),
                "type": "Read",
                "time": domain.clock.now().isoformat(),
                "stream": stream,
            },
            "domain": {
                "kind": MessageType.READ_POSITION.value,
                "origin_stream": CATEGORY,
            },
        },
    )


def _simulate_restore(domain, restored_head):
    """Roll the whole store back to `restored_head`: drop every newer row and reset the sequence."""
    with _admin_cursor(domain) as cursor:
        cursor.execute("DELETE FROM message_store.messages WHERE global_position > %s", (restored_head,))
        assert cursor.rowcount > 0, f"nothing past {restored_head} to roll back"
        # With is_called left true, the next message gets restored_head + 1.
        cursor.execute(
            "SELECT setval(pg_get_serial_sequence('message_store.messages', 'global_position'), %s)",
            (restored_head,),
        )


def _recover(domain, *flags):
    """Run `protean recover --verify-checkpoints --json` in-process against *domain*."""
    from unittest.mock import patch

    from protean.cli import app
    from typer.testing import CliRunner

    # `load_domain` resolves `derive_domain` from `protean.cli._helpers`, so the
    # configured domain is returned in place of a fresh import of the module path.
    with patch("protean.cli._helpers.derive_domain", return_value=domain):
        result = CliRunner().invoke(
            app,
            ["recover", "--verify-checkpoints", "--json", "--domain", "inventory.domain", *flags],
        )
    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"no JSON envelope on stdout (exit {result.exit_code}):\n{result.output}")
    return result.exit_code, envelope


def _rows_by_handler(envelope):
    rows = envelope["data"]["subscriptions"]
    assert len(rows) > 0, "Expected event-store subscriptions but got none"
    by_handler = {row["handler_name"]: row for row in rows}
    assert len(by_handler) == len(rows), f"a handler appears twice: {rows}"
    return by_handler


@pytest.fixture()
def restore_domain(inventory_bed, monkeypatch):
    """The inventory domain with two projectors on event-store subscriptions, stores reset around the test."""
    domain = inventory_bed.domain
    subscriptions = domain.config["server"]["subscriptions"]
    for handler in (RESTORED, FRESH):
        monkeypatch.setitem(subscriptions, handler, {"subscription_type": "event_store"})

    with inventory_bed.domain_context():
        _reset_stores(domain)
        try:
            yield domain
        finally:
            _reset_stores(domain)


def test_recover_finds_and_resets_a_checkpoint_past_the_restored_head(restore_domain):
    from inventory.projections.inventory_level import InventoryLevelProjector
    from inventory.stock.receiving import ReceiveStock
    from verification.oracles.test_crash_window_reconcile import _seed_item

    domain = restore_domain
    item_id = _seed_item(domain, on_hand=0)
    for n in range(RECEIPTS):
        domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=5, reference=f"GRN-{n}"),
            asynchronous=False,
        )

    item_stream = f"{CATEGORY}-{item_id}"
    positions = [m.metadata.event_store.global_position for m in domain.event_store.store.read(item_stream)]
    assert len(positions) == 1 + RECEIPTS, f"expected five events in {item_stream}, got {positions}"
    assert positions == sorted(set(positions)), f"global positions do not increase: {positions}"
    g3, g5 = positions[2], positions[4]

    _simulate_restore(domain, g3)
    restored = [m.metadata.event_store.global_position for m in domain.event_store.store.read(item_stream)]
    assert restored == positions[:3], f"the restore should keep g1 to g3: {restored}"
    # The checkpoint stream comes from a later backup than the item stream, so
    # it names g5, which the restored store no longer holds.
    _write_checkpoint(domain, InventoryLevelProjector, g5)

    # 1. Detection: the checkpoint names g5, the restored head is g3.
    code, envelope = _recover(domain)
    assert (code, envelope["status"]) == (1, "fail"), envelope
    rows = _rows_by_handler(envelope)
    assert set(rows) == {RESTORED, FRESH}, f"only the two re-configured projectors use the event store: {set(rows)}"
    assert rows[RESTORED]["checkpoint_position"] == str(g5)
    assert rows[RESTORED]["head_position"] == str(g3)
    assert rows[RESTORED]["verdict"] == "beyond_head"
    assert rows[FRESH]["checkpoint_position"] == "-1"
    assert rows[FRESH]["verdict"] == "consistent"
    assert envelope["data"]["summary"]["beyond_head"] == 1
    assert "recovery" not in envelope["data"], envelope["data"].get("recovery")

    # 2. Reset: only the stale checkpoint moves, and it moves back to the head.
    code, envelope = _recover(domain, "--reset-beyond-head")
    assert (code, envelope["status"]) == (0, "pass"), envelope
    resets = envelope["data"]["reset"]
    assert len(resets) == 1, resets
    assert resets[0]["handler_name"] == RESTORED
    assert resets[0]["previous_position"] == str(g5)
    assert resets[0]["new_position"] == str(g3)
    assert envelope["data"]["reset_failures"] == []

    # 3. Re-verify: nothing is beyond head any more.
    code, envelope = _recover(domain)
    assert (code, envelope["status"]) == (0, "pass"), envelope
    rows = _rows_by_handler(envelope)
    assert {row["verdict"] for row in rows.values()} == {"consistent"}
    assert rows[RESTORED]["checkpoint_position"] == str(g3)
    assert envelope["data"]["summary"]["beyond_head"] == 0
