"""Domain tests for the event-sourced PromoCampaign aggregate."""

import pytest
from protean.exceptions import ValidationError

from loyalty.campaign.campaign import PromoCampaign
from loyalty.campaign.events import CampaignActivated, CampaignLaunched


def _launch(code="SUMMER10"):
    return PromoCampaign.launch(
        campaign_code=code,
        name="Summer Sale",
        discount_type="percentage",
        discount_value=10,
    )


class TestPromoCampaignBehavior:
    def test_launch_creates_draft_and_raises_event(self):
        campaign = _launch()
        assert campaign.campaign_code == "SUMMER10"
        assert campaign.discount_type == "percentage"
        assert campaign.status == "draft"
        assert len(campaign._events) == 1
        assert isinstance(campaign._events[0], CampaignLaunched)

    def test_apply_rebuilds_state_through_lifecycle(self):
        campaign = _launch()
        campaign.activate()
        assert campaign.status == "active"
        assert isinstance(campaign._events[-1], CampaignActivated)
        campaign.pause(reason="budget")
        assert campaign.status == "paused"
        campaign.activate()  # paused -> active again
        assert campaign.status == "active"
        campaign.expire()
        assert campaign.status == "expired"

    def test_cannot_pause_a_draft_campaign(self):
        campaign = _launch()
        with pytest.raises(ValidationError, match="active campaign"):
            campaign.pause()

    def test_cannot_activate_an_expired_campaign(self):
        campaign = _launch()
        campaign.expire()
        with pytest.raises(ValidationError, match="Cannot activate"):
            campaign.activate()
