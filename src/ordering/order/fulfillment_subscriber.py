"""Inbound cross-domain subscriber — Ordering reacts to Fulfillment events.

Listens for ShipmentHandedOff, DeliveryConfirmed, and DeliveryException events
from the Fulfillment domain's external bus to update Order status accordingly.

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into domain commands.
No dependency on shared event classes or register_external_event.
"""

import structlog
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.fulfillment import RecordDelivery, RecordShipment

logger = structlog.get_logger(__name__)


@ordering.subscriber(broker="global", stream="fulfillment::fulfillment")
class FulfillmentEventsSubscriber:
    """Reacts to Fulfillment domain events to update Order status.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and dispatches domain commands. Ignores all
    event types not relevant to the Ordering domain.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "ShipmentHandedOff" in event_type:
            self._on_shipment_handed_off(data)
        elif "DeliveryConfirmed" in event_type:
            self._on_delivery_confirmed(data)
        elif "DeliveryException" in event_type:
            self._on_delivery_exception(data)

    def _on_shipment_handed_off(self, data: dict) -> None:
        """Record shipment on the order when fulfillment hands off to carrier."""
        logger.info(
            "Recording shipment on order from fulfillment handoff",
            order_id=str(data.get("order_id", "")),
            fulfillment_id=str(data.get("fulfillment_id", "")),
            tracking_number=data.get("tracking_number", ""),
        )
        current_domain.process(
            RecordShipment(
                order_id=data["order_id"],
                shipment_id=str(data["fulfillment_id"]),
                carrier=data["carrier"],
                tracking_number=data["tracking_number"],
                shipped_item_ids=data.get("shipped_item_ids", []),
            ),
            asynchronous=False,
        )

    def _on_delivery_confirmed(self, data: dict) -> None:
        """Record delivery on the order when carrier confirms delivery."""
        logger.info(
            "Recording delivery on order from fulfillment confirmation",
            order_id=str(data.get("order_id", "")),
            fulfillment_id=str(data.get("fulfillment_id", "")),
        )
        current_domain.process(
            RecordDelivery(order_id=data["order_id"]),
            asynchronous=False,
        )

    def _on_delivery_exception(self, data: dict) -> None:
        """Log delivery exception for customer service visibility.

        The Order aggregate stays in its current state (SHIPPED). The exception
        details are captured for CS visibility. The order is not transitioned
        to a separate EXCEPTION state because delivery exceptions are often
        temporary (e.g., failed first delivery attempt).
        """
        logger.warning(
            "Delivery exception reported for order",
            order_id=str(data.get("order_id", "")),
            fulfillment_id=str(data.get("fulfillment_id", "")),
            reason=data.get("reason", ""),
            location=data.get("location", ""),
        )
