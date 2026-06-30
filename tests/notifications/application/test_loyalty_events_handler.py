"""Application tests for the Loyalty cross-domain subscriber in Notifications."""

from protean import current_domain

from notifications.notification.loyalty_subscriber import LoyaltyEventsSubscriber
from notifications.notification.notification import Notification, NotificationType


def _message(event_type: str, data: dict) -> dict:
    return {"data": data, "metadata": {"headers": {"type": event_type}}}


def _notifications_for(customer_id, notification_type):
    return (
        current_domain.repository_for(Notification)
        .query.filter(recipient_id=customer_id, notification_type=notification_type)
        .all()
        .items
    )


class TestTierUpgradedHandler:
    def test_creates_tier_upgraded_notification(self):
        LoyaltyEventsSubscriber()(
            _message(
                "Loyalty.TierUpgraded.v1",
                {
                    "account_id": "acc-1",
                    "customer_id": "cust-tier-1",
                    "old_tier": "bronze",
                    "new_tier": "silver",
                    "lifetime_points": 1500,
                },
            )
        )
        assert len(_notifications_for("cust-tier-1", NotificationType.TIER_UPGRADED.value)) >= 1


class TestPointsRedeemedHandler:
    def test_creates_points_redeemed_notification(self):
        LoyaltyEventsSubscriber()(
            _message(
                "Loyalty.PointsRedeemed.v1",
                {
                    "account_id": "acc-2",
                    "customer_id": "cust-redeem-1",
                    "amount": 200,
                    "balance_after": 50,
                    "reason": "voucher",
                },
            )
        )
        assert len(_notifications_for("cust-redeem-1", NotificationType.POINTS_REDEEMED.value)) >= 1

    def test_missing_customer_id_is_a_noop(self):
        # Should not raise; simply skips notification creation.
        LoyaltyEventsSubscriber()(_message("Loyalty.PointsRedeemed.v1", {"account_id": "acc-3", "amount": 10}))

    def test_unrelated_event_type_is_ignored(self):
        LoyaltyEventsSubscriber()(_message("Loyalty.PointsEarned.v1", {"customer_id": "cust-earn-1", "amount": 5}))
        assert _notifications_for("cust-earn-1", NotificationType.TIER_UPGRADED.value) == []
