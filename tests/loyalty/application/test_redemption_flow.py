"""RedemptionSaga flow tests at the application layer.

The saga's full multi-step logic (reserve → issue → complete, and the compensation branch)
is proven deterministically by the unit tests in
``tests/loyalty/domain/test_redemption_saga.py`` (via ``given`` + mocked dispatch).

Here we verify the saga is correctly *wired* and *starts* against real aggregates: processing
``RequestRedemption`` synchronously fires the start handler, which reserves points on the
RewardAccount and advances the Redemption to ``points_reserved``. The later steps run under the
loyalty engine — like the ordering ``OrderCheckoutSaga``, the process manager is engine-driven.
(Under ``event_processing=sync`` later handlers re-enter before the start transition is
persisted, so the synchronous cascade stops after the reserve step.)
"""

from protean import current_domain

from loyalty.projections.redemption_view import RedemptionView
from loyalty.redemption.commands import RequestRedemption
from loyalty.reward.enrollment import EnrollRewardAccount
from loyalty.reward.points import EarnPoints
from loyalty.reward.reward_account import RewardAccount


def _funded_account(customer_id="cust-redeem", points=500):
    account_id = current_domain.process(EnrollRewardAccount(customer_id=customer_id), asynchronous=False)
    current_domain.process(EarnPoints(account_id=account_id, amount=points, reason="seed"), asynchronous=False)
    return account_id


def _balance(account_id):
    return current_domain.repository_for(RewardAccount).get(account_id).points_balance


def _request(account_id, points, reward_code="GIFT10"):
    return current_domain.process(
        RequestRedemption(account_id=account_id, points=points, reward_code=reward_code),
        asynchronous=False,
    )


def _view(redemption_id):
    return current_domain.repository_for(RedemptionView).get(redemption_id)


class TestRedemptionStart:
    def test_request_reserves_points_on_the_account(self):
        account_id = _funded_account(points=500)
        rid = _request(account_id, points=120)

        # Saga start handler reserved the points (RedeemPoints) and advanced the redemption.
        assert _view(rid).status == "points_reserved"
        assert _balance(account_id) == 380

    def test_request_creates_redemption_projection(self):
        account_id = _funded_account(customer_id="cust-redeem-2", points=300)
        rid = _request(account_id, points=50, reward_code="GIFT5")

        view = _view(rid)
        assert view.account_id == account_id
        assert view.points == 50
        assert view.reward_code == "GIFT5"
