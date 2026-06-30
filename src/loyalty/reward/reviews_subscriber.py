"""Inbound cross-domain subscriber — Loyalty reacts to the Reviews stream (ACL).

Awards a bonus to a customer's reward account when one of their reviews is approved for
publication. Like `OrderDeliveredSubscriber`, this uses subscriber **pattern B** (direct
aggregate mutation): it loads the RewardAccount and calls `earn_points` rather than
translating the message into a command. It receives raw dict payloads from the shared
`global` broker, filters by event type, and never imports the Reviews event classes.
"""

import structlog
from protean.utils.globals import current_domain

from loyalty.domain import loyalty
from loyalty.reward.reward_account import RewardAccount

logger = structlog.get_logger(__name__)

REVIEW_BONUS_POINTS = 20


@loyalty.subscriber(broker="global", stream="reviews::review")
class ReviewApprovedSubscriber:
    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        if "ReviewApproved" not in event_type:
            return

        data = payload.get("data", {})
        customer_id = data.get("customer_id")
        if not customer_id:
            return

        repo = current_domain.repository_for(RewardAccount)
        matches = repo._dao.query.filter(customer_id=str(customer_id)).all().items
        if not matches:
            logger.info(
                "No reward account for customer; skipping review bonus",
                customer_id=str(customer_id),
            )
            return

        # Pattern B: load and mutate the aggregate directly.
        account = repo.get(matches[0].id)
        account.earn_points(REVIEW_BONUS_POINTS, reason="review_approved")
        repo.add(account)
