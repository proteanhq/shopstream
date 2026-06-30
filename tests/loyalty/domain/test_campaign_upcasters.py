"""Unit tests for the CampaignLaunched upcaster chain (v1 -> v2 -> v3)."""

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
