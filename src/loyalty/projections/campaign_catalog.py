"""CampaignCatalog — a database-backed read model of promotional campaigns.

Projects the event-sourced PromoCampaign's delta events into a flat, queryable catalog.
It is the read side the points-earning flow consults to find an active points-multiplier
campaign (a cross-aggregate read; see loyalty/campaign/multiplier.py), and what the
campaign API lists from.
"""

from protean.core.projector import on
from protean.fields import Date, DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from loyalty.campaign.campaign import PromoCampaign
from loyalty.campaign.events import (
    CampaignActivated,
    CampaignExpired,
    CampaignLaunched,
    CampaignPaused,
)
from loyalty.domain import loyalty


@loyalty.projection
class CampaignCatalog:
    campaign_id = Identifier(identifier=True, required=True)
    campaign_code = String()
    name = String()
    discount_type = String()
    discount_value = Integer(default=0)
    status = String()
    starts_on = Date()
    ends_on = Date()
    updated_at = DateTime()


@loyalty.projector(projector_for=CampaignCatalog, aggregates=[PromoCampaign])
class CampaignCatalogProjector:
    @on(CampaignLaunched)
    def on_launched(self, event):
        current_domain.repository_for(CampaignCatalog).add(
            CampaignCatalog(
                campaign_id=event.campaign_id,
                campaign_code=event.campaign_code,
                name=event.name,
                discount_type=event.discount_type,
                discount_value=event.discount_value,
                status="draft",
                starts_on=event.starts_on,
                ends_on=event.ends_on,
                updated_at=event.launched_at,
            )
        )

    @on(CampaignActivated)
    def on_activated(self, event):
        self._set_status(event.campaign_id, "active", event.activated_at)

    @on(CampaignPaused)
    def on_paused(self, event):
        self._set_status(event.campaign_id, "paused", event.paused_at)

    @on(CampaignExpired)
    def on_expired(self, event):
        self._set_status(event.campaign_id, "expired", event.expired_at)

    def _set_status(self, campaign_id, status, occurred_at):
        repo = current_domain.repository_for(CampaignCatalog)
        entry = repo.get(campaign_id)
        entry.status = status
        entry.updated_at = occurred_at
        repo.add(entry)
