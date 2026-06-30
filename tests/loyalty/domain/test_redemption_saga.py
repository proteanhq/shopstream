"""Domain tests for the RedemptionSaga process manager.

Replays events through the saga with `protean.testing.given` and a mocked
`current_domain.process`, so we can assert both the forward (complete) and the
compensation (refund) branches, plus the commands the saga dispatches.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from protean.exceptions import ValidationError
from protean.testing import given

from loyalty.redemption.commands import (
    CompensateRedemption,
    CompleteRedemption,
    IssueRedemptionVoucher,
    ReserveRedemptionPoints,
)
from loyalty.redemption.events import (
    PointsReserved,
    RedemptionRequested,
    VoucherIssuanceFailed,
    VoucherIssued,
)
from loyalty.reward.points import EarnPoints, RedeemPoints

RID = "red-001"
ACC = "acc-001"


def _requested(points=100, reward_code="GIFT10"):
    return RedemptionRequested(
        redemption_id=RID,
        account_id=ACC,
        points=points,
        reward_code=reward_code,
        requested_at=datetime.now(UTC),
    )


def _reserved(points=100):
    return PointsReserved(redemption_id=RID, account_id=ACC, points=points, reserved_at=datetime.now(UTC))


def _voucher_issued(code="VCHR-ABC123"):
    return VoucherIssued(redemption_id=RID, voucher_code=code, issued_at=datetime.now(UTC))


def _voucher_failed(reason="No vouchers available"):
    return VoucherIssuanceFailed(redemption_id=RID, reason=reason, failed_at=datetime.now(UTC))


def _commands_of(mock_domain, command_cls):
    return [c.args[0] for c in mock_domain.process.call_args_list if isinstance(c.args[0], command_cls)]


class TestForwardFlow:
    @patch("loyalty.redemption.saga.current_domain")
    def test_request_reserves_points_and_advances(self, mock_domain):
        mock_domain.process = MagicMock()
        result = given(_saga(), _requested(points=150))
        assert result.status == "reserving"
        assert result.points == 150
        # Reserved points on the RewardAccount and advanced the Redemption.
        redeems = _commands_of(mock_domain, RedeemPoints)
        assert len(redeems) == 1 and redeems[0].amount == 150
        assert len(_commands_of(mock_domain, ReserveRedemptionPoints)) == 1

    @patch("loyalty.redemption.saga.current_domain")
    def test_points_reserved_issues_voucher(self, mock_domain):
        mock_domain.process = MagicMock()
        result = given(_saga(), _requested(), _reserved())
        assert result.status == "issuing_voucher"
        assert len(_commands_of(mock_domain, IssueRedemptionVoucher)) == 1

    @patch("loyalty.redemption.saga.current_domain")
    def test_voucher_issued_completes_saga(self, mock_domain):
        mock_domain.process = MagicMock()
        result = given(_saga(), _requested(), _reserved(), _voucher_issued(code="VCHR-XYZ"))
        assert result.status == "completed"
        assert result.voucher_code == "VCHR-XYZ"
        assert result.is_complete
        assert len(_commands_of(mock_domain, CompleteRedemption)) == 1


class TestCompensationFlow:
    @patch("loyalty.redemption.saga.current_domain")
    def test_voucher_failure_refunds_points_and_compensates(self, mock_domain):
        mock_domain.process = MagicMock()
        result = given(_saga(), _requested(points=200), _reserved(points=200), _voucher_failed("sold out"))
        assert result.status == "compensated"
        assert result.failure_reason == "sold out"
        assert result.is_complete

        # Compensating action: the reserved points are refunded via EarnPoints.
        refunds = _commands_of(mock_domain, EarnPoints)
        assert len(refunds) == 1 and refunds[0].amount == 200
        comps = _commands_of(mock_domain, CompensateRedemption)
        assert len(comps) == 1 and comps[0].refunded_points == 200


class TestReserveRejected:
    @patch("loyalty.redemption.saga.current_domain")
    def test_insufficient_balance_rejects_without_compensation(self, mock_domain):
        # RedeemPoints (the first dispatch) fails — nothing was deducted, nothing to refund.
        mock_domain.process = MagicMock(side_effect=ValidationError({"points_balance": ["negative"]}))
        result = given(_saga(), _requested())
        assert result.status == "rejected"
        assert result.is_complete
        assert _commands_of(mock_domain, EarnPoints) == []


def _saga():
    from loyalty.redemption.saga import RedemptionSaga

    return RedemptionSaga
