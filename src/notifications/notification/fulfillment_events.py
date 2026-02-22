"""Inbound cross-domain event handler — Notifications reacts to Fulfillment events.

Listens for ShipmentHandedOff (shipping update), DeliveryConfirmed (delivery
confirmation), and DeliveryException (delivery issue alert).
"""

import structlog
from notifications.domain import notifications
from notifications.notification.notification import Notification
from protean.utils.mixins import handle
from shared.events.fulfillment import (
    DeliveryConfirmed,
    DeliveryException,
    ShipmentHandedOff,
)

logger = structlog.get_logger(__name__)

notifications.register_external_event(ShipmentHandedOff, "Fulfillment.ShipmentHandedOff.v1")
notifications.register_external_event(DeliveryConfirmed, "Fulfillment.DeliveryConfirmed.v1")
notifications.register_external_event(DeliveryException, "Fulfillment.DeliveryException.v1")


@notifications.event_handler(part_of=Notification, stream_category="fulfillment::fulfillment")
class FulfillmentEventsHandler:
    """Reacts to Fulfillment domain events to send customer notifications."""

    @handle(ShipmentHandedOff)
    def on_shipment_handed_off(self, event: ShipmentHandedOff) -> None:
        """Send shipping notification when order ships.

        Note: ShipmentHandedOff doesn't carry customer_id directly.
        In a real system we'd look up the order. For now we log a warning.
        """
        # The shared ShipmentHandedOff event doesn't have customer_id
        # We'd need to query the order to get it. For this reference
        # implementation, we log and skip.
        logger.info(
            "ShipmentHandedOff received — shipping notification requires customer lookup",
            order_id=str(event.order_id),
            carrier=event.carrier,
            tracking_number=event.tracking_number,
        )

    @handle(DeliveryConfirmed)
    def on_delivery_confirmed(self, event: DeliveryConfirmed) -> None:
        """Send delivery confirmation when order is delivered.

        Note: DeliveryConfirmed doesn't carry customer_id.
        Same limitation as ShipmentHandedOff.
        """
        logger.info(
            "DeliveryConfirmed received — delivery notification requires customer lookup",
            order_id=str(event.order_id),
        )

    @handle(DeliveryException)
    def on_delivery_exception(self, event: DeliveryException) -> None:
        """Send delivery exception alert when there's a delivery issue.

        Note: DeliveryException doesn't carry customer_id.
        Same limitation as above.
        """
        logger.info(
            "DeliveryException received — exception notification requires customer lookup",
            order_id=str(event.order_id),
            reason=event.reason,
        )
