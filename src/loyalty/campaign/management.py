"""Commands and handler that drive the event-sourced PromoCampaign lifecycle.

These wire the previously-orphaned PromoCampaign aggregate into the domain: launch a
campaign, then move it through draft → active → paused → expired. Handlers are thin —
load (or create) the aggregate, invoke a business method, persist. Because PromoCampaign
is event-sourced, `repository_for(...).add(...)` appends the raised delta events to the
event store (and, with `fact_events=True`, a complete-state fact event after each persist).
"""

from protean import handle
from protean.fields import Date, Identifier, Integer, String
from protean.utils.globals import current_domain

from loyalty.campaign.campaign import PromoCampaign
from loyalty.domain import loyalty


@loyalty.command(part_of="PromoCampaign")
class LaunchCampaign:
    campaign_code = String(required=True, max_length=20)
    name = String(required=True, max_length=255)
    discount_type = String(required=True)
    discount_value = Integer(required=True)
    starts_on = Date()
    ends_on = Date()


@loyalty.command(part_of="PromoCampaign")
class ActivateCampaign:
    campaign_id = Identifier(required=True)


@loyalty.command(part_of="PromoCampaign")
class PauseCampaign:
    campaign_id = Identifier(required=True)
    reason = String(max_length=255)


@loyalty.command(part_of="PromoCampaign")
class ExpireCampaign:
    campaign_id = Identifier(required=True)


@loyalty.command_handler(part_of=PromoCampaign)
class PromoCampaignHandler:
    @handle(LaunchCampaign)
    def launch(self, command: LaunchCampaign):
        campaign = PromoCampaign.launch(
            campaign_code=command.campaign_code,
            name=command.name,
            discount_type=command.discount_type,
            discount_value=command.discount_value,
            starts_on=command.starts_on,
            ends_on=command.ends_on,
        )
        current_domain.repository_for(PromoCampaign).add(campaign)
        return str(campaign.id)

    @handle(ActivateCampaign)
    def activate(self, command: ActivateCampaign):
        repo = current_domain.repository_for(PromoCampaign)
        campaign = repo.get(command.campaign_id)
        campaign.activate()
        repo.add(campaign)

    @handle(PauseCampaign)
    def pause(self, command: PauseCampaign):
        repo = current_domain.repository_for(PromoCampaign)
        campaign = repo.get(command.campaign_id)
        campaign.pause(reason=command.reason)
        repo.add(campaign)

    @handle(ExpireCampaign)
    def expire(self, command: ExpireCampaign):
        repo = current_domain.repository_for(PromoCampaign)
        campaign = repo.get(command.campaign_id)
        campaign.expire()
        repo.add(campaign)
