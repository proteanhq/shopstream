"""Checkpoints after an event-store restore - `protean recover --verify-checkpoints`.

WHAT THIS CHECKS
    A checkpoint is the stored position up to which an event-store subscription
    has processed a stream category. Positions are `global_position` values, the
    store-wide sequence number Message DB gives every message. A checkpoint is a
    stream named `position-{handler fqn}-{category}` whose newest message holds
    `{"position": <global_position>}`. The head of a category is the
    `global_position` of its newest message.

    A restore can leave a checkpoint past the restored head when the backup is
    inconsistent: the checkpoint streams were saved later than the event
    streams, or an engine left running wrote its position back after the
    restore. That subscription would then skip every new event whose position
    lands between the head and its stale checkpoint. The same restore can leave
    recovery-tracking entries (failed positions the subscription retries) that
    name a message the restore removed. `protean recover --verify-checkpoints`
    reports both, and `--reset-beyond-head` moves the checkpoint back to the
    head and clears the stale entries.

    Every ShopStream handler reads Redis streams (`default_subscription_type =
    "stream"`), so `recover` checks nothing in ShopStream as configured.
    `test_no_context_uses_event_store_subscriptions` guards that for all nine
    contexts, in every env. The restore test moves three inventory projectors
    to event-store subscriptions through the test-time domain config only
    (`server.subscriptions.<HandlerClassName>`, the key Protean's
    `ConfigResolver` reads):

      * `InventoryLevelProjector` gets a checkpoint at g5, the newest of five
        events, after the simulated restore rolled the store back to g3. Its
        recovery tracking names g5 (gone) and g2 (still there).
      * `StockMovementLogProjector` gets a checkpoint at g2, below the head,
        which must stay where it is.
      * `InventoryValuationProjector` gets no checkpoint, so it stands for a
        fresh subscription (position `-1`), which must read as consistent.

    The oracle runs the command three times and checks it against the positions
    it read from the store itself:

      1. `--verify-checkpoints --json` exits 1 with `status: fail`. It reports
         checkpoint g5, head g3 and `beyond_head` for the level projector, the
         other two as consistent, and g5 as a stale recovery-tracking entry.
      2. adding `--reset-beyond-head` exits 0. It resets exactly that checkpoint
         from g5 to g3 and clears exactly g5 from the recovery tracking. The
         oracle reads the stored records back: the checkpoint holds the int g3,
         the g2 checkpoint is unchanged, and the tracking still holds g2.
      3. a run without the reset again exits 0 with every row consistent and no
         recovery-tracking finding.

    The other inventory handlers stay on Redis streams and must not appear.

HOW THE RESTORE IS SIMULATED
    A restore puts back the rows up to some position and rolls back Message
    DB's `global_position` sequence with them, so new messages reuse positions
    at or below the stale checkpoint. As the `postgres` user, the oracle deletes
    every row past g3 and sets the sequence back to g3. It checks the rollback:
    the first record written afterwards must get g3 + 1. Deleting only the
    item's rows is not enough: each `ReceiveStock` command sits in its own
    command stream between two events, and once the sequence is back at g3 the
    next write would collide with a surviving command row. The oracle then
    writes the checkpoint at g5 and the recovery tracking, as if their streams
    came from a later backup than the item stream. That is the stale state the
    command has to find.

STATUS
    Guard. The pinned Protean reports, resets and re-verifies as expected.

WHY POSTGRES + MESSAGE-DB ONLY
    The memory event store has no `global_position` sequence to roll back and no
    SQL table to delete from. The restore test is skipped in every env except
    `test`; the nine-context check runs everywhere.

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
real_stores = pytest.mark.skipif(
    ENV != "test",
    reason="restore oracle needs a real Message DB to roll back; run with --protean-env test",
)

CONTEXTS = (
    "identity",
    "catalogue",
    "ordering",
    "inventory",
    "payments",
    "fulfillment",
    "reviews",
    "notifications",
    "loyalty",
)
CATEGORY = "inventory::inventory_item"
RESTORED = "InventoryLevelProjector"
BEHIND = "StockMovementLogProjector"
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


def _position_stream(handler_cls):
    from protean.utils import fqn

    return f"position-{fqn(handler_cls)}-{CATEGORY}"


def _recovery_stream(handler_cls):
    from protean.utils import fqn
    from protean.utils.dlq import recovery_checkpoint_stream

    return recovery_checkpoint_stream(fqn(handler_cls), CATEGORY)


def _write_checkpoint(domain, handler_cls, position):
    """Write a checkpoint and return the `global_position` the store gave the record.

    Protean has no public function that writes a read position outside a running
    subscription, so this copies the record `EventStoreSubscription.write_position`
    writes, through the store's private `_write`.
    """
    from uuid import uuid4

    from protean.utils.eventing import MessageType

    store = domain.event_store.store
    stream = _position_stream(handler_cls)
    store._write(
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
    return store._read_last_message(stream)["global_position"]


def _write_recovery_tracking(domain, handler_cls, entries):
    """Record failed positions the subscription's recovery pass would retry.

    *entries* maps a `global_position` to the stream name and stream position
    of its event, the fields a `Failed` record carries.
    """
    from protean.server.subscription.event_store_subscription import write_recovery_checkpoint_record

    write_recovery_checkpoint_record(
        domain.event_store.store,
        _recovery_stream(handler_cls),
        CATEGORY,
        domain.clock.now().isoformat(),
        0,
        {
            pos: {"retry_count": 1, "stream_name": name, "stream_position": stream_pos}
            for pos, (name, stream_pos) in entries.items()
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
    # `load_domain` then calls `init()` again on the session-scoped inventory bed.
    # That is safe at the pinned Protean; suspect it first if a later inventory
    # oracle in the same session misbehaves.
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


@pytest.mark.parametrize("context", CONTEXTS)
def test_no_context_uses_event_store_subscriptions(context, request):
    """As configured, `recover` has nothing to check in any context, as the runbook says."""
    from protean.server.subscription_status import collect_subscription_statuses

    bed = request.getfixturevalue(f"{context}_bed")
    with bed.domain_context():
        statuses = collect_subscription_statuses(bed.domain)
    assert len(statuses) > 0, f"{context} reported no subscriptions at all"
    # `recover` keeps exactly these and reports their count as `summary.checked`.
    event_store = [s.handler_name for s in statuses if s.subscription_type == "event_store"]
    assert event_store == [], f"{context} handlers on event-store subscriptions: {event_store}"


@pytest.fixture()
def restore_domain(inventory_bed, monkeypatch):
    """The inventory domain with three projectors on event-store subscriptions, stores reset around the test."""
    domain = inventory_bed.domain
    subscriptions = domain.config["server"]["subscriptions"]
    for handler in (RESTORED, BEHIND, FRESH):
        monkeypatch.setitem(subscriptions, handler, {"subscription_type": "event_store"})

    with inventory_bed.domain_context():
        _reset_stores(domain)
        try:
            yield domain
        finally:
            _reset_stores(domain)


@real_stores
def test_recover_finds_and_resets_a_checkpoint_past_the_restored_head(restore_domain):
    from inventory.projections.inventory_level import InventoryLevelProjector
    from inventory.projections.stock_movement_log import StockMovementLogProjector
    from inventory.stock.receiving import ReceiveStock
    from verification.oracles.test_crash_window_reconcile import _seed_item

    domain = restore_domain
    store = domain.event_store.store
    item_id = _seed_item(domain, on_hand=0)
    for n in range(RECEIPTS):
        domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=5, reference=f"GRN-{n}"),
            asynchronous=False,
        )

    item_stream = f"{CATEGORY}-{item_id}"
    positions = [m.metadata.event_store.global_position for m in store.read(item_stream)]
    assert len(positions) == 1 + RECEIPTS, f"expected five events in {item_stream}, got {positions}"
    assert positions == sorted(set(positions)), f"global positions do not increase: {positions}"
    g2, g3, g5 = positions[1], positions[2], positions[4]

    _simulate_restore(domain, g3)
    restored = [m.metadata.event_store.global_position for m in store.read(item_stream)]
    assert restored == positions[:3], f"the restore should keep g1 to g3: {restored}"
    # The checkpoint stream comes from a later backup than the item stream, so
    # it names g5, which the restored store no longer holds. The restore rolled
    # the sequence back too, so this record reuses the first position past g3.
    stale_record_position = _write_checkpoint(domain, InventoryLevelProjector, g5)
    assert stale_record_position == g3 + 1, "the restore did not roll the global_position sequence back"
    # A checkpoint behind the head must be left where it is.
    _write_checkpoint(domain, StockMovementLogProjector, g2)
    # Recovery tracking from the same later backup: g5 (item stream position 4)
    # is gone, g2 (item stream position 1) survived the restore.
    _write_recovery_tracking(domain, InventoryLevelProjector, {g5: (item_stream, 4), g2: (item_stream, 1)})

    # 1. Detection: the checkpoint names g5, the restored head is g3.
    code, envelope = _recover(domain)
    assert (code, envelope["status"]) == (1, "fail"), envelope
    rows = _rows_by_handler(envelope)
    assert set(rows) == {RESTORED, BEHIND, FRESH}, (
        f"only the three re-configured projectors use the event store: {set(rows)}"
    )
    assert rows[RESTORED]["checkpoint_position"] == str(g5)
    assert rows[RESTORED]["head_position"] == str(g3)
    assert rows[RESTORED]["verdict"] == "beyond_head"
    assert rows[BEHIND]["checkpoint_position"] == str(g2)
    assert rows[BEHIND]["verdict"] == "consistent"
    assert rows[FRESH]["checkpoint_position"] == "-1"
    assert rows[FRESH]["verdict"] == "consistent"
    summary = envelope["data"]["summary"]
    assert (summary["beyond_head"], summary["unknown"]) == (1, 0), summary
    recovery = envelope["data"]["recovery"]
    assert [(r["handler_name"], r["verdict"], r["stale_positions"]) for r in recovery] == [(RESTORED, "stale", [g5])], (
        recovery
    )
    assert (summary["recovery_stale"], summary["recovery_unknown"]) == (1, 0), summary

    # 2. Reset: only the stale checkpoint moves, and it moves back to the head.
    code, envelope = _recover(domain, "--reset-beyond-head")
    assert (code, envelope["status"]) == (0, "pass"), envelope
    resets = envelope["data"]["reset"]
    assert len(resets) == 1, resets
    assert resets[0]["handler_name"] == RESTORED
    assert resets[0]["previous_position"] == str(g5)
    assert resets[0]["new_position"] == str(g3)
    assert envelope["data"]["reset_failures"] == []
    recovery_resets = envelope["data"]["recovery_reset"]
    assert [(r["handler_name"], r["cleared_positions"]) for r in recovery_resets] == [(RESTORED, [g5])]
    assert envelope["data"]["recovery_reset_failures"] == []
    # Read the stored records directly: the subscription does arithmetic on the
    # position, so it must be stored as an int, not the string `recover` prints.
    assert store._read_last_message(_position_stream(InventoryLevelProjector))["data"] == {"position": g3}
    assert store._read_last_message(_position_stream(StockMovementLogProjector))["data"] == {"position": g2}
    tracked = store._read_last_message(_recovery_stream(InventoryLevelProjector))["data"]["unresolved"]
    assert set(tracked) == {str(g2)}, tracked

    # 3. Re-verify: nothing is beyond head or stale any more.
    code, envelope = _recover(domain)
    assert (code, envelope["status"]) == (0, "pass"), envelope
    rows = _rows_by_handler(envelope)
    assert {row["verdict"] for row in rows.values()} == {"consistent"}
    assert rows[RESTORED]["checkpoint_position"] == str(g3)
    assert rows[BEHIND]["checkpoint_position"] == str(g2)
    assert envelope["data"]["summary"]["beyond_head"] == 0
    assert "recovery" not in envelope["data"], envelope["data"].get("recovery")
