"""Optimistic-concurrency tests for RewardAccount.

Two readers that load the same account, both mutate it, and both try to persist must not
silently lose an update — the stale writer is rejected with an optimistic-concurrency error.
"""

import pytest
from protean import current_domain
from protean.exceptions import ExpectedVersionError

from loyalty.reward.enrollment import EnrollRewardAccount
from loyalty.reward.points import EarnPoints
from loyalty.reward.reward_account import RewardAccount


def _seed_account(customer_id="cust-conc", points=100):
    account_id = current_domain.process(EnrollRewardAccount(customer_id=customer_id), asynchronous=False)
    current_domain.process(EarnPoints(account_id=account_id, amount=points, reason="seed"), asynchronous=False)
    return account_id


class TestOptimisticConcurrency:
    def test_stale_writer_is_rejected(self):
        account_id = _seed_account(points=100)
        repo = current_domain.repository_for(RewardAccount)

        first = repo.get(account_id)
        second = repo.get(account_id)  # same version as `first`

        first.earn_points(10)
        repo.add(first)  # bumps the stored version

        second.earn_points(20)
        with pytest.raises(ExpectedVersionError):
            repo.add(second)  # stale — must be rejected, not silently overwrite

    def test_winning_write_is_persisted_intact(self):
        account_id = _seed_account(points=100)
        repo = current_domain.repository_for(RewardAccount)

        first = repo.get(account_id)
        second = repo.get(account_id)

        first.earn_points(10)
        repo.add(first)

        second.earn_points(20)
        with pytest.raises(ExpectedVersionError):
            repo.add(second)

        # The first (winning) write survives; the stale write did not corrupt it.
        reloaded = repo.get(account_id)
        assert reloaded.points_balance == 110

    def test_sequential_reload_avoids_the_conflict(self):
        account_id = _seed_account(points=100)
        repo = current_domain.repository_for(RewardAccount)

        first = repo.get(account_id)
        first.earn_points(10)
        repo.add(first)

        # Re-reading picks up the new version, so the second write succeeds.
        second = repo.get(account_id)
        second.earn_points(20)
        repo.add(second)

        assert repo.get(account_id).points_balance == 130
