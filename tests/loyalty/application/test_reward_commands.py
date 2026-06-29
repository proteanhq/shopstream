"""Application tests for RewardAccount commands — full CQRS pipeline.

Processes commands through the handlers and asserts both the persisted aggregate and
the read models, including the cache-backed PointsLeaderboard projection.
"""

from protean import current_domain

from loyalty.projections.points_leaderboard import PointsLeaderboard
from loyalty.projections.reward_account_view import RewardAccountView
from loyalty.reward.enrollment import EnrollRewardAccount
from loyalty.reward.points import EarnPoints, RedeemPoints
from loyalty.reward.reward_account import RewardAccount


def _enroll(customer_id="cust-1"):
    return current_domain.process(EnrollRewardAccount(customer_id=customer_id), asynchronous=False)


class TestRewardCommands:
    def test_enroll_persists_account_and_both_projections(self):
        account_id = _enroll()

        account = current_domain.repository_for(RewardAccount).get(account_id)
        assert account.customer_id == "cust-1"
        assert account.points_balance == 0

        view = current_domain.repository_for(RewardAccountView).get(account_id)
        assert view.points_balance == 0
        assert view.status == "Active"

        # cache-backed projection (read via cache_for)
        entry = current_domain.view_for(PointsLeaderboard).get(account_id)
        assert entry.points_balance == 0
        assert entry.customer_id == "cust-1"

    def test_earn_updates_aggregate_db_view_and_cache(self):
        account_id = _enroll()
        current_domain.process(EarnPoints(account_id=account_id, amount=120), asynchronous=False)

        account = current_domain.repository_for(RewardAccount).get(account_id)
        assert account.points_balance == 120

        view = current_domain.repository_for(RewardAccountView).get(account_id)
        assert view.points_balance == 120
        assert view.lifetime_points == 120

        entry = current_domain.view_for(PointsLeaderboard).get(account_id)
        assert entry.points_balance == 120

    def test_redeem_updates_balance_but_not_lifetime(self):
        account_id = _enroll()
        current_domain.process(EarnPoints(account_id=account_id, amount=120), asynchronous=False)
        current_domain.process(RedeemPoints(account_id=account_id, amount=50), asynchronous=False)

        view = current_domain.repository_for(RewardAccountView).get(account_id)
        assert view.points_balance == 70
        assert view.lifetime_points == 120

        entry = current_domain.view_for(PointsLeaderboard).get(account_id)
        assert entry.points_balance == 70
