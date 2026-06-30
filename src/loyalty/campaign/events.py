"""Domain events for the event-sourced PromoCampaign aggregate."""

from protean.fields import Date, DateTime, Integer, String

from loyalty.domain import loyalty


@loyalty.event(part_of="PromoCampaign")
class CampaignLaunched:
    # Schema has evolved twice; see loyalty/campaign/upcasters.py for the v1->v2->v3 chain.
    __version__ = 3

    campaign_id = String(required=True)
    campaign_code = String(required=True)
    name = String(required=True)
    discount_type = String(required=True)
    discount_value = Integer(required=True)
    starts_on = Date()
    ends_on = Date()
    launched_at = DateTime(required=True)


@loyalty.event(part_of="PromoCampaign")
class CampaignActivated:
    campaign_id = String(required=True)
    activated_at = DateTime(required=True)


@loyalty.event(part_of="PromoCampaign")
class CampaignPaused:
    campaign_id = String(required=True)
    reason = String()
    paused_at = DateTime(required=True)


@loyalty.event(part_of="PromoCampaign")
class CampaignExpired:
    campaign_id = String(required=True)
    expired_at = DateTime(required=True)
