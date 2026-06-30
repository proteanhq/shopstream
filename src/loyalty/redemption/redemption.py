"""Redemption — a state-based aggregate tracking one points-for-voucher redemption.

A redemption moves through a small state machine that the `RedemptionSaga` orchestrates:

    requested → points_reserved → voucher_issued → completed
                              ↘ (voucher unavailable) → compensated

The aggregate only records *what happened* (raising an event per transition); the saga owns
the *decisions* (reserve points, issue the voucher, complete, or compensate by refunding).
"""

from datetime import UTC, datetime

from protean import invariant
from protean.exceptions import ValidationError
from protean.fields import DateTime, Integer, String

from loyalty.domain import loyalty

REDEMPTION_STATUSES = [
    "requested",
    "points_reserved",
    "voucher_issued",
    "completed",
    "compensated",
]


@loyalty.aggregate
class Redemption:
    account_id = String(required=True, max_length=255)
    points = Integer(required=True)
    reward_code = String(required=True, max_length=40)
    status = String(choices=REDEMPTION_STATUSES, default="requested")
    voucher_code = String(max_length=40)
    failure_reason = String(max_length=255)
    requested_at = DateTime(default=lambda: datetime.now(UTC))

    @invariant.post
    def points_must_be_positive(self):
        if self.points <= 0:
            raise ValidationError({"points": ["Redemption points must be positive"]})

    @classmethod
    def request(cls, account_id, points, reward_code):
        from loyalty.redemption.events import RedemptionRequested

        redemption = cls(account_id=account_id, points=points, reward_code=reward_code)
        redemption.raise_(
            RedemptionRequested(
                redemption_id=redemption.id,
                account_id=account_id,
                points=points,
                reward_code=reward_code,
                requested_at=redemption.requested_at,
            )
        )
        return redemption

    def reserve_points(self):
        from loyalty.redemption.events import PointsReserved

        self.status = "points_reserved"
        self.raise_(
            PointsReserved(
                redemption_id=self.id,
                account_id=self.account_id,
                points=self.points,
                reserved_at=datetime.now(UTC),
            )
        )

    def issue_voucher(self, voucher_code):
        from loyalty.redemption.events import VoucherIssued

        self.status = "voucher_issued"
        self.voucher_code = voucher_code
        self.raise_(
            VoucherIssued(
                redemption_id=self.id,
                voucher_code=voucher_code,
                issued_at=datetime.now(UTC),
            )
        )

    def fail_voucher(self, reason):
        from loyalty.redemption.events import VoucherIssuanceFailed

        self.failure_reason = reason
        self.raise_(
            VoucherIssuanceFailed(
                redemption_id=self.id,
                reason=reason,
                failed_at=datetime.now(UTC),
            )
        )

    def complete(self):
        from loyalty.redemption.events import RedemptionCompleted

        self.status = "completed"
        self.raise_(
            RedemptionCompleted(
                redemption_id=self.id,
                voucher_code=self.voucher_code,
                completed_at=datetime.now(UTC),
            )
        )

    def compensate(self, refunded_points, reason):
        from loyalty.redemption.events import RedemptionCompensated

        self.status = "compensated"
        self.failure_reason = reason
        self.raise_(
            RedemptionCompensated(
                redemption_id=self.id,
                refunded_points=refunded_points,
                reason=reason,
                compensated_at=datetime.now(UTC),
            )
        )
