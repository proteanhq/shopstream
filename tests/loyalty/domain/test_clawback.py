"""Domain tests for RewardAccount.claw_back_points (refund reversal)."""

from loyalty.reward.events import PointsRedeemed
from loyalty.reward.reward_account import RewardAccount


def _account(points=0):
    account = RewardAccount.enroll(customer_id="cust-claw")
    if points:
        account.earn_points(points)
    account._events.clear()
    return account


class TestClawBackPoints:
    def test_clawback_deducts_up_to_balance(self):
        account = _account(points=200)
        account.claw_back_points(50)
        assert account.points_balance == 150

    def test_clawback_is_clamped_and_never_negative(self):
        account = _account(points=30)
        account.claw_back_points(100)  # more than balance
        assert account.points_balance == 0  # clamped, not -70

    def test_clawback_records_an_adjust_ledger_entry(self):
        account = _account(points=200)
        account.claw_back_points(40, reason="refund:ord-1")
        entry = account.entries[-1]
        assert entry.entry_type == "adjust"
        assert entry.amount == 40
        assert entry.reason == "refund:ord-1"

    def test_clawback_raises_points_redeemed(self):
        account = _account(points=200)
        account.claw_back_points(40)
        assert any(isinstance(e, PointsRedeemed) for e in account._events)

    def test_clawback_does_not_touch_lifetime_points(self):
        account = _account(points=200)
        account.claw_back_points(40)
        assert account.lifetime_points == 200  # lifetime is never reduced

    def test_zero_balance_clawback_is_a_noop(self):
        account = _account(points=0)
        account.claw_back_points(50)
        assert account.points_balance == 0
        assert account._events == []
