"""Outbound cross-domain event handler — Inventory reacts to Fulfillment events.

Listens for ShipmentHandedOff events from the Fulfillment domain to commit
reserved stock (reduce on-hand count) when items leave the warehouse.

Cross-domain events are imported from shared.events.fulfillment and registered
as external events via inventory.register_external_event().
"""

import structlog
from protean.utils.globals import current_domain
from protean.utils.mixins import handle
from shared.events.fulfillment import ShipmentHandedOff

from inventory.domain import inventory
from inventory.stock.stock import InventoryItem

logger = structlog.get_logger(__name__)

# Register external event so Protean can deserialize it
inventory.register_external_event(ShipmentHandedOff, "Fulfillment.ShipmentHandedOff.v1")


@inventory.event_handler(part_of=InventoryItem, stream_category="fulfillment::fulfillment")
class FulfillmentInventoryEventHandler:
    """Reacts to Fulfillment domain events to commit reserved stock."""

    @handle(ShipmentHandedOff)
    def on_shipment_handed_off(self, event: ShipmentHandedOff) -> None:
        """Commit reserved stock when shipment leaves the warehouse.

        This finds active reservations for the order and commits them,
        reducing on-hand stock and clearing the reservation.
        """
        logger.info(
            "Committing stock for shipped fulfillment",
            order_id=str(event.order_id),
            fulfillment_id=str(event.fulfillment_id),
        )
        # Find inventory items with active reservations for this order
        repo = current_domain.repository_for(InventoryItem)
        results = repo._dao.query.all()

        if not results or not results.items:
            logger.warning(
                "No inventory items found for stock commitment",
                order_id=str(event.order_id),
            )
            return

        for item in results.items:
            if not item.reservations:
                continue
            for reservation in item.reservations:
                if str(reservation.order_id) == str(event.order_id) and reservation.status == "Active":
                    from inventory.stock.shipping import CommitStock

                    current_domain.process(
                        CommitStock(
                            inventory_item_id=str(item.id),
                            reservation_id=str(reservation.id),
                        ),
                        asynchronous=False,
                    )
                    logger.info(
                        "Committed stock reservation",
                        inventory_item_id=str(item.id),
                        reservation_id=str(reservation.id),
                        order_id=str(event.order_id),
                    )
