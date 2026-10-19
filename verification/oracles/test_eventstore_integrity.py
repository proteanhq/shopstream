"""Event store integrity - `verify` passes on a real workload and catches corruption.

WHAT THIS CHECKS
    `BaseEventStore.verify()` (CLI: `protean eventstore verify`) reads the whole
    store once and reports six kinds of violation: a gap in a stream's
    positions, a snapshot whose `_version` runs past its aggregate stream, a
    malformed snapshot, a duplicate message id, a malformed message and a
    global_position that does not increase. Upstream tests the violation cases
    against its in-memory and list-backed test stores, and only the clean path
    against Message DB. This oracle checks the first three kinds on Message DB:

      * CLEAN - a fixed workload writes an event-sourced InventoryItem and an
        Order through their commands, and a PromoCampaign through its aggregate
        methods and repository. The InventoryItem passes Protean's default
        `snapshot_threshold` (10) and the PromoCampaign passes loyalty's (5), so
        each load past the threshold writes a snapshot inline, the path
        ShopStream's own code uses. The store must verify clean, and its message
        and stream counts must equal independent SQL counts, also when verify
        reads the store two rows per page.
      * FALSIFICATIONS - one hand-made corruption per test, written as the
        `postgres` user. Each must yield exactly one violation of the expected
        kind, stream and position:
          - delete position 1 of the InventoryItem stream -> `position_gap`
          - set the newest campaign snapshot's `_version` one past the head ->
            `snapshot_ahead_of_stream`
          - make that `_version` a string -> `malformed_snapshot`
      * CLI - `protean eventstore verify --json` exits 0 with `status: pass` on
        the clean store and 1 with `status: fail` after a corruption.

    Verify does not detect a deleted tail row or a deleted whole stream: what
    is left is still gapless.

KINDS LEFT TO PROTEAN'S OWN TESTS
    Message DB's schema rejects the rows the other three kinds need, so they
    cannot be injected here without altering the schema:
      * `duplicate_message_id` - `id` has a unique index (`messages_id`).
      * `malformed_message` - `id`, `stream_name` and `position` are NOT NULL.
      * `non_monotonic_global_position` - `global_position` is the primary key,
        so it cannot repeat, and the adapter reads `$all` ordered by it, so a
        read never sees it fall.

PROTEAN FINDINGS (not filed upstream yet, xfail(strict=True) here)
    * A row whose `data` is SQL NULL (the column is nullable) makes `verify()`
      raise `TypeError` from the Message DB client's `json.loads`, so no report
      comes back and the row is never named.
    * An unreachable Message DB makes the CLI exit 1, the code for "violations
      found", with a traceback and no JSON envelope. The CLI exit-code rule
      keeps 2 for an environment error.

WHY MESSAGE-DB ONLY
    Under `--protean-env memory` each process starts with an empty memory store,
    and the SQL corruptions need the real table. Skipped there.

SHARED STORE
    No context has a `[test.event_store]` overlay, so the test env and the dev
    env share one `message_store` database. Every test resets it at the start
    and in a `finally`, which also wipes dev events (as the crash-window oracle
    does). A dev engine writing to the same store during the run would break the
    exact counts; stop it first.

RUN:
    make docker-up && make setup-db      # once
    .venv/bin/python -m pytest \
        verification/oracles/test_eventstore_integrity.py --protean-env test -q
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import uuid
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from typing import NamedTuple
from urllib.parse import parse_qsl, urlparse

import pytest

ENV = os.environ.get("PROTEAN_ENV")
pytestmark = pytest.mark.skipif(
    ENV != "test",
    reason="event store integrity oracle needs a real Message DB; run with --protean-env test",
)

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
# Ten receipts after the initial stock: the item passes Protean's default
# snapshot_threshold (10), which no ShopStream context but loyalty overrides.
RECEIPTS = 10


class Workload(NamedTuple):
    item_stream: str
    item_snapshot_stream: str
    order_stream: str
    campaign_stream: str
    snapshot_stream: str


@pytest.fixture()
def beds(inventory_bed, ordering_bed, loyalty_bed):
    """The three contexts the workload writes through, with the store reset around each test.

    The helpers push `bed.domain.domain_context()`, not `bed.domain_context()`:
    the fixture's context resets every store on exit, which would wipe the
    workload before verify could read it.
    """
    beds = (inventory_bed, ordering_bed, loyalty_bed)
    _reset_stores(beds)
    try:
        yield beds
    finally:
        _reset_stores(beds)


def _reset_stores(beds):
    """Empty the shared Message DB and each context's relational store."""
    for bed in beds:
        with bed.domain.domain_context():
            from protean import current_domain

            for _, provider in current_domain.providers.items():
                provider._data_reset()
    with beds[0].domain.domain_context():
        from protean import current_domain

        current_domain.event_store.store._data_reset()


@contextmanager
def _admin_cursor(bed):
    """A cursor on the Message DB as `postgres`, the convention Protean's own truncate uses."""
    import psycopg2

    with bed.domain.domain_context():
        from protean import current_domain

        uri = current_domain.event_store.store.conn_info["database_uri"]
    parsed = urlparse(uri)
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


def _run_workload(beds):
    """Drive the fixed workload and return the stream names the tests check."""
    inventory_bed, ordering_bed, loyalty_bed = beds

    with inventory_bed.domain.domain_context():
        from protean import current_domain

        from inventory.stock.initialization import InitializeStock
        from inventory.stock.receiving import ReceiveStock
        from inventory.stock.stock import InventoryItem

        suffix = uuid.uuid4().hex[:8]
        item_id = current_domain.process(
            InitializeStock(
                product_id=f"p-{suffix}",
                variant_id=f"v-{suffix}",
                warehouse_id=f"w-{suffix}",
                sku=f"SKU-{suffix}",
                initial_quantity=0,
            ),
            asynchronous=False,
        )
        # Each ReceiveStock loads the item first; the load that sees 10 events
        # writes the item's snapshot.
        for n in range(RECEIPTS):
            current_domain.process(
                ReceiveStock(inventory_item_id=item_id, quantity=5, reference=f"GRN-{n}"),
                asynchronous=False,
            )
        category = InventoryItem.meta_.stream_category
        item_stream = f"{category}-{item_id}"
        item_snapshot_stream = f"{category}:snapshot-{item_id}"

    with ordering_bed.domain.domain_context():
        from protean import current_domain

        from ordering.order.creation import CreateOrder
        from ordering.order.order import Order

        address = {
            "street": "123 Main",
            "city": "Town",
            "state": "CA",
            "postal_code": "90210",
            "country": "US",
        }
        order_id = current_domain.process(
            CreateOrder(
                customer_id="cust-001",
                items=[
                    {
                        "product_id": "prod-001",
                        "variant_id": "var-001",
                        "sku": "SKU-001",
                        "title": "Widget",
                        "quantity": 1,
                        "unit_price": 25.0,
                    },
                ],
                shipping_address=address,
                billing_address=address,
                subtotal=25.0,
                grand_total=27.5,
            ),
            asynchronous=False,
        )
        order_stream = f"{Order.meta_.stream_category}-{order_id}"

    with loyalty_bed.domain.domain_context():
        from protean import current_domain

        from loyalty.campaign.campaign import PromoCampaign
        from verification.metamorphic.test_snapshot_equals_replay import _build_campaign

        repo = current_domain.repository_for(PromoCampaign)
        campaign = _build_campaign()
        repo.add(campaign)
        # Six events against a threshold of 5: this load writes the first snapshot.
        campaign = repo.get(campaign.id)
        for n in range(3):
            campaign.pause(reason=f"break {n}")
            campaign.activate()
        repo.add(campaign)
        # Six more events past the snapshot: this load writes the second one.
        repo.get(campaign.id)
        category = PromoCampaign.meta_.stream_category
        campaign_stream = f"{category}-{campaign.id}"
        snapshot_stream = f"{category}:snapshot-{campaign.id}"

    return Workload(item_stream, item_snapshot_stream, order_stream, campaign_stream, snapshot_stream)


def _verify(bed):
    with bed.domain.domain_context():
        from protean import current_domain

        return current_domain.event_store.store.verify()


def _delete_position_one(bed, stream):
    with _admin_cursor(bed) as cursor:
        cursor.execute(
            "DELETE FROM message_store.messages WHERE stream_name = %s AND position = 1",
            (stream,),
        )
        assert cursor.rowcount == 1


def _snapshot_versions(bed, snapshot_stream):
    """The `_version` of each snapshot row, oldest first."""
    with _admin_cursor(bed) as cursor:
        cursor.execute(
            "SELECT data->'_version' FROM message_store.messages WHERE stream_name = %s ORDER BY global_position",
            (snapshot_stream,),
        )
        return [row[0] for row in cursor.fetchall()]


def _set_newest_snapshot_version(bed, snapshot_stream, version_sql, version_args):
    """Overwrite `data._version` on the newest snapshot row; return that row's position."""
    with _admin_cursor(bed) as cursor:
        cursor.execute(
            "SELECT global_position, position FROM message_store.messages "
            "WHERE stream_name = %s ORDER BY global_position DESC LIMIT 1",
            (snapshot_stream,),
        )
        row = cursor.fetchone()
        assert row is not None, f"no snapshot row in {snapshot_stream}"
        global_position, position = row
        cursor.execute(
            "UPDATE message_store.messages "
            f"SET data = jsonb_set(data, '{{_version}}', {version_sql}) "
            "WHERE global_position = %s",
            (*version_args, global_position),
        )
        assert cursor.rowcount == 1
    return position


def _stream_head(bed, stream):
    with _admin_cursor(bed) as cursor:
        cursor.execute(
            "SELECT max(position) FROM message_store.messages WHERE stream_name = %s",
            (stream,),
        )
        return cursor.fetchone()[0]


def _run_cli(**env):
    """Run `protean eventstore verify --json` in a child process against the test env."""
    result = subprocess.run(
        [sys.executable, "-m", "protean", "eventstore", "verify", "--domain=inventory.domain", "--json"],
        cwd=SRC_DIR,
        env={
            **os.environ,
            "PROTEAN_ENV": "test",
            "PROTEAN_LOG_LEVEL": "WARNING",
            "PYTHONPATH": str(SRC_DIR),
            **env,
        },
        capture_output=True,
        text=True,
        timeout=180,
    )
    # --json sends logs to stderr, so stdout holds only the envelope.
    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"no JSON envelope on stdout (exit {result.returncode}); stderr:\n{result.stderr}")
    return result.returncode, envelope


def test_clean_workload_verifies_and_counts_match_sql(beds):
    workload = _run_workload(beds)

    with _admin_cursor(beds[0]) as cursor:
        cursor.execute("SELECT count(*), count(DISTINCT stream_name) FROM message_store.messages")
        sql_messages, sql_streams = cursor.fetchone()

    # The workload must have written what the falsifications rely on.
    assert _stream_head(beds[0], workload.item_stream) == RECEIPTS
    assert _stream_head(beds[0], workload.order_stream) == 0
    assert len(_snapshot_versions(beds[0], workload.item_snapshot_stream)) == 1
    campaign_head = _stream_head(beds[0], workload.campaign_stream)
    versions = _snapshot_versions(beds[0], workload.snapshot_stream)
    assert len(versions) == 2
    assert versions[0] < versions[1] == campaign_head

    report = _verify(beds[0])

    assert report.ok
    assert report.violations == ()
    assert report.message_count == sql_messages
    assert report.stream_count == sql_streams


def test_clean_workload_verifies_across_page_boundaries(beds, monkeypatch):
    """Two rows per page, so a row read twice or skipped between pages changes the counts."""
    workload = _run_workload(beds)
    _delete_position_one(beds[0], workload.item_stream)

    with _admin_cursor(beds[0]) as cursor:
        cursor.execute("SELECT count(*), count(DISTINCT stream_name) FROM message_store.messages")
        sql_messages, sql_streams = cursor.fetchone()
    assert sql_messages > 2

    with beds[0].domain.domain_context():
        from protean import current_domain

        store = current_domain.event_store.store
        monkeypatch.setattr(store, "_iter_all_messages", partial(type(store)._iter_all_messages, store, batch_size=2))
        report = store.verify()

    assert report.message_count == sql_messages
    assert report.stream_count == sql_streams
    assert [(v.kind, v.stream, v.position) for v in report.violations] == [("position_gap", workload.item_stream, 2)]


def test_deleted_stream_position_reports_one_position_gap(beds):
    workload = _run_workload(beds)
    _delete_position_one(beds[0], workload.item_stream)

    report = _verify(beds[0])

    assert len(report.violations) == 1
    (violation,) = report.violations
    assert violation.kind == "position_gap"
    assert violation.stream == workload.item_stream
    assert violation.position == 2
    assert "expected 1" in violation.detail


def test_snapshot_version_past_stream_head_reports_snapshot_ahead(beds):
    workload = _run_workload(beds)
    ahead = _stream_head(beds[0], workload.campaign_stream) + 1
    _set_newest_snapshot_version(beds[0], workload.snapshot_stream, "to_jsonb(%s::int)", (ahead,))

    report = _verify(beds[0])

    assert len(report.violations) == 1
    (violation,) = report.violations
    assert violation.kind == "snapshot_ahead_of_stream"
    assert violation.stream == workload.snapshot_stream
    assert violation.position is None


def test_non_integer_snapshot_version_reports_malformed_snapshot(beds):
    workload = _run_workload(beds)
    position = _set_newest_snapshot_version(beds[0], workload.snapshot_stream, "to_jsonb(%s::text)", ("7",))
    # The newest of two snapshot rows, so a check of the first row only would miss it.
    assert position == 1

    report = _verify(beds[0])

    assert len(report.violations) == 1
    (violation,) = report.violations
    assert violation.kind == "malformed_snapshot"
    assert violation.stream == workload.snapshot_stream
    assert violation.position == position


@pytest.mark.xfail(
    strict=True,
    raises=TypeError,
    reason="Protean bug, not filed yet: verify() raises TypeError on a row with NULL data instead of reporting it",
)
def test_null_message_data_is_reported_not_raised(beds):
    workload = _run_workload(beds)
    with _admin_cursor(beds[0]) as cursor:
        cursor.execute(
            "UPDATE message_store.messages SET data = NULL WHERE stream_name = %s AND position = 1",
            (workload.item_stream,),
        )
        assert cursor.rowcount == 1

    report = _verify(beds[0])

    # The kind is left open: upstream decides which kind a NULL body becomes.
    assert not report.ok
    assert [(v.stream, v.position) for v in report.violations] == [(workload.item_stream, 1)]


def test_cli_exits_0_on_clean_store_and_1_on_corrupted_store(beds):
    workload = _run_workload(beds)

    code, envelope = _run_cli()
    assert code == 0
    assert envelope["status"] == "pass"
    assert envelope["data"]["violations"] == []

    _delete_position_one(beds[0], workload.item_stream)

    code, envelope = _run_cli()
    assert code == 1
    assert envelope["status"] == "fail"
    violations = envelope["data"]["violations"]
    assert len(violations) == 1
    assert violations[0]["kind"] == "position_gap"
    assert violations[0]["stream"] == workload.item_stream
    assert violations[0]["position"] == 2


@pytest.mark.xfail(
    strict=True,
    reason="Protean bug, not filed yet: an unreachable Message DB makes the CLI exit 1 with no JSON envelope",
)
def test_cli_exits_2_with_an_error_envelope_when_message_db_is_unreachable():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        closed_port = sock.getsockname()[1]

    code, envelope = _run_cli(
        MESSAGE_DB_URL=f"postgresql://message_store:message_store@127.0.0.1:{closed_port}/message_store"
    )

    assert code == 2
    assert envelope["status"] == "error"
