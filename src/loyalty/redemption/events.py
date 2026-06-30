"""Domain events for the Redemption aggregate.

Every event carries ``redemption_id`` — the value the `RedemptionSaga` correlates on
(via a dict ``correlate`` spec) as it drives the redemption through its lifecycle.
"""

from protean.fields import DateTime, Integer, String

from loyalty.domain import loyalty


@loyalty.event(part_of="Redemption")
class RedemptionRequested:
    redemption_id = String(required=True)
    account_id = String(required=True)
    points = Integer(required=True)
    reward_code = String(required=True)
    requested_at = DateTime(required=True)


@loyalty.event(part_of="Redemption")
class PointsReserved:
    redemption_id = String(required=True)
    account_id = String(required=True)
    points = Integer(required=True)
    reserved_at = DateTime(required=True)


@loyalty.event(part_of="Redemption")
class VoucherIssued:
    redemption_id = String(required=True)
    voucher_code = String(required=True)
    issued_at = DateTime(required=True)


@loyalty.event(part_of="Redemption")
class VoucherIssuanceFailed:
    redemption_id = String(required=True)
    reason = String(required=True)
    failed_at = DateTime(required=True)


@loyalty.event(part_of="Redemption")
class RedemptionCompleted:
    redemption_id = String(required=True)
    voucher_code = String(required=True)
    completed_at = DateTime(required=True)


@loyalty.event(part_of="Redemption")
class RedemptionCompensated:
    redemption_id = String(required=True)
    refunded_points = Integer(required=True)
    reason = String(required=True)
    compensated_at = DateTime(required=True)
