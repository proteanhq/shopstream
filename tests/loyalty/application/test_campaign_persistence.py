"""Persistence tests for the event-sourced PromoCampaign aggregate.

Verifies state is reconstructed from the event stream and that fact_events=True emits a
complete-state fact event on the ...-fact-<id> stream after each persist.
"""

from protean import current_domain

from loyalty.campaign.campaign import PromoCampaign


def _persist_launched_active(code="SUMMER10"):
    campaign = PromoCampaign.launch(code, "Summer Sale", "percentage", 10)
    campaign.activate()
    current_domain.repository_for(PromoCampaign).add(campaign)
    return campaign.id


class TestPromoCampaignEventSourcing:
    def test_roundtrip_reconstructs_state_from_events(self):
        campaign_id = _persist_launched_active()

        loaded = current_domain.repository_for(PromoCampaign).get(campaign_id)
        assert loaded.campaign_code == "SUMMER10"
        assert loaded.discount_type == "percentage"
        assert loaded.status == "active"

    def test_fact_event_carries_full_state(self):
        campaign_id = _persist_launched_active(code="WINTER20")

        store = current_domain.event_store.store
        fact_messages = store.read(f"loyalty::promo_campaign-fact-{campaign_id}")
        assert len(fact_messages) >= 1

        data = fact_messages[-1].data
        assert data["campaign_code"] == "WINTER20"
        assert data["status"] == "active"
        assert data["discount_type"] == "percentage"
        assert data["discount_value"] == 10


class TestPromoCampaignSnapshots:
    """Event-sourcing snapshots (snapshot_threshold=5 in loyalty domain.toml)."""

    def test_create_snapshot_and_reload_preserves_state(self):
        campaign = PromoCampaign.launch("SNAP1", "Snapshot Sale", "percentage", 10)
        campaign.activate()
        campaign.pause(reason="budget")
        campaign.activate()
        current_domain.repository_for(PromoCampaign).add(campaign)

        assert current_domain.create_snapshot(PromoCampaign, campaign.id) is True

        loaded = current_domain.repository_for(PromoCampaign).get(campaign.id)
        assert loaded.status == "active"
        assert loaded.campaign_code == "SNAP1"

    def test_create_snapshots_for_all_instances(self):
        for i in range(2):
            campaign = PromoCampaign.launch(f"BULK{i}", "Bulk", "fixed", 5)
            current_domain.repository_for(PromoCampaign).add(campaign)

        count = current_domain.create_snapshots(PromoCampaign)
        assert count >= 2


class TestCampaignLaunchedUpcastingOnReplay:
    """A historical v1 CampaignLaunched event is upcast v1->v2->v3 during replay."""

    def _write_raw_v1_event(self, store, stream, data, position=0):
        type_string = "Loyalty.CampaignLaunched.v1"
        store._write(
            stream,
            type_string,
            data,
            {
                "headers": {
                    "id": f"evt-{position}",
                    "type": type_string,
                    "time": "2025-01-01T00:00:00+00:00",
                    "stream": stream,
                },
                "envelope": {"specversion": "1.0"},
                "domain": {
                    "fqn": "loyalty.campaign.events.CampaignLaunched",
                    "kind": "EVENT",
                    "origin_stream": None,
                    "stream_category": stream.rsplit("-", 1)[0],
                    "version": 1,
                    "sequence_id": str(position),
                    "asynchronous": True,
                },
            },
            position - 1,
        )

    def test_v1_event_upcast_through_full_chain(self):
        campaign_id = "promo-upcast-001"
        stream = f"loyalty::promo_campaign-{campaign_id}"
        store = current_domain.event_store.store

        # v1 schema: a single discount_pct, no discount_type / scheduling fields.
        self._write_raw_v1_event(
            store,
            stream,
            {
                "campaign_id": campaign_id,
                "campaign_code": "LEGACY15",
                "name": "Legacy Campaign",
                "discount_pct": 15,
                "launched_at": "2025-01-01T00:00:00+00:00",
            },
        )

        campaign = current_domain.repository_for(PromoCampaign).get(campaign_id)
        assert campaign.campaign_code == "LEGACY15"
        assert campaign.discount_value == 15  # v1 discount_pct -> v2 discount_value
        assert campaign.discount_type == "percentage"  # added by v1->v2
        assert campaign.starts_on is None  # added by v2->v3
