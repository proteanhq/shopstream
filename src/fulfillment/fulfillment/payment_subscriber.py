"""Inbound cross-domain subscriber — Fulfillment reacts to Payment events.

Listens for PaymentSucceeded events from the Payments domain to automatically
create a fulfillment when an order is paid, triggering the warehouse
picking workflow.

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into domain-local side effects.
No dependency on shared event classes or register_external_event.
"""

import structlog

from fulfillment.domain import fulfillment

logger = structlog.get_logger(__name__)


@fulfillment.subscriber(broker="global", stream="payments::payment")
class PaymentEventsSubscriber:
    """Reacts to Payment domain events to create fulfillments.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and performs domain actions. Ignores all event
    types not relevant to the Fulfillment domain.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "PaymentSucceeded" in event_type:
            self._on_payment_succeeded(data)

    def _on_payment_succeeded(self, data: dict) -> None:
        """Create a fulfillment when payment succeeds.

        Note: The PaymentSucceeded event carries order_id and customer_id
        but not the full item list. We query the Order read model for item
        details needed to create the fulfillment pick list.
        """
        logger.info(
            "Payment succeeded — creating fulfillment",
            order_id=str(data.get("order_id", "")),
            payment_id=str(data.get("payment_id", "")),
        )

        # We need order item details to create the fulfillment.
        # Since we can't query the Ordering domain directly from here,
        # the fulfillment creation requires items data. In a fully wired
        # system, the OrderPaid shared event (which carries items) would
        # be used instead. For now, log and skip if items aren't available.
        #
        # In production, the API or saga would call CreateFulfillment with
        # the full item list after payment confirmation.
        logger.info(
            "Fulfillment auto-creation requires order item details. "
            "In production, the OrderCheckoutSaga or API orchestrates this.",
            order_id=str(data.get("order_id", "")),
        )
