"""CampaignCatalog — a database-backed read model of promotional campaigns.

Projects the event-sourced PromoCampaign's delta events into a flat, queryable catalog.
It is the read side the points-earning flow consults to find an active points-multiplier
campaign (a cross-aggregate read; see loyalty/campaign/multiplier.py), and what the
campaign API lists from.

This projection is bound to loyalty's **second persistence provider** (`provider="reporting"`,
a SQLite store under Postgres; see `domain.toml`) — everything else in the domain uses the
default Postgres provider. It exercises Protean running more than one database engine in a
single domain; `repository_for(CampaignCatalog)` resolves to the reporting provider
transparently, so the projector, queries, and the multiplier read need no special handling.
"""

from datetime import date, datetime

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


@loyalty.projection(provider="reporting")
class CampaignCatalog:
    campaign_id: str = Identifier(identifier=True, required=True)
    campaign_code: str | None = String()
    name: str | None = String()
    discount_type: str | None = String()
    discount_value: int = Integer(default=0)
    status: str | None = String()
    starts_on: date | None = Date()
    ends_on: date | None = Date()
    updated_at: datetime | None = DateTime()


@loyalty.projector(projector_for=CampaignCatalog, aggregates=[PromoCampaign])
class CampaignCatalogProjector:
    @on(CampaignLaunched)
    def on_launched(self, event: CampaignLaunched) -> None:
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
    def on_activated(self, event: CampaignActivated) -> None:
        self._set_status(event.campaign_id, "active", event.activated_at)

    @on(CampaignPaused)
    def on_paused(self, event: CampaignPaused) -> None:
        self._set_status(event.campaign_id, "paused", event.paused_at)

    @on(CampaignExpired)
    def on_expired(self, event: CampaignExpired) -> None:
        self._set_status(event.campaign_id, "expired", event.expired_at)

    def _set_status(self, campaign_id: str, status: str, occurred_at: datetime) -> None:
        repo = current_domain.repository_for(CampaignCatalog)
        entry = repo.get(campaign_id)
        entry.status = status
        entry.updated_at = occurred_at
        repo.add(entry)
