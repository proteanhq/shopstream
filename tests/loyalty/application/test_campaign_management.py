"""Application tests for the PromoCampaign command handlers, CampaignCatalog projection,
and the active-campaign points multiplier applied during earning (a cross-aggregate read).
"""

from datetime import date, timedelta

import pytest
from protean import current_domain
from protean.exceptions import ValidationError

from loyalty.campaign.management import (
    ActivateCampaign,
    ExpireCampaign,
    LaunchCampaign,
    PauseCampaign,
)
from loyalty.projections.campaign_catalog import CampaignCatalog
from loyalty.reward.enrollment import EnrollRewardAccount
from loyalty.reward.points import EarnPoints


def _launch(code="SUMMER10", discount_type="percentage", discount_value=10, **kw):
    return current_domain.process(
        LaunchCampaign(
            campaign_code=code,
            name="Summer Sale",
            discount_type=discount_type,
            discount_value=discount_value,
            **kw,
        ),
        asynchronous=False,
    )


def _catalog(campaign_id):
    return current_domain.repository_for(CampaignCatalog).get(campaign_id)


class TestCampaignCommandHandlers:
    def test_launch_creates_draft_catalog_entry(self):
        campaign_id = _launch()
        entry = _catalog(campaign_id)
        assert entry.status == "draft"
        assert entry.campaign_code == "SUMMER10"
        assert entry.discount_value == 10

    def test_activate_pause_expire_transitions_catalog(self):
        campaign_id = _launch()

        current_domain.process(ActivateCampaign(campaign_id=campaign_id), asynchronous=False)
        assert _catalog(campaign_id).status == "active"

        current_domain.process(PauseCampaign(campaign_id=campaign_id, reason="budget"), asynchronous=False)
        assert _catalog(campaign_id).status == "paused"

        current_domain.process(ExpireCampaign(campaign_id=campaign_id), asynchronous=False)
        assert _catalog(campaign_id).status == "expired"

    def test_invalid_transition_is_rejected(self):
        campaign_id = _launch()  # draft
        with pytest.raises(ValidationError, match="active campaign"):
            current_domain.process(PauseCampaign(campaign_id=campaign_id), asynchronous=False)


class TestPointsMultiplier:
    def _enroll(self, customer_id="cust-mult"):
        return current_domain.process(EnrollRewardAccount(customer_id=customer_id), asynchronous=False)

    def _earn(self, account_id, amount):
        current_domain.process(EarnPoints(account_id=account_id, amount=amount, reason="order"), asynchronous=False)

    def _balance(self, account_id):
        from loyalty.reward.reward_account import RewardAccount

        return current_domain.repository_for(RewardAccount).get(account_id).points_balance

    def test_no_active_campaign_earns_face_value(self):
        account_id = self._enroll()
        self._earn(account_id, 100)
        assert self._balance(account_id) == 100

    def test_active_points_multiplier_boosts_earnings(self):
        account_id = self._enroll()
        campaign_id = _launch(code="DOUBLE", discount_type="points_multiplier", discount_value=2)
        current_domain.process(ActivateCampaign(campaign_id=campaign_id), asynchronous=False)

        self._earn(account_id, 100)
        assert self._balance(account_id) == 200

    def test_only_active_campaign_applies(self):
        account_id = self._enroll()
        campaign_id = _launch(code="TRIPLE", discount_type="points_multiplier", discount_value=3)
        # Still draft — not active — so no boost.
        self._earn(account_id, 100)
        assert self._balance(account_id) == 100

        current_domain.process(ActivateCampaign(campaign_id=campaign_id), asynchronous=False)
        self._earn(account_id, 100)  # now x3
        assert self._balance(account_id) == 100 + 300

    def test_highest_multiplier_wins(self):
        account_id = self._enroll()
        for code, value in [("X2", 2), ("X5", 5)]:
            cid = _launch(code=code, discount_type="points_multiplier", discount_value=value)
            current_domain.process(ActivateCampaign(campaign_id=cid), asynchronous=False)

        self._earn(account_id, 10)
        assert self._balance(account_id) == 50

    def test_non_multiplier_campaign_does_not_boost(self):
        account_id = self._enroll()
        cid = _launch(code="PCT", discount_type="percentage", discount_value=25)
        current_domain.process(ActivateCampaign(campaign_id=cid), asynchronous=False)

        self._earn(account_id, 100)
        assert self._balance(account_id) == 100

    def test_expired_window_does_not_boost(self):
        account_id = self._enroll()
        yesterday = date.today() - timedelta(days=1)
        cid = _launch(
            code="PAST",
            discount_type="points_multiplier",
            discount_value=4,
            starts_on=yesterday - timedelta(days=5),
            ends_on=yesterday,
        )
        current_domain.process(ActivateCampaign(campaign_id=cid), asynchronous=False)

        self._earn(account_id, 100)
        assert self._balance(account_id) == 100

    def test_current_window_boosts(self):
        account_id = self._enroll()
        today = date.today()
        cid = _launch(
            code="NOW",
            discount_type="points_multiplier",
            discount_value=4,
            starts_on=today - timedelta(days=1),
            ends_on=today + timedelta(days=1),
        )
        current_domain.process(ActivateCampaign(campaign_id=cid), asynchronous=False)

        self._earn(account_id, 100)
        assert self._balance(account_id) == 400
