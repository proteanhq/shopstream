"""Inbound cross-domain event handler — Reviews reacts to Ordering events.

Listens for OrderDelivered events from the Ordering domain to populate
the VerifiedPurchases projection, which is used by the SubmitReview handler
to flag reviews as verified purchases.

Cross-domain events are imported from shared.events.ordering and registered
as external events via reviews.register_external_event().
"""

import structlog
from protean.utils.globals import current_domain
from protean.utils.mixins import handle
from shared.events.ordering import OrderDelivered

from reviews.domain import reviews
from reviews.projections.verified_purchases import VerifiedPurchases
from reviews.review.review import Review

logger = structlog.get_logger(__name__)

# Register external event so Protean can deserialize it
reviews.register_external_event(OrderDelivered, "Ordering.OrderDelivered.v1")


@reviews.event_handler(part_of=Review, stream_category="ordering::order")
class OrderingEventsHandler:
    """Reacts to Ordering domain events to track verified purchases."""

    @handle(OrderDelivered)
    def on_order_delivered(self, event: OrderDelivered) -> None:
        """Record verified purchase when order is delivered.

        Note: OrderDelivered only carries order_id and delivered_at.
        We look up the order details from the Ordering domain's OrderDetail
        projection or use the customer_id/items if available on the shared event.
        """
        # The shared OrderDelivered event carries customer_id and items
        if not hasattr(event, "customer_id") or not event.customer_id:
            logger.info(
                "OrderDelivered missing customer_id, skipping verified purchase",
                order_id=str(event.order_id),
            )
            return

        vp_repo = current_domain.repository_for(VerifiedPurchases)

        # If items are available, create one record per product
        if hasattr(event, "items") and event.items:
            import json
            import uuid

            items = json.loads(event.items) if isinstance(event.items, str) else []
            for item in items:
                try:
                    vp_repo.add(
                        VerifiedPurchases(
                            vp_id=str(uuid.uuid4()),
                            customer_id=str(event.customer_id),
                            product_id=str(item["product_id"]),
                            variant_id=str(item.get("variant_id", "")),
                            order_id=str(event.order_id),
                            delivered_at=event.delivered_at,
                        )
                    )
                except Exception:
                    logger.warning(
                        "Failed to create verified purchase record",
                        order_id=str(event.order_id),
                        product_id=str(item.get("product_id")),
                    )
        else:
            logger.info(
                "OrderDelivered missing items, cannot create per-product records",
                order_id=str(event.order_id),
            )
