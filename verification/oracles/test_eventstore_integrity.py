"""Event store integrity - `verify` passes on real workloads and catches corruption.

WHAT THIS CHECKS
    `BaseEventStore.verify()` (CLI: `protean eventstore verify`) reads the whole
    store once and reports every break of the store's own rules: a gap in a
    stream's positions, a snapshot whose `_version` runs past its aggregate
    stream, a malformed snapshot, and a few kinds the schema below rules out.
    Upstream tests the violation cases against the in-file and memory stores and
    only the clean path against Message DB. This oracle closes that gap for
    ShopStream:

      * CLEAN - real command paths write an event-sourced InventoryItem, an
        Order and a PromoCampaign past loyalty's `snapshot_threshold` (5). The
        store must verify clean, and its message and stream counts must equal
        independent SQL counts.
      * FALSIFICATIONS - one hand-made corruption per test, written as the
        `postgres` user. Each must yield exactly one violation of the expected
        kind, stream and position:
          - delete position 1 of the InventoryItem stream -> `position_gap`
          - raise the newest snapshot's `_version` past the head ->
            `snapshot_ahead_of_stream`
          - make that `_version` a string -> `malformed_snapshot`
      * CLI - `protean eventstore verify --json` exits 0 with `status: pass` on
        the clean store and 1 with `status: fail` after a corruption.

KINDS LEFT TO PROTEAN'S OWN TESTS
    Message DB's schema rejects the rows the other three kinds need, so they
    cannot be injected here:
      * `duplicate_message_id` - `id` has a unique index (`messages_id`).
      * `malformed_message` - `id`, `stream_name` and `position` are NOT NULL.
      * `non_monotonic_global_position` - `global_position` is the primary key
        and verify reads rows ordered by it, so a read can never see it repeat
        or fall.

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
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

import pytest

ENV = os.environ.get("PROTEAN_ENV")
pytestmark = pytest.mark.skipif(
    ENV != "test",
    reason="event store integrity oracle needs a real Message DB; run with --protean-env test",
)

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
RECEIPTS = 3


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
    """Drive the fixed workload through real command paths.

    Returns the InventoryItem stream, the PromoCampaign stream and its snapshot
    stream, the names the falsifications corrupt.
    """
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
        for n in range(RECEIPTS):
            current_domain.process(
                ReceiveStock(inventory_item_id=item_id, quantity=5, reference=f"GRN-{n}"),
                asynchronous=False,
            )
        item_stream = f"{InventoryItem.meta_.stream_category}-{item_id}"

    with ordering_bed.domain.domain_context():
        from protean import current_domain

        from ordering.order.creation import CreateOrder

        address = {
            "street": "123 Main",
            "city": "Town",
            "state": "CA",
            "postal_code": "90210",
            "country": "US",
        }
        current_domain.process(
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

    with loyalty_bed.domain.domain_context():
        from protean import current_domain

        from loyalty.campaign.campaign import PromoCampaign
        from verification.metamorphic.test_snapshot_equals_replay import _build_campaign

        campaign = _build_campaign()
        current_domain.repository_for(PromoCampaign).add(campaign)
        assert current_domain.create_snapshot(PromoCampaign, campaign.id) is True
        category = PromoCampaign.meta_.stream_category
        campaign_stream = f"{category}-{campaign.id}"
        snapshot_stream = f"{category}:snapshot-{campaign.id}"

    return item_stream, campaign_stream, snapshot_stream


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


def _run_cli():
    """Run `protean eventstore verify --json` in a child process against the test env."""
    result = subprocess.run(
        [sys.executable, "-m", "protean", "eventstore", "verify", "--domain=inventory.domain", "--json"],
        cwd=SRC_DIR,
        env={**os.environ, "PROTEAN_ENV": "test", "PROTEAN_LOG_LEVEL": "WARNING", "PYTHONPATH": str(SRC_DIR)},
        capture_output=True,
        text=True,
        timeout=180,
    )
    # --json sends logs to stderr, so stdout holds only the envelope.
    return result.returncode, json.loads(result.stdout)


def test_clean_workload_verifies_and_counts_match_sql(beds):
    item_stream, _, snapshot_stream = _run_workload(beds)

    with _admin_cursor(beds[0]) as cursor:
        cursor.execute("SELECT count(*), count(DISTINCT stream_name) FROM message_store.messages")
        sql_messages, sql_streams = cursor.fetchone()
        cursor.execute(
            "SELECT count(*) FROM message_store.messages WHERE stream_name = %s",
            (snapshot_stream,),
        )
        (snapshots,) = cursor.fetchone()

    # The workload must have written what the falsifications rely on.
    assert _stream_head(beds[0], item_stream) == RECEIPTS
    assert snapshots >= 1

    report = _verify(beds[0])

    assert report.ok
    assert report.violations == ()
    assert report.message_count == sql_messages
    assert report.stream_count == sql_streams


def test_deleted_stream_position_reports_one_position_gap(beds):
    item_stream, _, _ = _run_workload(beds)
    _delete_position_one(beds[0], item_stream)

    report = _verify(beds[0])

    assert len(report.violations) == 1
    (violation,) = report.violations
    assert violation.kind == "position_gap"
    assert violation.stream == item_stream
    assert violation.position == 2
    assert "expected 1" in violation.detail


def test_snapshot_version_past_stream_head_reports_snapshot_ahead(beds):
    _, campaign_stream, snapshot_stream = _run_workload(beds)
    ahead = _stream_head(beds[0], campaign_stream) + 5
    _set_newest_snapshot_version(beds[0], snapshot_stream, "to_jsonb(%s::int)", (ahead,))

    report = _verify(beds[0])

    assert len(report.violations) == 1
    (violation,) = report.violations
    assert violation.kind == "snapshot_ahead_of_stream"
    assert violation.stream == snapshot_stream
    assert violation.position is None
    assert f"_version {ahead}" in violation.detail


def test_non_integer_snapshot_version_reports_malformed_snapshot(beds):
    _, _, snapshot_stream = _run_workload(beds)
    position = _set_newest_snapshot_version(beds[0], snapshot_stream, "to_jsonb(%s::text)", ("7",))

    report = _verify(beds[0])

    assert len(report.violations) == 1
    (violation,) = report.violations
    assert violation.kind == "malformed_snapshot"
    assert violation.stream == snapshot_stream
    assert violation.position == position


def test_cli_exits_0_on_clean_store_and_1_on_corrupted_store(beds):
    item_stream, _, _ = _run_workload(beds)

    code, envelope = _run_cli()
    assert code == 0
    assert envelope["status"] == "pass"
    assert envelope["data"]["violations"] == []

    _delete_position_one(beds[0], item_stream)

    code, envelope = _run_cli()
    assert code == 1
    assert envelope["status"] == "fail"
    violations = envelope["data"]["violations"]
    assert len(violations) == 1
    assert violations[0]["kind"] == "position_gap"
    assert violations[0]["stream"] == item_stream
    assert violations[0]["position"] == 2
