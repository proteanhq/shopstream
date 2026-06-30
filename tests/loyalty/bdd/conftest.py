"""Shared BDD fixtures and step definitions for the Loyalty domain."""

import pytest
from pytest_bdd import given, parsers, then

from loyalty.campaign.campaign import PromoCampaign
from loyalty.campaign.events import (
    CampaignActivated,
    CampaignExpired,
    CampaignLaunched,
    CampaignPaused,
)
from loyalty.redemption.events import (
    PointsReserved,
    RedemptionCompensated,
    RedemptionCompleted,
    RedemptionRequested,
    VoucherIssuanceFailed,
    VoucherIssued,
)
from loyalty.redemption.redemption import Redemption
from loyalty.reward.events import (
    MembershipCardIssued,
    PointsEarned,
    PointsRedeemed,
    RewardAccountClosed,
    RewardAccountEnrolled,
    TierUpgraded,
)
from loyalty.reward.reward_account import RewardAccount

_EVENT_CLASSES = {
    cls.__name__: cls
    for cls in (
        RewardAccountEnrolled,
        PointsEarned,
        PointsRedeemed,
        TierUpgraded,
        MembershipCardIssued,
        RewardAccountClosed,
        CampaignLaunched,
        CampaignActivated,
        CampaignPaused,
        CampaignExpired,
        RedemptionRequested,
        PointsReserved,
        VoucherIssued,
        VoucherIssuanceFailed,
        RedemptionCompleted,
        RedemptionCompensated,
    )
}


@pytest.fixture()
def error():
    """Container for a captured validation error."""
    return {"exc": None}


# ---------------------------------------------------------------------------
# Given steps (shared)
# ---------------------------------------------------------------------------
@given("an enrolled reward account", target_fixture="account")
def enrolled_account():
    account = RewardAccount.enroll(customer_id="cust-bdd")
    account._events.clear()
    return account


@given(parsers.cfparse("an enrolled reward account with {points:d} points"), target_fixture="account")
def enrolled_account_with_points(points):
    account = RewardAccount.enroll(customer_id="cust-bdd")
    account.earn_points(points)
    account._events.clear()
    return account


@given("a draft promo campaign", target_fixture="campaign")
def draft_campaign():
    campaign = PromoCampaign.launch(
        campaign_code="BDD10",
        name="BDD Campaign",
        discount_type="points_multiplier",
        discount_value=2,
    )
    campaign._events.clear()
    return campaign


@given("a requested redemption", target_fixture="redemption")
def requested_redemption():
    redemption = Redemption.request(account_id="acc-bdd", points=100, reward_code="GIFT10")
    redemption._events.clear()
    return redemption


# ---------------------------------------------------------------------------
# Then steps (shared)
# ---------------------------------------------------------------------------
@then(parsers.cfparse('the account status is "{status}"'))
def account_status_is(account, status):
    assert account.status == status


@then(parsers.cfparse('the account tier is "{tier}"'))
def account_tier_is(account, tier):
    assert account.tier == tier


@then(parsers.cfparse("the points balance is {balance:d}"))
def points_balance_is(account, balance):
    assert account.points_balance == balance


@then(parsers.cfparse("the lifetime points is {lifetime:d}"))
def lifetime_points_is(account, lifetime):
    assert account.lifetime_points == lifetime


@then(parsers.cfparse('the campaign status is "{status}"'))
def campaign_status_is(campaign, status):
    assert campaign.status == status


@then(parsers.cfparse('the redemption status is "{status}"'))
def redemption_status_is(redemption, status):
    assert redemption.status == status


@then("the action fails with a validation error")
def action_fails(error):
    from protean.exceptions import ValidationError

    assert error["exc"] is not None, "Expected a validation error but none was raised"
    assert isinstance(error["exc"], ValidationError)


@then(parsers.cfparse("a {event_type} event is raised"))
def event_is_raised(request, event_type):
    # The aggregate fixture is whichever one the scenario used.
    holder = None
    for name in ("account", "campaign", "redemption"):
        try:
            holder = request.getfixturevalue(name)
            break
        except pytest.FixtureLookupError:
            continue
    assert holder is not None, "No aggregate fixture available"
    event_cls = _EVENT_CLASSES[event_type]
    assert any(isinstance(e, event_cls) for e in holder._events), (
        f"No {event_type} event. Events: {[type(e).__name__ for e in holder._events]}"
    )
