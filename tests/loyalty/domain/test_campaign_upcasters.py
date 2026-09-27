"""Unit tests for the CampaignLaunched upcaster chain (v1 -> v2 -> v3)."""

from loyalty.campaign.events import CampaignLaunched
from loyalty.campaign.upcasters import (
    UpcastCampaignLaunchedV1ToV2,
    UpcastCampaignLaunchedV2ToV3,
)


class TestCampaignLaunchedUpcasters:
    def test_v1_to_v2_renames_discount_and_adds_type(self):
        result = UpcastCampaignLaunchedV1ToV2().upcast({"campaign_code": "LEGACY15", "discount_pct": 15})
        assert result["discount_value"] == 15
        assert result["discount_type"] == "percentage"
        assert "discount_pct" not in result

    def test_v2_to_v3_adds_schedule_fields(self):
        result = UpcastCampaignLaunchedV2ToV3().upcast(
            {"campaign_code": "X", "discount_value": 15, "discount_type": "percentage"}
        )
        assert result["starts_on"] is None
        assert result["ends_on"] is None


class TestUpcasterEventTypeForms:
    """Loyalty keeps one upcaster per ``event_type`` form so both stay exercised on replay."""

    def test_v1_to_v2_names_its_event_as_a_string(self):
        assert UpcastCampaignLaunchedV1ToV2.meta_.event_type == "CampaignLaunched"

    def test_v2_to_v3_names_its_event_as_a_class(self):
        assert UpcastCampaignLaunchedV2ToV3.meta_.event_type is CampaignLaunched
