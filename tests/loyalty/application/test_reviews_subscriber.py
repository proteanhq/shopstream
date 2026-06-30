"""Application tests for the loyalty ReviewApprovedSubscriber (pattern-B ACL) and the
TierUpgraded projection update."""

from protean import current_domain

from loyalty.projections.reward_account_view import RewardAccountView
from loyalty.reward.enrollment import EnrollRewardAccount
from loyalty.reward.points import EarnPoints
from loyalty.reward.reviews_subscriber import (
    REVIEW_BONUS_POINTS,
    ReviewApprovedSubscriber,
)


def _enroll(customer_id):
    return current_domain.process(EnrollRewardAccount(customer_id=customer_id), asynchronous=False)


def _message(event_type, data):
    return {"metadata": {"headers": {"type": event_type}}, "data": data}


class TestReviewApprovedSubscriber:
    def test_approval_awards_bonus_to_existing_account(self):
        account_id = _enroll("cust-rev-1")

        ReviewApprovedSubscriber()(
            _message(
                "Reviews.ReviewApproved.v1",
                {"review_id": "rev-1", "product_id": "prod-1", "customer_id": "cust-rev-1"},
            )
        )

        view = current_domain.repository_for(RewardAccountView).get(account_id)
        assert view.points_balance == REVIEW_BONUS_POINTS

    def test_other_event_types_are_ignored(self):
        account_id = _enroll("cust-rev-2")

        ReviewApprovedSubscriber()(_message("Reviews.ReviewRejected.v1", {"customer_id": "cust-rev-2"}))

        view = current_domain.repository_for(RewardAccountView).get(account_id)
        assert view.points_balance == 0

    def test_no_account_for_customer_is_a_noop(self):
        # Should not raise even when the customer has no reward account.
        ReviewApprovedSubscriber()(
            _message("Reviews.ReviewApproved.v1", {"customer_id": "cust-unknown", "review_id": "r9"})
        )


class TestTierUpgradeProjection:
    def test_earning_past_threshold_updates_view_tier(self):
        account_id = _enroll("cust-rev-tier")
        current_domain.process(EarnPoints(account_id=account_id, amount=1_500, reason="order"), asynchronous=False)

        view = current_domain.repository_for(RewardAccountView).get(account_id)
        assert view.tier == "silver"
        assert view.lifetime_points == 1_500
