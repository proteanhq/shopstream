"""P4 - exactly one outbox row per (message_id, target_broker).

WHAT THIS CHECKS
    The outbox is the atomic hand-off between "the aggregate changed" and "the
    event was published". Its correctness rests on one row per delivery target:

      - A `published=True` event is dual-written — one row for the internal
        broker, one for every external broker — all sharing a single
        `message_id` and differing only by `target_broker`.
      - No target may ever receive TWO rows for the same message, or the Engine
        would publish that event twice.

    Protean guarantees this with a UNIQUE index on `(message_id, target_broker)`
    (see `protean.utils.outbox.OUTBOX_INDEXES`). This oracle checks both halves:
    the happy-path dual-write produces exactly the expected rows, and the
    database physically rejects a duplicate.

WHY THIS IS A TYPE-A ORACLE (see VERIFICATION_STRATEGY.md section 2)
    The "duplicate rejected" check probes the schema guarantee directly — it
    forces a second insert with the same key and asserts the database raises
    `IntegrityError`. The expected outcome is defined by the constraint, not by
    reading back what Protean happened to write, so a framework bug that emitted
    a duplicate row could not hide it.

WHY THE DUPLICATE CHECK IS POSTGRES-ONLY
    This half asserts the specific relational failure — `sqlalchemy.exc.
    IntegrityError`. The in-memory adapter now enforces the unique index too (since
    proteanhq/protean#1074), but rejects with a Protean `ValidationError`, not the
    SQLAlchemy type; that memory-enforcement path is guarded by
    `regression/test_1071_memory_adapter_enforces_unique_index`. The dual-write
    shape check is adapter-independent and runs everywhere.

RUN:
    make docker-up && make setup-db      # once
    .venv/bin/python -m pytest \
        verification/oracles/test_outbox_exactly_once.py --protean-env test -q
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

ENV = os.environ.get("PROTEAN_ENV")


def _earn_points(loyalty):
    """Fire a published-event command; return only THIS command's PointsEarned rows.

    The outbox accumulates rows until they are published, so filter to the
    account just created (a unique customer per call) rather than assuming the
    table is empty.
    """
    from loyalty.reward.enrollment import EnrollRewardAccount
    from loyalty.reward.points import EarnPoints

    customer_id = f"cust-p4-{uuid.uuid4().hex[:8]}"
    account_id = loyalty.process(EnrollRewardAccount(customer_id=customer_id), asynchronous=False)
    loyalty.process(EarnPoints(account_id=account_id, amount=120, reason="order"), asynchronous=False)

    rows = loyalty._get_outbox_repo("default").find_unprocessed()
    return [r for r in rows if r.type == "Loyalty.PointsEarned.v1" and r.data.get("account_id") == account_id]


@pytest.mark.usefixtures("loyalty_ctx")
def test_published_event_dual_written_exactly_once():
    """A published event yields exactly one row per (message_id, target_broker)."""
    from protean import current_domain

    earned = _earn_points(current_domain)

    pairs = [(r.message_id, r.target_broker) for r in earned]

    # published=True ⇒ one internal (default) + one external (global) row...
    assert {r.target_broker for r in earned} == {"default", "global"}
    # ...sharing a single message_id...
    assert len({r.message_id for r in earned}) == 1
    # ...and no (message_id, target_broker) appears more than once.
    assert len(pairs) == len(set(pairs)) == 2, f"expected 2 unique rows, got {pairs}"


@pytest.mark.skipif(
    ENV != "test",
    reason="asserts the relational sqlalchemy IntegrityError; memory enforces too but raises a Protean error (see test_1071)",
)
@pytest.mark.usefixtures("loyalty_ctx")
def test_duplicate_outbox_row_is_rejected_by_the_database():
    """Forcing a second row with the same (message_id, target_broker) must fail.

    This is the teeth: it proves the DB — not just application code — prevents a
    message from being published twice to the same broker.
    """
    from protean import current_domain
    from protean.utils.outbox import Outbox

    earned = _earn_points(current_domain)
    existing = earned[0]

    # A brand-new Outbox row (fresh id) that collides on the unique key.
    duplicate = Outbox.create_message(
        message_id=existing.message_id,
        stream_name=existing.stream_name,
        message_type=existing.type,
        data=existing.data,
        metadata=existing.metadata_,
        target_broker=existing.target_broker,
    )
    outbox_repo = current_domain._get_outbox_repo("default")

    with pytest.raises(IntegrityError):
        outbox_repo._dao.save(duplicate)
