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
    fix touched both the attribute setter (`ValueObject.__set__`) and
    serialization (`to_dict`), so the test checks the reloaded attribute and its
    serialized form. The fix arrived with the pin bump to Protean main 6b4cd312
    (after 0.17.0), so this is now a permanent guard.
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
    assert reloaded.to_dict()["levels"] == {
        "on_hand": 0,
        "reserved": 0,
        "available": 0,
        "in_transit": 0,
        "damaged": 0,
    }


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="current_domain warns 'Working outside of domain context' on attribute and type probes",
)
def test_current_domain_probe_outside_context_is_silent():
    """Protean finding (not filed, feature request): `current_domain` has no warning-free probe.

    Test modules import `current_domain` at module level. During collection pytest
    runs `getattr(obj, "__test__", None)` (`_pytest/compat.py`) and `isinstance`
    checks over every module attribute. With no domain context active, both go
    through the proxy's `_find_domain()` and emit the "Working outside of domain
    context" `UserWarning`, so collection prints it for dozens of modules.

    The proxy's docstring promises None-like results outside a context, not
    silence, and Protean's own tests assert that `bool`/`repr` warn. So this is a
    request for a probe that stays quiet (as `_domain_now()` already reads the
    stack without warning), not a regression. The warning predates this pin: it
    showed on Protean 0.16.0 too, and `pyproject.toml` filters it for the suite.
    """
    from protean import current_domain
    from protean.utils.globals import _domain_context_stack

    if _domain_context_stack.top is not None:
        pytest.fail("precondition: no domain context may be active")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        test_attr = getattr(current_domain, "__test__", None)
        is_type = isinstance(current_domain, type)

    assert test_attr is None
    assert is_type is False
    messages = [str(w.message) for w in caught]
    assert not any("outside of domain context" in m for m in messages), messages


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Config2 keeps only keys from _default_config(), so a top-level [lint] table in domain.toml is dropped",
)
def test_lint_table_in_domain_toml_is_loaded(tmp_path, monkeypatch):
    """Protean finding (not filed): a top-level `[lint]` table in `domain.toml` is dropped.

    Protean's configuration docs describe a `[lint]` table (`level`, `suppressions`,
    and more) that `protean check` and `protean verify` read through
    `domain.config.get("lint", {})`. `Config2._normalize_config` keeps only the
    top-level keys that `_default_config()` defines, and `lint` is not one of
    them, so a top-level `[lint]` is discarded. An environment overlay such as
    `[test.lint]` is deep-merged without that key filter, so it does load. The
    bug is that the filter is applied to one and not the other.

    ShopStream's `make domain-check` works around it by reading the error count
    from `protean check --format=json`.
    """
    from protean.domain.config import Config2

    (tmp_path / "domain.toml").write_text('debug = true\n\n[lint]\nlevel = "error"\n\n[test.lint]\nlevel = "error"\n')

    monkeypatch.setenv("PROTEAN_ENV", "test")
    overlay = Config2.load_from_path(str(tmp_path))
    if overlay.get("lint", {}).get("level") != "error":
        pytest.fail("precondition: the [test.lint] overlay should load")

    monkeypatch.delenv("PROTEAN_ENV")
    config = Config2.load_from_path(str(tmp_path))

    if config["debug"] is not True:
        pytest.fail("precondition: the domain.toml was read")
    assert config.get("lint", {}).get("level") == "error"


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="the is_event_sourced deprecation warning is attributed to protean/domain/__init__.py, not the caller",
)
def test_is_event_sourced_warning_points_at_the_decorator():
    """Protean finding (not filed): the `is_event_sourced` warning names the wrong line.

    Registering an element with the deprecated `is_event_sourced=True` warns, but
    the warning's file and line are Protean's own `_domain_element.wrap` in
    `protean/domain/__init__.py`, not the `@domain.aggregate(...)` line that used
    the option. The `stacklevel` stops one frame short, so a user cannot see which
    of their elements to change.
    """
    from protean import Domain
    from protean.fields import String

    domain = Domain(name="StacklevelProbe")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        @domain.aggregate(is_event_sourced=True)
        class Probe:
            name = String()

    deprecations = [w for w in caught if "is_event_sourced" in str(w.message)]
    if not deprecations:
        pytest.fail("precondition: the deprecation warning was raised")
    assert deprecations[0].filename == __file__, deprecations[0].filename
