"""BDD steps for the event-sourced PromoCampaign lifecycle."""

from protean.exceptions import ValidationError
from pytest_bdd import scenarios, when

from loyalty.campaign.campaign import PromoCampaign

scenarios("features/campaign_lifecycle.feature")


@when("a campaign is launched", target_fixture="campaign")
def launch():
    return PromoCampaign.launch(
        campaign_code="BDDLAUNCH",
        name="BDD Launch",
        discount_type="percentage",
        discount_value=10,
    )


@when("the campaign is activated")
def activate(campaign, error):
    try:
        campaign.activate()
    except ValidationError as exc:
        error["exc"] = exc


@when("the campaign is paused")
def pause(campaign, error):
    try:
        campaign.pause()
    except ValidationError as exc:
        error["exc"] = exc


@when("the campaign is expired")
def expire(campaign, error):
    try:
        campaign.expire()
    except ValidationError as exc:
        error["exc"] = exc
