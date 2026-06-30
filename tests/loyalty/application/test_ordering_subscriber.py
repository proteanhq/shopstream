"""Application tests for the loyalty OrderDeliveredSubscriber (pattern-B ACL)."""

from protean import current_domain

from loyalty.projections.reward_account_view import RewardAccountView
from loyalty.reward.enrollment import EnrollRewardAccount
from loyalty.reward.ordering_subscriber import (
    DELIVERY_BONUS_POINTS,
    OrderDeliveredSubscriber,
)


def _enroll(customer_id):
    return current_domain.process(EnrollRewardAccount(customer_id=customer_id), asynchronous=False)


def _message(event_type, data):
    return {"metadata": {"headers": {"type": event_type}}, "data": data}


class TestOrderDeliveredSubscriber:
    def test_delivery_awards_bonus_to_existing_account(self):
        account_id = _enroll("cust-1")

        OrderDeliveredSubscriber()(
            _message(
                "Ordering.OrderDelivered.v1",
                {"order_id": "ord-1", "customer_id": "cust-1"},
            )
        )

        view = current_domain.repository_for(RewardAccountView).get(account_id)
        assert view.points_balance == DELIVERY_BONUS_POINTS

    def test_other_event_types_are_ignored(self):
        account_id = _enroll("cust-1")

        OrderDeliveredSubscriber()(_message("Ordering.OrderShipped.v1", {"customer_id": "cust-1"}))

        view = current_domain.repository_for(RewardAccountView).get(account_id)
        assert view.points_balance == 0

    def test_no_account_for_customer_is_a_noop(self):
        # Should not raise even when the customer has no reward account.
        OrderDeliveredSubscriber()(
            _message(
                "Ordering.OrderDelivered.v1",
                {"order_id": "ord-9", "customer_id": "cust-unknown"},
            )
        )
