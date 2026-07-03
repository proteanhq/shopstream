"""P11 - loading an aggregate via a snapshot equals a full event replay.

WHAT THIS CHECKS
    An event-sourced aggregate can be reconstructed two ways:

      * FULL REPLAY - fold the entire event stream from version 0 through the
        @apply handlers.
      * SNAPSHOT LOAD - restore a persisted snapshot (a materialized state at
        version K) and then fold only the events after K.

    Protean snapshots aggregates once a stream crosses `snapshot_threshold`
    (loyalty sets it to 5). Both reconstruction paths must yield the exact same
    aggregate - a snapshot that drops or mis-encodes a field would make a loaded
    aggregate silently disagree with its own history.

    Property P11: snapshot load == full replay.

WHERE THE TWO PATHS COME FROM
    We capture the full-replay state BEFORE any snapshot exists (repository.get
    folds the whole stream), then create a snapshot and load again (repository
    .get now restores from the snapshot). Same id, same events, two
    reconstruction paths - they must be identical. A second assertion adds events
    AFTER the snapshot and checks the snapshot+tail load still matches the live
    in-memory aggregate, so the "fold only events after K" path is exercised too.

SCOPE
    Metamorphic (source B): only catches bugs that differ between the two paths.
    PromoCampaign is ShopStream's only snapshot-configured aggregate; this check
    lives next to it. If another domain enables snapshots, add a case here.

RUN (no Docker):
    .venv/bin/python -m pytest \
        verification/metamorphic/test_snapshot_equals_replay.py --protean-env memory -q
"""

import pytest
from protean import current_domain


def _build_campaign():
    """Launch a campaign and drive >5 delta events to cross snapshot_threshold=5."""
    from loyalty.campaign.campaign import PromoCampaign

    campaign = PromoCampaign.launch(
        campaign_code="P11",
        name="Snapshot Days",
        discount_type="points_multiplier",
        discount_value=3,
    )
    # launch + 5 transitions = 6 events, past the threshold of 5.
    campaign.activate()
    campaign.pause(reason="scheduled break")
    campaign.activate()
    campaign.pause(reason="second break")
    campaign.activate()
    return campaign


@pytest.mark.usefixtures("loyalty_ctx")
def test_snapshot_load_equals_full_replay():
    from loyalty.campaign.campaign import PromoCampaign

    live = _build_campaign()
    repo = current_domain.repository_for(PromoCampaign)
    repo.add(live)

    # Path 1: full replay - no snapshot exists yet, so .get folds the whole stream.
    full_replay = repo.get(live.id)

    # Materialize a snapshot at the current version.
    created = current_domain.create_snapshot(PromoCampaign, live.id)
    assert created is True, "expected a snapshot to be created past the threshold"

    # Path 2: snapshot load - .get now restores from the snapshot.
    from_snapshot = repo.get(live.id)

    assert from_snapshot.to_dict() == full_replay.to_dict()


@pytest.mark.usefixtures("loyalty_ctx")
def test_snapshot_plus_tail_equals_live():
    """Snapshot at version K, then more events: load must fold snapshot + tail."""
    from loyalty.campaign.campaign import PromoCampaign

    campaign = _build_campaign()  # ends 'active'
    repo = current_domain.repository_for(PromoCampaign)
    repo.add(campaign)

    current_domain.create_snapshot(PromoCampaign, campaign.id)

    # Load (from the snapshot), mutate, and persist the new event AFTER the
    # snapshot - the idiomatic load -> mutate -> save cycle.
    loaded = repo.get(campaign.id)
    loaded.pause(reason="post-snapshot pause")
    repo.add(loaded)

    # Reconstruction now folds: snapshot (version K) + the one event after it.
    reloaded = repo.get(campaign.id)

    assert reloaded.to_dict() == loaded.to_dict()
    assert reloaded.status == "paused"
