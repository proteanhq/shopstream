"""Inbound cross-domain subscriber — Loyalty reacts to the Payments stream (ACL).

Claws back loyalty points when an order is refunded: a refunded purchase should not keep the
points it earned. Like the ordering/reviews subscribers, this uses subscriber **pattern B**
(direct aggregate mutation) — it loads the customer's `RewardAccount` and calls a business
method. It receives raw dict payloads from the shared `global` broker, filters by event type,
and never imports the Payments event classes.

Points model: one point clawed back per unit of refunded amount, clamped to the balance (see
`RewardAccount.claw_back_points`). A real program would track points per order; this keeps the
showcase self-contained while exercising a refund→loyalty reversal end-to-end.
"""

import structlog
from protean.utils.globals import current_domain

from loyalty.domain import loyalty
from loyalty.reward.reward_account import RewardAccount

logger = structlog.get_logger(__name__)


@loyalty.subscriber(broker="global", stream="payments::payment")
class PaymentRefundedSubscriber:
    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        if "RefundCompleted" not in event_type:
            return

        data = payload.get("data", {})
        customer_id = data.get("customer_id")
        if not customer_id:
            logger.info("RefundCompleted missing customer_id; skipping clawback")
            return

        points = int(data.get("amount") or 0)
        if points <= 0:
            return

        repo = current_domain.repository_for(RewardAccount)
        matches = repo._dao.query.filter(customer_id=str(customer_id)).all().items
        if not matches:
            logger.info("No reward account for customer; skipping clawback", customer_id=str(customer_id))
            return

        account = repo.get(matches[0].id)
        account.claw_back_points(points, reason=f"refund:{data.get('order_id', '')}")
        repo.add(account)
