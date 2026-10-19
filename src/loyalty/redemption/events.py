"""Domain events for the Redemption aggregate.

Every event carries ``redemption_id`` — the value the `RedemptionSaga` correlates on
(via a dict ``correlate`` spec) as it drives the redemption through its lifecycle.
"""

from datetime import datetime

from protean.fields import DateTime, Integer, String

from loyalty.domain import loyalty


@loyalty.event(part_of="Redemption")
class RedemptionRequested:
    redemption_id: str = String(required=True)
    account_id: str = String(required=True)
    points: int = Integer(required=True)
    reward_code: str = String(required=True)
    requested_at: datetime = DateTime(required=True)


@loyalty.event(part_of="Redemption")
class PointsReserved:
    redemption_id: str = String(required=True)
    account_id: str = String(required=True)
    points: int = Integer(required=True)
    reserved_at: datetime = DateTime(required=True)


@loyalty.event(part_of="Redemption")
class VoucherIssued:
    redemption_id: str = String(required=True)
    voucher_code: str = String(required=True)
    issued_at: datetime = DateTime(required=True)


@loyalty.event(part_of="Redemption")
class VoucherIssuanceFailed:
    redemption_id: str = String(required=True)
    reason: str = String(required=True)
    failed_at: datetime = DateTime(required=True)


@loyalty.event(part_of="Redemption")
class RedemptionCompleted:
    redemption_id: str = String(required=True)
    voucher_code: str = String(required=True)
    completed_at: datetime = DateTime(required=True)


@loyalty.event(part_of="Redemption")
class RedemptionCompensated:
    redemption_id: str = String(required=True)
    refunded_points: int = Integer(required=True)
    reason: str = String(required=True)
    compensated_at: datetime = DateTime(required=True)
