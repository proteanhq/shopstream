"""A snapshot that predates the current schema is discarded, and the load equals a full replay.

WHAT THIS CHECKS
    A snapshot is a cache of an aggregate's state at version K. When the
    aggregate's fields change after the snapshot was written (a field renamed,
    removed or newly required), the stored dict no longer builds the aggregate.
    Protean then logs a `snapshot_discarded` warning on the `protean.snapshot`
    logger and rebuilds the aggregate from its whole event stream.

    Each test writes such a stale snapshot straight to PromoCampaign's snapshot
    stream and checks that:

      * the load equals a full replay of the same stream,
      * exactly one `snapshot_discarded` record is logged for that load,
      * a current-version load past `snapshot_threshold` writes a fresh
        snapshot, so the next load logs nothing (the repair),
      * an `at_version` load never writes one, so each load logs again,
      * a snapshot that still builds is used, and nothing is logged.

    Property: stale snapshot load == full replay.

SCOPE
    Metamorphic (source B), PromoCampaign only (loyalty's `snapshot_threshold`
    is 5). A stale snapshot that still builds is outside this check: Protean
    uses it as it is. That case is pinned as a Protean finding in
    `verification/regression/test_protean_regressions.py`.

RUN (no Docker):
    .venv/bin/python -m pytest \
        verification/metamorphic/test_stale_snapshot_falls_back_to_replay.py --protean-env memory -q
"""

import logging

import pytest
from protean import current_domain


def _build_campaign(transitions: int = 5):
    """Launch a campaign and alternate activate/pause `transitions` times (ends active)."""
    from loyalty.campaign.campaign import PromoCampaign

    campaign = PromoCampaign.launch(
        campaign_code="STALE",
        name="Stale Days",
        discount_type="points_multiplier",
        discount_value=2,
    )
    for step in range(transitions):
        if step % 2 == 0:
            campaign.activate()
        else:
            campaign.pause(reason=f"break {step}")
    return campaign


def _write_snapshot(identifier: str, data: dict) -> None:
    from loyalty.campaign.campaign import PromoCampaign

    current_domain.event_store.store._write(
        f"{PromoCampaign.meta_.stream_category}:snapshot-{identifier}",
        "SNAPSHOT",
        data,
    )


def _discards(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "protean.snapshot" and r.getMessage() == "snapshot_discarded"]


def _extra_key(data: dict) -> dict:
    return {**data, "legacy_code": "OLD-1"}


def _renamed_field(data: dict) -> dict:
    stale = {k: v for k, v in data.items() if k != "name"}
    stale["campaign_name"] = data["name"]
    return stale


def _missing_required_field(data: dict) -> dict:
    return {k: v for k, v in data.items() if k != "campaign_code"}


STALE_SHAPES = [
    pytest.param(_extra_key, id="removed-field"),
    pytest.param(_renamed_field, id="renamed-field"),
    pytest.param(_missing_required_field, id="newly-required-field"),
]


@pytest.mark.parametrize("make_stale", STALE_SHAPES)
@pytest.mark.usefixtures("loyalty_ctx")
def test_stale_snapshot_is_discarded_and_rewritten(make_stale, caplog):
    from loyalty.campaign.campaign import PromoCampaign

    live = _build_campaign()  # 6 events, past the threshold of 5
    repo = current_domain.repository_for(PromoCampaign)
    repo.add(live)
    full_replay = repo.get(live.id)
    expected = full_replay.to_dict()

    _write_snapshot(live.id, make_stale(expected))

    with caplog.at_level(logging.WARNING, logger="protean.snapshot"):
        first = repo.get(live.id)
    discarded = _discards(caplog)
    assert first.to_dict() == expected
    assert len(discarded) == 1
    assert discarded[0].aggregate == "PromoCampaign"
    assert str(discarded[0].aggregate_id) == str(live.id)

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="protean.snapshot"):
        second = repo.get(live.id)
    assert second.to_dict() == expected
    assert _discards(caplog) == [], "the first load should have written a fresh snapshot"


@pytest.mark.usefixtures("loyalty_ctx")
def test_stale_snapshot_at_version_replays_and_writes_nothing(caplog):
    from loyalty.campaign.campaign import PromoCampaign

    live = _build_campaign()
    repo = current_domain.repository_for(PromoCampaign)
    repo.add(live)
    full_replay = repo.get(live.id)
    head = full_replay._version
    expected = repo.get(live.id, at_version=head).to_dict()

    # The snapshot carries `_version == head`, so the at_version path tries it.
    _write_snapshot(live.id, _extra_key(full_replay.to_dict()))

    for attempt in (1, 2):
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="protean.snapshot"):
            loaded = repo.get(live.id, at_version=head)
        assert loaded.to_dict() == expected, f"load {attempt}"
        assert len(_discards(caplog)) == 1, f"load {attempt}: a temporal load writes no snapshot"


@pytest.mark.usefixtures("loyalty_ctx")
def test_stale_snapshot_below_threshold_is_discarded_until_rebuilt(caplog):
    from loyalty.campaign.campaign import PromoCampaign

    live = _build_campaign(transitions=1)  # 2 events, below the threshold of 5
    repo = current_domain.repository_for(PromoCampaign)
    repo.add(live)
    full_replay = repo.get(live.id)
    expected = full_replay.to_dict()

    _write_snapshot(live.id, _extra_key(expected))

    for attempt in (1, 2):
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="protean.snapshot"):
            loaded = repo.get(live.id)
        assert loaded.to_dict() == expected, f"load {attempt}"
        assert len(_discards(caplog)) == 1, f"load {attempt}: below the threshold no snapshot is rewritten"

    assert current_domain.create_snapshot(PromoCampaign, live.id) is True

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="protean.snapshot"):
        rebuilt = repo.get(live.id)
    assert rebuilt.to_dict() == expected
    assert _discards(caplog) == []


@pytest.mark.usefixtures("loyalty_ctx")
def test_snapshot_that_builds_is_used(caplog):
    from loyalty.campaign.campaign import PromoCampaign

    live = _build_campaign()
    repo = current_domain.repository_for(PromoCampaign)
    repo.add(live)
    full_replay = repo.get(live.id)

    # A name no event ever set proves the load came from this snapshot, not a replay.
    _write_snapshot(live.id, {**full_replay.to_dict(), "name": "FROM-SNAPSHOT"})

    with caplog.at_level(logging.WARNING, logger="protean.snapshot"):
        loaded = repo.get(live.id)
    assert loaded.name == "FROM-SNAPSHOT"
    assert loaded.status == full_replay.status
    assert _discards(caplog) == []
