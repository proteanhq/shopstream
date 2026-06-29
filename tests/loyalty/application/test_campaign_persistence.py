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
