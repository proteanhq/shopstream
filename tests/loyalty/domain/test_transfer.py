"""Domain tests for the TransferPoints domain service (pure, no DB)."""

import pytest
from protean.exceptions import ValidationError

from loyalty.reward.reward_account import RewardAccount
from loyalty.reward.transfer import TransferPoints


def _funded(customer_id, points):
    account = RewardAccount.enroll(customer_id=customer_id)
    if points:
        account.earn_points(points)
    return account


class TestTransferPoints:
    def test_transfer_moves_points_between_accounts(self):
        source = _funded("cust-1", 100)
        target = _funded("cust-2", 0)

        TransferPoints(source, target)(40)

        assert source.points_balance == 60
        assert target.points_balance == 40
        # total conserved
        assert source.points_balance + target.points_balance == 100

    def test_transfer_over_balance_is_rejected(self):
        source = _funded("cust-1", 30)
        target = _funded("cust-2", 0)
        with pytest.raises(ValidationError):
            TransferPoints(source, target)(50)

    def test_transfer_requires_both_accounts_active(self):
        source = _funded("cust-1", 100)
        target = _funded("cust-2", 0)
        target.close()
        with pytest.raises(ValidationError, match="active"):
            TransferPoints(source, target)(10)

    def test_transfer_amount_must_be_positive(self):
        source = _funded("cust-1", 100)
        target = _funded("cust-2", 0)
        with pytest.raises(ValidationError, match="positive"):
            TransferPoints(source, target)(0)
