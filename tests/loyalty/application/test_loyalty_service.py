"""Application-service tests — LoyaltyService.transfer_points (@use_case).

Exercises an application service invoked directly (not via domain.process): it loads
two aggregates, runs the TransferPoints domain service, and persists both within the
@use_case UnitOfWork, returning a value synchronously.
"""

from protean import current_domain

from loyalty.projections.reward_account_view import RewardAccountView
from loyalty.reward.enrollment import EnrollRewardAccount
from loyalty.reward.points import EarnPoints
from loyalty.reward.services import LoyaltyService


def _enroll(customer_id):
    return current_domain.process(EnrollRewardAccount(customer_id=customer_id), asynchronous=False)


class TestLoyaltyApplicationService:
    def test_transfer_points_use_case_moves_and_persists(self):
        source_id = _enroll("cust-1")
        current_domain.process(EarnPoints(account_id=source_id, amount=100), asynchronous=False)
        target_id = _enroll("cust-2")

        result = LoyaltyService().transfer_points(source_id, target_id, 40)

        assert result == {"source_balance": 60, "target_balance": 40}

        # Both aggregates persisted and their read models updated.
        source_view = current_domain.repository_for(RewardAccountView).get(source_id)
        target_view = current_domain.repository_for(RewardAccountView).get(target_id)
        assert source_view.points_balance == 60
        assert target_view.points_balance == 40
