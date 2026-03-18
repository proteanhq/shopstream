"""Inbound cross-domain subscriber — Notifications reacts to Fulfillment events.

Listens for ShipmentHandedOff (shipping update), DeliveryConfirmed (delivery
confirmation), and DeliveryException (delivery issue alert).

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into domain-local side effects.
No dependency on shared event classes or register_external_event.
"""

import structlog

from notifications.domain import notifications

logger = structlog.get_logger(__name__)


@notifications.subscriber(broker="global", stream="fulfillment::fulfillment")
class FulfillmentEventsSubscriber:
    """Reacts to Fulfillment domain events to send customer notifications.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and creates notifications. Ignores all event
    types not relevant to the Notifications domain.
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
        """Send shipping notification when order ships.

        Note: ShipmentHandedOff doesn't carry customer_id directly.
        In a real system we'd look up the order. For now we log a warning.
        """
        logger.info(
            "ShipmentHandedOff received — shipping notification requires customer lookup",
            order_id=str(data.get("order_id", "")),
            carrier=data.get("carrier"),
            tracking_number=data.get("tracking_number"),
        )

    def _on_delivery_confirmed(self, data: dict) -> None:
        """Send delivery confirmation when order is delivered.

        Note: DeliveryConfirmed doesn't carry customer_id.
        Same limitation as ShipmentHandedOff.
        """
        logger.info(
            "DeliveryConfirmed received — delivery notification requires customer lookup",
            order_id=str(data.get("order_id", "")),
        )

    def _on_delivery_exception(self, data: dict) -> None:
        """Send delivery exception alert when there's a delivery issue.

        Note: DeliveryException doesn't carry customer_id.
        Same limitation as above.
        """
        logger.info(
            "DeliveryException received — exception notification requires customer lookup",
            order_id=str(data.get("order_id", "")),
            reason=data.get("reason"),
        )
