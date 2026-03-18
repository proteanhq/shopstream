"""Inbound cross-domain subscriber — Inventory reacts to Fulfillment events.

Listens for ShipmentHandedOff events from the Fulfillment domain's external bus
to commit reserved stock (reduce on-hand count) when items leave the warehouse.

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into domain commands.
No dependency on shared event classes or register_external_event.
"""

import structlog
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.projections.reservation_status import ReservationStatus

logger = structlog.get_logger(__name__)


@inventory.subscriber(broker="global", stream="fulfillment::fulfillment")
class FulfillmentEventsSubscriber:
    """Reacts to Fulfillment domain events to commit reserved stock.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and dispatches CommitStock commands. Ignores all
    event types not relevant to the Inventory domain.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "ShipmentHandedOff" in event_type:
            self._on_shipment_handed_off(data)

    def _on_shipment_handed_off(self, data: dict) -> None:
        """Commit reserved stock when shipment leaves the warehouse.

        Queries the ReservationStatus projection to find confirmed
        reservations for the order, then commits each one.
        """
        order_id = str(data.get("order_id", ""))
        logger.info(
            "Committing stock for shipped fulfillment",
            order_id=order_id,
            fulfillment_id=str(data.get("fulfillment_id", "")),
        )

        try:
            confirmed = (
                current_domain.view_for(ReservationStatus)
                .query.filter(
                    order_id=order_id,
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
                order_id=order_id,
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
                order_id=order_id,
            )
