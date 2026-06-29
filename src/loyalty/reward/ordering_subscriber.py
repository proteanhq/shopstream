"""Inbound cross-domain subscriber — Loyalty reacts to the Ordering stream (ACL).

Awards a delivery bonus to a customer's reward account when their order is delivered.

This uses subscriber **pattern B** (direct aggregate mutation): it loads the RewardAccount
and calls a business method, rather than translating the message into a command and
dispatching it (pattern A, used by the other ShopStream subscribers). It receives raw dict
payloads from the shared `global` broker and never imports Ordering's event classes.
"""

import structlog
from protean.utils.globals import current_domain

from loyalty.domain import loyalty
from loyalty.reward.reward_account import RewardAccount

logger = structlog.get_logger(__name__)

DELIVERY_BONUS_POINTS = 50


@loyalty.subscriber(broker="global", stream="ordering::order")
class OrderDeliveredSubscriber:
    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        if "OrderDelivered" not in event_type:
            return

        data = payload.get("data", {})
        customer_id = data.get("customer_id")
        if not customer_id:
            return

        repo = current_domain.repository_for(RewardAccount)
        matches = repo._dao.query.filter(customer_id=customer_id).all().items
        if not matches:
            logger.info(
                "No reward account for customer; skipping delivery bonus",
                customer_id=str(customer_id),
            )
            return

        # Pattern B: load and mutate the aggregate directly.
        account = repo.get(matches[0].id)
        account.earn_points(DELIVERY_BONUS_POINTS, reason="order_delivered")
        repo.add(account)
