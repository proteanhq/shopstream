"""RedemptionSaga flow tests at the application layer.

The saga's full multi-step logic (reserve → issue → complete, and the compensation branch) is
proven deterministically by the unit tests in ``tests/loyalty/domain/test_redemption_saga.py``
(via ``given`` + mocked dispatch).

Here we drive the saga against real aggregates. Processing ``RequestRedemption`` synchronously
fires the start handler, which reserves points on the RewardAccount and creates the redemption;
the remaining steps (issue voucher → complete, or compensate on failure) now cascade in the same
synchronous pass. Multi-step process managers cascade under ``event_processing="sync"`` since
proteanhq/protean#1048 was fixed, so the saga runs to a terminal state deterministically.
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
    """Deterministic behaviour: the saga starts, reserves points, and records the redemption."""

    def test_request_reserves_points_on_the_account(self):
        account_id = _funded_account(points=500)
        _request(account_id, points=120)
        # The saga's start handler reserved (spent) the points on the account.
        assert _balance(account_id) == 380

    def test_request_creates_redemption_projection(self):
        account_id = _funded_account(customer_id="cust-redeem-2", points=300)
        rid = _request(account_id, points=50, reward_code="GIFT5")

        view = _view(rid)
        assert view.account_id == account_id
        assert view.points == 50
        assert view.reward_code == "GIFT5"
        # The saga cascades to a terminal state in the same synchronous pass.
        assert view.status == "completed"


class TestRedemptionFullFlow:
    """Full saga completion — cascades synchronously (proteanhq/protean#1048 fixed)."""

    def test_successful_redemption_completes_and_spends_points(self):
        account_id = _funded_account(points=500)
        rid = _request(account_id, points=120, reward_code="GIFT10")

        view = _view(rid)
        assert view.status == "completed"
        assert view.voucher_code and view.voucher_code.startswith("VCHR-")
        assert _balance(account_id) == 380  # points spent, not refunded

    def test_voucher_failure_compensates_and_refunds_points(self):
        account_id = _funded_account(customer_id="cust-redeem-fail", points=500)
        rid = _request(account_id, points=100, reward_code="FAIL-STOCK")

        view = _view(rid)
        assert view.status == "compensated"
        assert _balance(account_id) == 500  # compensation refunded the reserved points
