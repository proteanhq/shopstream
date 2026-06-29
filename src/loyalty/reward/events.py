"""Domain events for the RewardAccount aggregate (delta events, versioned)."""

from protean.fields import DateTime, Integer, String

from loyalty.domain import loyalty


@loyalty.event(part_of="RewardAccount")
class RewardAccountEnrolled:
    account_id = String(required=True)
    customer_id = String(required=True)
    member_code = String(required=True)
    tier = String(required=True)
    enrolled_at = DateTime(required=True)


@loyalty.event(part_of="RewardAccount")
class PointsEarned:
    account_id = String(required=True)
    amount = Integer(required=True)
    balance_after = Integer(required=True)
    reason = String()
    occurred_at = DateTime(required=True)


@loyalty.event(part_of="RewardAccount")
class PointsRedeemed:
    account_id = String(required=True)
    amount = Integer(required=True)
    balance_after = Integer(required=True)
    reason = String()
    occurred_at = DateTime(required=True)


@loyalty.event(part_of="RewardAccount")
class MembershipCardIssued:
    account_id = String(required=True)
    card_number = String(required=True)
    issued_on = String(required=True)


@loyalty.event(part_of="RewardAccount")
class RewardAccountClosed:
    account_id = String(required=True)
    closed_at = DateTime(required=True)
