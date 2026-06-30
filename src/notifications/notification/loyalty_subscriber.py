"""Inbound cross-domain subscriber — Notifications reacts to Loyalty events.

Listens for TierUpgraded (congratulatory milestone) and PointsRedeemed (redemption
confirmation) on the loyalty reward-account stream.

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global broker,
filters by event type, and translates into domain-local notifications. No dependency on
shared event classes or register_external_event.
"""

import structlog

from notifications.domain import notifications
from notifications.notification.helpers import create_notifications_for_customer
from notifications.notification.notification import NotificationType

logger = structlog.get_logger(__name__)


@notifications.subscriber(broker="global", stream="loyalty::reward_account")
class LoyaltyEventsSubscriber:
    """Reacts to Loyalty domain events to send customer notifications."""

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "TierUpgraded" in event_type:
            self._on_tier_upgraded(data)
        elif "PointsRedeemed" in event_type:
            self._on_points_redeemed(data)

    def _on_tier_upgraded(self, data: dict) -> None:
        customer_id = data.get("customer_id")
        if not customer_id:
            return
        create_notifications_for_customer(
            customer_id=str(customer_id),
            notification_type=NotificationType.TIER_UPGRADED.value,
            context={
                "old_tier": data.get("old_tier", ""),
                "new_tier": data.get("new_tier", ""),
                "lifetime_points": str(data.get("lifetime_points", "")),
            },
            source_event_type="Loyalty.TierUpgraded.v1",
        )

    def _on_points_redeemed(self, data: dict) -> None:
        customer_id = data.get("customer_id")
        if not customer_id:
            logger.info(
                "PointsRedeemed missing customer_id, skipping notification",
                account_id=str(data.get("account_id", "")),
            )
            return
        create_notifications_for_customer(
            customer_id=str(customer_id),
            notification_type=NotificationType.POINTS_REDEEMED.value,
            context={
                "amount": str(data.get("amount", "")),
                "balance_after": str(data.get("balance_after", "")),
                "reason": data.get("reason") or "",
            },
            source_event_type="Loyalty.PointsRedeemed.v1",
        )
