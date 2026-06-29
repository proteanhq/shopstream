"""PromoCampaign — an event-sourced aggregate.

State is rebuilt by replaying events through @apply handlers. `fact_events=True` makes
Protean auto-generate a complete-state fact event after each persist (Event-Carried State
Transfer), in addition to the delta events raised by business methods.

This is the only event-sourced aggregate in the loyalty domain and the only place in
ShopStream that uses fact events.
"""

from datetime import UTC, datetime

from protean import apply
from protean.exceptions import ValidationError
from protean.fields import Date, DateTime, Integer, String

from loyalty.campaign.events import (
    CampaignActivated,
    CampaignExpired,
    CampaignLaunched,
    CampaignPaused,
)
from loyalty.domain import loyalty

DISCOUNT_TYPES = ["percentage", "fixed", "points_multiplier"]
CAMPAIGN_STATUSES = ["draft", "active", "paused", "expired"]


@loyalty.aggregate(is_event_sourced=True, fact_events=True)
class PromoCampaign:
    campaign_code = String(required=True, max_length=20)
    name = String(required=True, max_length=255)
    discount_type = String(choices=DISCOUNT_TYPES, required=True)
    discount_value = Integer(required=True)
    status = String(choices=CAMPAIGN_STATUSES, default="draft")
    starts_on = Date()
    ends_on = Date()
    launched_at = DateTime()

    @classmethod
    def launch(cls, campaign_code, name, discount_type, discount_value, starts_on=None, ends_on=None):
        campaign = cls._create_new()
        campaign.raise_(
            CampaignLaunched(
                campaign_id=str(campaign.id),
                campaign_code=campaign_code,
                name=name,
                discount_type=discount_type,
                discount_value=discount_value,
                starts_on=starts_on,
                ends_on=ends_on,
                launched_at=datetime.now(UTC),
            )
        )
        return campaign

    def activate(self):
        if self.status not in ("draft", "paused"):
            raise ValidationError({"status": [f"Cannot activate a {self.status} campaign"]})
        self.raise_(CampaignActivated(campaign_id=str(self.id), activated_at=datetime.now(UTC)))

    def pause(self, reason=None):
        if self.status != "active":
            raise ValidationError({"status": ["Only an active campaign can be paused"]})
        self.raise_(CampaignPaused(campaign_id=str(self.id), reason=reason, paused_at=datetime.now(UTC)))

    def expire(self):
        if self.status == "expired":
            raise ValidationError({"status": ["Campaign already expired"]})
        self.raise_(CampaignExpired(campaign_id=str(self.id), expired_at=datetime.now(UTC)))

    # -- @apply handlers: rebuild state during replay ----------------------
    @apply
    def _on_launched(self, event: CampaignLaunched):
        self.id = event.campaign_id
        self.campaign_code = event.campaign_code
        self.name = event.name
        self.discount_type = event.discount_type
        self.discount_value = event.discount_value
        self.status = "draft"
        self.starts_on = event.starts_on
        self.ends_on = event.ends_on
        self.launched_at = event.launched_at

    @apply
    def _on_activated(self, event: CampaignActivated):  # noqa: ARG002
        self.status = "active"

    @apply
    def _on_paused(self, event: CampaignPaused):  # noqa: ARG002
        self.status = "paused"

    @apply
    def _on_expired(self, event: CampaignExpired):  # noqa: ARG002
        self.status = "expired"
