"""Named regressions for Protean bugs ShopStream found (the T1.5 habit).

Every Protean bug ShopStream surfaces becomes ONE permanent, named test here (or
an oracle, cross-referenced in README.md). The naming is `test_<issue>_<slug>` so
the guard and the upstream issue are one click apart.

Lifecycle of a regression:

  1. Bug found → filed upstream → a test added here that asserts the CORRECT
     (post-fix) behavior.
  2. While the installed Protean still has the bug, the test is `xfail(strict)` —
     it documents the bug and, because it is strict, flips loudly (xpass → failure)
     the moment the fix lands, prompting us to drop the marker.
  3. Once the fix is in ShopStream's Protean pin, the marker is removed and the
     test becomes a permanent green guard against regression.

See README.md for the full manifest (every filed issue → its guard → status).
"""

from __future__ import annotations

import os
import warnings
from datetime import datetime

import pytest

ENV = os.environ.get("PROTEAN_ENV")


def _earn_points_row():
    """Process a published-event command; return its PointsEarned outbox row."""
    import uuid

    from protean import current_domain

    from loyalty.reward.enrollment import EnrollRewardAccount
    from loyalty.reward.points import EarnPoints

    account_id = current_domain.process(
        EnrollRewardAccount(customer_id=f"cust-reg-{uuid.uuid4().hex[:8]}"), asynchronous=False
    )
    current_domain.process(EarnPoints(account_id=account_id, amount=120, reason="order"), asynchronous=False)

    rows = current_domain._get_outbox_repo("default").find_unprocessed()
    return next(r for r in rows if r.type == "Loyalty.PointsEarned.v1" and r.data.get("account_id") == account_id)


@pytest.mark.usefixtures("loyalty_ctx")
def test_1039_event_datetime_serialized_as_iso_utc():
    """proteanhq/protean#1039 (FIXED): datetime payloads are ISO-8601, UTC-normalized.

    The bug serialized datetimes with `str()` — naive, timezone-lossy, and in a
    different format from the metadata. The fix emits `.isoformat()` in UTC. This
    guards against a regression to `str()`.
    """
    row = _earn_points_row()
    raw = row.data["occurred_at"]

    # Must be a parseable ISO-8601 string (not str(datetime), not a bare object).
    assert isinstance(raw, str)
    parsed = datetime.fromisoformat(raw)  # raises if it regressed to str()/non-ISO

    # ...and timezone-aware, normalized to UTC (offset zero).
    assert parsed.tzinfo is not None, f"datetime lost its timezone: {raw!r}"
    assert parsed.utcoffset().total_seconds() == 0, f"datetime not UTC-normalized: {raw!r}"


@pytest.mark.skipif(
    ENV == "test",
    reason="#1071 is about the in-memory adapter; the relational path is covered by test_outbox_exactly_once",
)
@pytest.mark.usefixtures("loyalty_ctx")
def test_1071_memory_adapter_enforces_unique_index():
    """proteanhq/protean#1071 (guard): the in-memory adapter enforces Index(unique=True).

    Was a tripwire (xfail) while the fix was upstream-only; the pin bump to Protean
    main (#1074) landed it, so this is now a permanent guard against regression.
    """
    from protean import current_domain
    from protean.utils.outbox import Outbox

    row = _earn_points_row()
    duplicate = Outbox.create_message(
        message_id=row.message_id,
        stream_name=row.stream_name,
        message_type=row.type,
        data=row.data,
        metadata=row.metadata_,
        target_broker=row.target_broker,  # same composite unique key
    )

    rejected = False
    try:
        current_domain._get_outbox_repo("default")._dao.save(duplicate)
    except Exception:
        rejected = True
    assert rejected, "in-memory adapter accepted a row that violates the (message_id, target_broker) unique index"


@pytest.mark.usefixtures("inventory_ctx")
def test_1078_all_default_value_object_round_trips():
    """proteanhq/protean#1078 (guard): an all-default ValueObject survives event replay.

    An event-sourced aggregate whose ValueObject had only falsy fields (every
    `StockLevels` count at 0) came back as `None` after a persist and reload. The
    pin bump to Protean 0.17.0 landed the fix, so this is now a permanent guard.
    """
    import uuid

    from protean import current_domain

    from inventory.stock.stock import InventoryItem, StockLevels

    item = InventoryItem.create(
        product_id=str(uuid.uuid4()),
        variant_id=str(uuid.uuid4()),
        warehouse_id=str(uuid.uuid4()),
        sku=f"SKU-{uuid.uuid4().hex[:8]}",
        initial_quantity=0,
        reorder_point=0,
    )
    repo = current_domain.repository_for(InventoryItem)
    repo.add(item)

    reloaded = repo.get(item.id)
    assert reloaded.levels == StockLevels(on_hand=0, reserved=0, available=0, in_transit=0, damaged=0)


@pytest.mark.xfail(
    strict=True,
    reason="current_domain's __class__ property warns 'Working outside of domain context' on a type probe",
)
def test_current_domain_type_probe_outside_context_is_silent():
    """Protean finding (not filed): probing `current_domain`'s type outside a context warns.

    Test modules import `current_domain` at module level. During collection pytest
    runs `isinstance(obj, type)` and `issubclass(...)` over every module attribute,
    which reads the proxy's `__class__`. With no domain context active, that read
    goes through `_find_domain()` and emits the "Working outside of domain context"
    `UserWarning`, so collection prints it for dozens of modules. The proxy is meant
    to act like `None` when nothing is active; a type probe is not domain use and
    should stay silent, the way `_domain_now()` reads the stack without warning.
    """
    from protean import current_domain
    from protean.utils.globals import _domain_context_stack

    assert _domain_context_stack.top is None, "precondition: no domain context is active"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        is_type = isinstance(current_domain, type)

    assert is_type is False
    messages = [str(w.message) for w in caught]
    assert not any("outside of domain context" in m for m in messages), messages
