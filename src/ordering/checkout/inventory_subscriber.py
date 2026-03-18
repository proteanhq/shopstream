"""Inbound cross-domain subscriber — Ordering reacts to Inventory events.

Listens for StockReserved and ReservationReleased events from the Inventory
domain's external bus and translates them into Ordering domain commands.

This subscriber replaces the direct stream subscription that the
OrderCheckoutSaga previously had to inventory::inventory_item. The saga
now reacts only to internal ordering events.

Flow:
- StockReserved → dispatches RecordPaymentPending (initiates payment step)
- ReservationReleased → dispatches CancelOrder (reservation expired/failed)
"""

import structlog
from protean.exceptions import ValidationError
from protean.utils.globals import current_domain

from ordering.domain import ordering

logger = structlog.get_logger(__name__)


@ordering.subscriber(broker="global", stream="inventory::inventory_item")
class InventoryEventsSubscriber:
    """Translates Inventory domain events into Ordering domain commands.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and dispatches domain commands. Ignores all
    event types not relevant to the Ordering domain's checkout flow.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "StockReserved" in event_type:
            self._on_stock_reserved(data)
        elif "ReservationReleased" in event_type:
            self._on_reservation_released(data)

    def _on_stock_reserved(self, data: dict) -> None:
        """Stock reserved — initiate payment for the order."""
        order_id = data.get("order_id")
        if not order_id:
            return

        logger.info(
            "Stock reserved for order — initiating payment",
            order_id=str(order_id),
            reservation_id=str(data.get("reservation_id", "")),
        )

        from ordering.order.payment import RecordPaymentPending

        try:
            current_domain.process(
                RecordPaymentPending(
                    order_id=order_id,
                    payment_id=f"saga-pay-{order_id}",
                    payment_method="credit_card",
                ),
                asynchronous=False,
            )
        except ValidationError:
            logger.info(
                "Order %s already transitioned; skipping RecordPaymentPending",
                order_id,
            )

    def _on_reservation_released(self, data: dict) -> None:
        """Reservation released — cancel the order."""
        order_id = data.get("order_id")
        if not order_id:
            return

        reason = data.get("reason", "Reservation released")
        logger.info(
            "Reservation released for order — cancelling",
            order_id=str(order_id),
            reason=reason,
        )

        from ordering.order.cancellation import CancelOrder

        try:
            current_domain.process(
                CancelOrder(
                    order_id=order_id,
                    reason=f"Inventory reservation released: {reason}",
                    cancelled_by="System",
                ),
                asynchronous=False,
            )
        except ValidationError:
            logger.info(
                "Order %s already cancelled; skipping CancelOrder",
                order_id,
            )
