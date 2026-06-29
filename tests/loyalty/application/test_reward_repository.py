"""Application tests for the custom RewardAccountRepository (Q / F / lookups)."""

import pytest
from protean import current_domain

from loyalty.reward.enrollment import EnrollRewardAccount
from loyalty.reward.points import EarnPoints, RedeemPoints
from loyalty.reward.reward_account import RewardAccount


def _enroll(customer_id):
    return current_domain.process(EnrollRewardAccount(customer_id=customer_id), asynchronous=False)


def _earn(account_id, amount):
    current_domain.process(EarnPoints(account_id=account_id, amount=amount), asynchronous=False)


def _redeem(account_id, amount):
    current_domain.process(RedeemPoints(account_id=account_id, amount=amount), asynchronous=False)


@pytest.fixture
def accounts():
    high = _enroll("cust-high")
    _earn(high, 500)
    mid = _enroll("cust-mid")
    _earn(mid, 100)
    _redeem(mid, 30)  # balance 70, lifetime 100 -> has redeemed
    zero = _enroll("cust-zero")  # balance 0, lifetime 0 -> never redeemed
    return {"high": high, "mid": mid, "zero": zero}


class TestRewardAccountRepository:
    def test_repository_for_returns_custom_repository(self):
        repo = current_domain.repository_for(RewardAccount)
        assert hasattr(repo, "top_savers")
        assert hasattr(repo, "add")  # inherits default methods

    def test_top_savers_orders_by_balance_desc(self, accounts):
        repo = current_domain.repository_for(RewardAccount)
        top = repo.top_savers(limit=2)
        assert [a.id for a in top] == [accounts["high"], accounts["mid"]]

    def test_never_redeemed_uses_F_expression(self, accounts):
        repo = current_domain.repository_for(RewardAccount)
        ids = {a.id for a in repo.never_redeemed()}
        assert accounts["high"] in ids  # 500 == 500
        assert accounts["zero"] in ids  # 0 == 0
        assert accounts["mid"] not in ids  # 70 != 100 (redeemed)

    def test_eligible_for_promo_combines_Q_or(self, accounts):
        repo = current_domain.repository_for(RewardAccount)
        # No bronze in tiers, so only the >= 200 balance branch matches.
        eligible = {a.id for a in repo.eligible_for_promo(tiers=["gold"], min_balance=200)}
        assert eligible == {accounts["high"]}

        # All accounts are bronze, so the tier branch matches everyone.
        everyone = {a.id for a in repo.eligible_for_promo(tiers=["bronze"], min_balance=10_000)}
        assert everyone == set(accounts.values())
