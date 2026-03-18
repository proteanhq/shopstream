"""Inbound cross-domain subscriber — Inventory reacts to Ordering events.

Listens for OrderCancelled and OrderReturned events from the Ordering domain's
external bus to release reservations (on cancellation) or log returns for
restocking (on return).

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into domain commands.
No dependency on shared event classes or register_external_event.
"""

import structlog
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.projections.reservation_status import ReservationStatus

logger = structlog.get_logger(__name__)


@inventory.subscriber(broker="global", stream="ordering::order")
class OrderingEventsSubscriber:
    """Reacts to Ordering domain events to manage stock reservations and returns.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and dispatches appropriate commands. Ignores all
    event types not relevant to the Inventory domain.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "OrderCancelled" in event_type:
            self._on_order_cancelled(data)
        elif "OrderReturned" in event_type:
            self._on_order_returned(data)

    def _on_order_cancelled(self, data: dict) -> None:
        """Release active/confirmed reservations when an order is cancelled."""
        order_id = str(data.get("order_id", ""))
        reason = data.get("reason", "")

        logger.info(
            "Releasing reservations for cancelled order",
            order_id=order_id,
            reason=reason,
        )

        # Find active or confirmed reservations for this order
        reservations = current_domain.view_for(ReservationStatus).query.filter(order_id=order_id).all().items

        releasable = [r for r in reservations if r.status in ("Active", "Confirmed")]

        if not releasable:
            logger.info(
                "No releasable reservations for cancelled order",
                order_id=order_id,
            )
            return

        from inventory.stock.reservation import ReleaseReservation

        for reservation in releasable:
            current_domain.process(
                ReleaseReservation(
                    inventory_item_id=str(reservation.inventory_item_id),
                    reservation_id=str(reservation.reservation_id),
                    reason=f"order_cancelled: {reason}",
                ),
                asynchronous=False,
            )
            logger.info(
                "Released reservation for cancelled order",
                reservation_id=str(reservation.reservation_id),
                inventory_item_id=str(reservation.inventory_item_id),
                order_id=order_id,
            )

    def _on_order_returned(self, data: dict) -> None:
        """Return items to stock when an order is returned.

        Note: OrderReturned carries returned_item_ids (order item UUIDs),
        not product/variant details needed for stock lookup. Restocking
        requires a separate enrichment step or a query back to the order.
        For now we log the return for auditing.
        """
        order_id = str(data.get("order_id", ""))
        returned_item_ids = data.get("returned_item_ids", [])

        logger.info(
            "Order returned — items noted for restocking",
            order_id=order_id,
            returned_item_ids=returned_item_ids,
        )
