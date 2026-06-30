"""Application tests for the loyalty PaymentRefundedSubscriber (pattern-B ACL)."""

from protean import current_domain

from loyalty.projections.reward_account_view import RewardAccountView
from loyalty.reward.enrollment import EnrollRewardAccount
from loyalty.reward.payments_subscriber import PaymentRefundedSubscriber
from loyalty.reward.points import EarnPoints


def _enroll_with_points(customer_id, points):
    account_id = current_domain.process(EnrollRewardAccount(customer_id=customer_id), asynchronous=False)
    current_domain.process(EarnPoints(account_id=account_id, amount=points, reason="seed"), asynchronous=False)
    return account_id


def _message(event_type, data):
    return {"metadata": {"headers": {"type": event_type}}, "data": data}


def _refund(customer_id, amount, order_id="ord-1"):
    return _message(
        "Payments.RefundCompleted.v1",
        {
            "payment_id": "pay-1",
            "refund_id": "ref-1",
            "order_id": order_id,
            "customer_id": customer_id,
            "amount": amount,
        },
    )


class TestPaymentRefundedSubscriber:
    def test_refund_claws_back_points(self):
        account_id = _enroll_with_points("cust-r1", 200)
        PaymentRefundedSubscriber()(_refund("cust-r1", 60.0))

        view = current_domain.repository_for(RewardAccountView).get(account_id)
        assert view.points_balance == 140

    def test_clawback_clamped_to_balance(self):
        account_id = _enroll_with_points("cust-r2", 30)
        PaymentRefundedSubscriber()(_refund("cust-r2", 100.0))

        view = current_domain.repository_for(RewardAccountView).get(account_id)
        assert view.points_balance == 0

    def test_other_event_types_ignored(self):
        account_id = _enroll_with_points("cust-r3", 80)
        PaymentRefundedSubscriber()(_message("Payments.PaymentSucceeded.v1", {"customer_id": "cust-r3", "amount": 50}))

        view = current_domain.repository_for(RewardAccountView).get(account_id)
        assert view.points_balance == 80

    def test_missing_customer_id_is_a_noop(self):
        PaymentRefundedSubscriber()(_message("Payments.RefundCompleted.v1", {"order_id": "o", "amount": 10}))

    def test_unknown_customer_is_a_noop(self):
        PaymentRefundedSubscriber()(_refund("cust-unknown", 10.0))
