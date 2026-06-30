"""Domain events for the RewardAccount aggregate (delta events, versioned).

`PointsEarned`, `PointsRedeemed`, `TierUpgraded`, and `RewardAccountEnrolled` are
`published=True` — dual-written to the shared external bus so other contexts can react
(Notifications turns tier upgrades and redemptions into customer notifications). They carry
`customer_id` so downstream consumers can address the customer without a loyalty lookup.
"""

from protean.fields import DateTime, Integer, String

from loyalty.domain import loyalty


@loyalty.event(part_of="RewardAccount", published=True)
class RewardAccountEnrolled:
    account_id = String(required=True)
    customer_id = String(required=True)
    member_code = String(required=True)
    tier = String(required=True)
    enrolled_at = DateTime(required=True)


@loyalty.event(part_of="RewardAccount", published=True)
class PointsEarned:
    account_id = String(required=True)
    customer_id = String()
    amount = Integer(required=True)
    balance_after = Integer(required=True)
    reason = String()
    occurred_at = DateTime(required=True)


@loyalty.event(part_of="RewardAccount", published=True)
class PointsRedeemed:
    account_id = String(required=True)
    customer_id = String()
    amount = Integer(required=True)
    balance_after = Integer(required=True)
    reason = String()
    occurred_at = DateTime(required=True)


@loyalty.event(part_of="RewardAccount", published=True)
class TierUpgraded:
    account_id = String(required=True)
    customer_id = String(required=True)
    old_tier = String(required=True)
    new_tier = String(required=True)
    lifetime_points = Integer(required=True)
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
