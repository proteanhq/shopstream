"""Inbound cross-domain subscriber — Fulfillment reacts to Ordering events.

Listens for OrderCancelled events from the Ordering domain's external bus
to cancel in-progress fulfillments.

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into domain-local side effects.
No dependency on shared event classes or register_external_event.
"""

import structlog
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment

logger = structlog.get_logger(__name__)


@fulfillment.subscriber(broker="global", stream="ordering::order")
class OrderEventsSubscriber:
    """Reacts to Ordering domain events relevant to Fulfillment.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and performs domain actions. Ignores all event
    types not relevant to the Fulfillment domain.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "OrderCancelled" in event_type:
            self._on_order_cancelled(data)

    def _on_order_cancelled(self, data: dict) -> None:
        """Cancel in-progress fulfillment when order is cancelled."""
        order_id = str(data["order_id"])
        repo = current_domain.repository_for(Fulfillment)

        results = repo.query.filter(order_id=order_id).all()
        if not results or not results.items:
            logger.info(
                "No fulfillment found for cancelled order",
                order_id=order_id,
            )
            return

        ff = results.first
        from fulfillment.fulfillment.fulfillment import FulfillmentStatus

        if ff.can_transition_to("status", FulfillmentStatus.CANCELLED.value):
            reason = data.get("reason", "Order cancelled")
            ff.cancel(reason=f"Order cancelled: {reason}")
            repo.add(ff)
            logger.info(
                "Fulfillment cancelled due to order cancellation",
                fulfillment_id=str(ff.id),
                order_id=order_id,
            )
        else:
            logger.warning(
                "Cannot cancel fulfillment — already shipped",
                fulfillment_id=str(ff.id),
                order_id=order_id,
                status=ff.status,
            )
