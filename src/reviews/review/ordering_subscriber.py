"""Inbound cross-domain subscriber — Reviews reacts to Ordering stream.

Listens for OrderDelivered messages from the Ordering domain's broker stream
to populate the VerifiedPurchases projection, which is used by the
SubmitReview handler to flag reviews as verified purchases.

Uses the subscriber (ACL) pattern: receives raw dict payloads from the broker,
filters by event type, and translates into domain-local side effects.
No dependency on shared event classes or register_external_event.
"""

import uuid

import structlog
from protean.utils.globals import current_domain

from reviews.domain import reviews
from reviews.projections.verified_purchases import VerifiedPurchases

logger = structlog.get_logger(__name__)


@reviews.subscriber(stream="ordering::order")
class OrderDeliveredSubscriber:
    """Reacts to OrderDelivered events to track verified purchases.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and creates VerifiedPurchases records from the
    event data. Ignores all other event types on the stream.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        if "OrderDelivered" not in event_type:
            return

        data = payload.get("data", {})

        customer_id = data.get("customer_id")
        if not customer_id:
            logger.info(
                "OrderDelivered missing customer_id, skipping verified purchase",
                order_id=str(data.get("order_id", "")),
            )
            return

        items = data.get("items", [])
        if not items:
            logger.info(
                "OrderDelivered missing items, cannot create per-product records",
                order_id=str(data.get("order_id", "")),
            )
            return

        vp_repo = current_domain.repository_for(VerifiedPurchases)

        for item in items:
            try:
                vp_repo.add(
                    VerifiedPurchases(
                        vp_id=str(uuid.uuid4()),
                        customer_id=str(customer_id),
                        product_id=str(item["product_id"]),
                        variant_id=str(item.get("variant_id", "")),
                        order_id=str(data["order_id"]),
                        delivered_at=data.get("delivered_at"),
                    )
                )
            except Exception:
                logger.warning(
                    "Failed to create verified purchase record",
                    order_id=str(data.get("order_id", "")),
                    product_id=str(item.get("product_id", "")),
                )
