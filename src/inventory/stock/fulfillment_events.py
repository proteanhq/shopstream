"""Outbound cross-domain event handler — Inventory reacts to Fulfillment events.

Listens for ShipmentHandedOff events from the Fulfillment domain to commit
reserved stock (reduce on-hand count) when items leave the warehouse.

Cross-domain events are imported from shared.events.fulfillment and registered
as external events via inventory.register_external_event().
"""

import structlog
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from inventory.domain import inventory
from inventory.projections.reservation_status import ReservationStatus
from inventory.stock.stock import InventoryItem
from shared.events.fulfillment import (
    DeliveryConfirmed,
    DeliveryException,
    FulfillmentCancelled,
    FulfillmentCreated,
    ItemPicked,
    PackingCompleted,
    PickerAssigned,
    PickingCompleted,
    ShipmentHandedOff,
    ShippingLabelGenerated,
    TrackingEventReceived,
)

logger = structlog.get_logger(__name__)

# Register external events so Protean can deserialize them
inventory.register_external_event(FulfillmentCreated, "Fulfillment.FulfillmentCreated.v1")
inventory.register_external_event(PickerAssigned, "Fulfillment.PickerAssigned.v1")
inventory.register_external_event(ItemPicked, "Fulfillment.ItemPicked.v1")
inventory.register_external_event(PickingCompleted, "Fulfillment.PickingCompleted.v1")
inventory.register_external_event(PackingCompleted, "Fulfillment.PackingCompleted.v1")
inventory.register_external_event(ShippingLabelGenerated, "Fulfillment.ShippingLabelGenerated.v1")
inventory.register_external_event(ShipmentHandedOff, "Fulfillment.ShipmentHandedOff.v1")
inventory.register_external_event(DeliveryConfirmed, "Fulfillment.DeliveryConfirmed.v1")
inventory.register_external_event(DeliveryException, "Fulfillment.DeliveryException.v1")
inventory.register_external_event(TrackingEventReceived, "Fulfillment.TrackingEventReceived.v1")
inventory.register_external_event(FulfillmentCancelled, "Fulfillment.FulfillmentCancelled.v1")


@inventory.event_handler(part_of=InventoryItem, stream_category="fulfillment::fulfillment")
class FulfillmentInventoryEventHandler:
    """Reacts to Fulfillment domain events to commit reserved stock."""

    @handle(ShipmentHandedOff)
    def on_shipment_handed_off(self, event: ShipmentHandedOff) -> None:
        """Commit reserved stock when shipment leaves the warehouse.

        Queries the ReservationStatus projection to find confirmed
        reservations for the order, then commits each one.
        """
        logger.info(
            "Committing stock for shipped fulfillment",
            order_id=str(event.order_id),
            fulfillment_id=str(event.fulfillment_id),
        )

        # Query the ReservationStatus read model for confirmed reservations
        try:
            confirmed = (
                current_domain.view_for(ReservationStatus)
                .query.filter(
                    order_id=str(event.order_id),
                    status="Confirmed",
                )
                .all()
                .items
            )
        except Exception:
            confirmed = []

        if not confirmed:
            logger.info(
                "No confirmed reservations for order",
                order_id=str(event.order_id),
            )
            return

        from inventory.stock.shipping import CommitStock

        for reservation in confirmed:
            current_domain.process(
                CommitStock(
                    inventory_item_id=str(reservation.inventory_item_id),
                    reservation_id=str(reservation.reservation_id),
                ),
                asynchronous=False,
            )
            logger.info(
                "Committed stock reservation",
                inventory_item_id=str(reservation.inventory_item_id),
                reservation_id=str(reservation.reservation_id),
                order_id=str(event.order_id),
            )
