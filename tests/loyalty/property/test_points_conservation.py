"""Property-based tests for loyalty points invariants (Hypothesis).

These assert the laws that must hold for *any* sequence of operations, rather than a few
hand-picked cases: points are conserved, balances never go negative, lifetime points only
grow, and tier is a pure function of lifetime points (and never downgrades).
"""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from protean.exceptions import ValidationError

from loyalty.reward.reward_account import (
    TIERS,
    RewardAccount,
    tier_for_lifetime_points,
)
from loyalty.reward.transfer import TransferPoints

# The autouse `_ctx` fixture (domain context) is function-scoped and shared across all
# Hypothesis examples in a test — intended here, so silence the health check.
_SETTINGS = settings(
    max_examples=200,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)

amounts = st.integers(min_value=1, max_value=10_000)
operations = st.lists(st.tuples(st.sampled_from(["earn", "redeem"]), amounts), max_size=40)


def _account(customer_id="cust-prop"):
    return RewardAccount.enroll(customer_id=customer_id)


class TestSingleAccountConservation:
    @_SETTINGS
    @given(ops=operations)
    def test_balance_and_lifetime_account_for_every_movement(self, ops):
        account = _account()
        earned = 0
        redeemed = 0
        for kind, amount in ops:
            if kind == "earn":
                account.earn_points(amount)
                earned += amount
            elif amount <= account.points_balance:
                account.redeem_points(amount)
                redeemed += amount
            # redeeming more than the balance is rejected by the invariant — skip it.

        assert account.points_balance == earned - redeemed
        assert account.lifetime_points == earned
        assert account.points_balance >= 0
        assert account.lifetime_points >= account.points_balance

    @_SETTINGS
    @given(amount=amounts, extra=st.integers(min_value=1, max_value=10_000))
    def test_over_redemption_is_always_rejected(self, amount, extra):
        account = _account()
        account.earn_points(amount)
        with pytest.raises(ValidationError):
            account.redeem_points(amount + extra)


class TestTierProgression:
    @_SETTINGS
    @given(earns=st.lists(amounts, min_size=1, max_size=25))
    def test_tier_is_a_function_of_lifetime_and_never_downgrades(self, earns):
        account = _account()
        previous_rank = TIERS.index(account.tier)
        for amount in earns:
            account.earn_points(amount)
            rank = TIERS.index(account.tier)
            assert rank >= previous_rank  # monotonic — never downgrades
            previous_rank = rank
        # tier is fully determined by lifetime points
        assert account.tier == tier_for_lifetime_points(account.lifetime_points)


class TestTransferConservation:
    @_SETTINGS
    @given(source_pts=amounts, target_pts=amounts, amount=amounts)
    def test_transfer_conserves_total_or_is_rejected(self, source_pts, target_pts, amount):
        source = _account("cust-src")
        source.earn_points(source_pts)
        target = _account("cust-tgt")
        target.earn_points(target_pts)
        total_before = source.points_balance + target.points_balance

        if amount <= source.points_balance:
            TransferPoints(source, target)(amount)
            assert source.points_balance + target.points_balance == total_before
            assert source.points_balance >= 0
            assert target.points_balance >= 0
        else:
            with pytest.raises(ValidationError):
                TransferPoints(source, target)(amount)
