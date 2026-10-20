"""Domain events for the RewardAccount aggregate (delta events, versioned).

`PointsEarned`, `PointsRedeemed`, `TierUpgraded`, and `RewardAccountEnrolled` are
`published=True` — dual-written to the shared external bus so other contexts can react
(Notifications turns tier upgrades and redemptions into customer notifications). They carry
`customer_id` so downstream consumers can address the customer without a loyalty lookup.
"""

from datetime import datetime

from protean.fields import DateTime, Integer, String

from loyalty.domain import loyalty


@loyalty.event(part_of="RewardAccount", published=True)
class RewardAccountEnrolled:
    account_id: str = String(required=True)
    customer_id: str = String(required=True)
    member_code: str = String(required=True)
    tier: str = String(required=True)
    enrolled_at: datetime = DateTime(required=True)


@loyalty.event(part_of="RewardAccount", published=True)
class PointsEarned:
    account_id: str = String(required=True)
    customer_id: str | None = String()
    amount: int = Integer(required=True)
    balance_after: int = Integer(required=True)
    reason: str | None = String()
    occurred_at: datetime = DateTime(required=True)


@loyalty.event(part_of="RewardAccount", published=True)
class PointsRedeemed:
    account_id: str = String(required=True)
    customer_id: str | None = String()
    amount: int = Integer(required=True)
    balance_after: int = Integer(required=True)
    reason: str | None = String()
    occurred_at: datetime = DateTime(required=True)


@loyalty.event(part_of="RewardAccount", published=True)
class TierUpgraded:
    account_id: str = String(required=True)
    customer_id: str = String(required=True)
    old_tier: str = String(required=True)
    new_tier: str = String(required=True)
    lifetime_points: int = Integer(required=True)
    occurred_at: datetime = DateTime(required=True)


@loyalty.event(part_of="RewardAccount")
class MembershipCardIssued:
    account_id: str = String(required=True)
    card_number: str = String(required=True)
    issued_on: str = String(required=True)


@loyalty.event(part_of="RewardAccount")
class RewardAccountClosed:
    account_id: str = String(required=True)
    closed_at: datetime = DateTime(required=True)
