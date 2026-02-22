"""Outbound cross-domain event handler — Ordering reacts to Fulfillment events.

Listens for ShipmentHandedOff, DeliveryConfirmed, and DeliveryException events
from the Fulfillment domain to update Order status accordingly.

Cross-domain events are imported from shared.events.fulfillment and registered
as external events via ordering.register_external_event().
"""

import structlog
from protean.utils.globals import current_domain
from protean.utils.mixins import handle
from shared.events.fulfillment import DeliveryConfirmed, DeliveryException, ShipmentHandedOff

from ordering.domain import ordering
from ordering.order.fulfillment import RecordDelivery, RecordShipment
from ordering.order.order import Order

logger = structlog.get_logger(__name__)

# Register external events so Protean can deserialize them
ordering.register_external_event(ShipmentHandedOff, "Fulfillment.ShipmentHandedOff.v1")
ordering.register_external_event(DeliveryConfirmed, "Fulfillment.DeliveryConfirmed.v1")
ordering.register_external_event(DeliveryException, "Fulfillment.DeliveryException.v1")


@ordering.event_handler(part_of=Order, stream_category="fulfillment::fulfillment")
class FulfillmentOrderEventHandler:
    """Reacts to Fulfillment domain events to update Order status."""

    @handle(ShipmentHandedOff)
    def on_shipment_handed_off(self, event: ShipmentHandedOff) -> None:
        """Record shipment on the order when fulfillment hands off to carrier."""
        logger.info(
            "Recording shipment on order from fulfillment handoff",
            order_id=str(event.order_id),
            fulfillment_id=str(event.fulfillment_id),
            tracking_number=event.tracking_number,
        )
        current_domain.process(
            RecordShipment(
                order_id=event.order_id,
                shipment_id=str(event.fulfillment_id),
                carrier=event.carrier,
                tracking_number=event.tracking_number,
                shipped_item_ids=event.shipped_item_ids,
            ),
            asynchronous=False,
        )

    @handle(DeliveryConfirmed)
    def on_delivery_confirmed(self, event: DeliveryConfirmed) -> None:
        """Record delivery on the order when carrier confirms delivery."""
        logger.info(
            "Recording delivery on order from fulfillment confirmation",
            order_id=str(event.order_id),
            fulfillment_id=str(event.fulfillment_id),
        )
        current_domain.process(
            RecordDelivery(order_id=event.order_id),
            asynchronous=False,
        )

    @handle(DeliveryException)
    def on_delivery_exception(self, event: DeliveryException) -> None:
        """Log delivery exception on the order for customer service.

        The Order aggregate stays in its current state (SHIPPED). The exception
        details are captured for CS visibility. The order is not transitioned
        to a separate EXCEPTION state because delivery exceptions are often
        temporary (e.g., failed first delivery attempt).
        """
        logger.warning(
            "Delivery exception reported for order",
            order_id=str(event.order_id),
            fulfillment_id=str(event.fulfillment_id),
            reason=event.reason,
            location=event.location,
        )
