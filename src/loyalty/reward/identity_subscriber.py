"""Inbound cross-domain subscriber — Loyalty reacts to Identity events (ACL).

On `CustomerRegistered`, auto-enrols the customer into the rewards program by dispatching
an `EnrollRewardAccount` command (subscriber **pattern A** — translate the event into a
command, in contrast to the pattern-B `OrderDeliveredSubscriber`). Idempotent: skips if the
customer already has a reward account, so at-least-once delivery is safe.

This is what gives every customer a reward account through the normal event flow — no
HTTP enrolment endpoint and no out-of-band seeding required.
"""

import structlog
from protean.utils.globals import current_domain

from loyalty.domain import loyalty
from loyalty.reward.enrollment import EnrollRewardAccount
from loyalty.reward.reward_account import RewardAccount

logger = structlog.get_logger(__name__)


@loyalty.subscriber(broker="global", stream="identity::customer")
class CustomerRegisteredSubscriber:
    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        if "CustomerRegistered" not in event_type:
            return

        customer_id = payload.get("data", {}).get("customer_id")
        if not customer_id:
            return

        customer_id = str(customer_id)
        repo = current_domain.repository_for(RewardAccount)

        # Idempotent: don't enrol the same customer twice on redelivery.
        if repo._dao.query.filter(customer_id=customer_id).all().items:
            logger.info("Customer already enrolled in rewards; skipping", customer_id=customer_id)
            return

        current_domain.process(EnrollRewardAccount(customer_id=customer_id), asynchronous=False)
