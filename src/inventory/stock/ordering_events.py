"""Inbound cross-domain event handler — Inventory reacts to Ordering events.

Listens for OrderCancelled and OrderReturned events from the Ordering domain
to release reservations (on cancellation) or restock items (on return).

Cross-domain events are imported from shared.events.ordering and registered
as external events via inventory.register_external_event().
"""

import structlog
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from inventory.domain import inventory
from inventory.projections.reservation_status import ReservationStatus
from inventory.stock.stock import InventoryItem
from shared.events.ordering import (
    CouponApplied,
    ItemAdded,
    ItemQuantityUpdated,
    ItemRemoved,
    OrderCancelled,
    OrderCompleted,
    OrderConfirmed,
    OrderCreated,
    OrderDelivered,
    OrderPartiallyShipped,
    OrderProcessing,
    OrderRefunded,
    OrderReturned,
    OrderShipped,
    PaymentFailed,
    PaymentPending,
    PaymentSucceeded,
    ReturnApproved,
    ReturnRequested,
)

logger = structlog.get_logger(__name__)

# Register external events so Protean can deserialize them
inventory.register_external_event(OrderCreated, "Ordering.OrderCreated.v1")
inventory.register_external_event(ItemAdded, "Ordering.ItemAdded.v1")
inventory.register_external_event(ItemRemoved, "Ordering.ItemRemoved.v1")
inventory.register_external_event(ItemQuantityUpdated, "Ordering.ItemQuantityUpdated.v1")
inventory.register_external_event(CouponApplied, "Ordering.CouponApplied.v1")
inventory.register_external_event(OrderConfirmed, "Ordering.OrderConfirmed.v1")
inventory.register_external_event(PaymentPending, "Ordering.PaymentPending.v1")
inventory.register_external_event(PaymentSucceeded, "Ordering.PaymentSucceeded.v1")
inventory.register_external_event(PaymentFailed, "Ordering.PaymentFailed.v1")
inventory.register_external_event(OrderProcessing, "Ordering.OrderProcessing.v1")
inventory.register_external_event(OrderShipped, "Ordering.OrderShipped.v1")
inventory.register_external_event(OrderPartiallyShipped, "Ordering.OrderPartiallyShipped.v1")
inventory.register_external_event(OrderDelivered, "Ordering.OrderDelivered.v1")
inventory.register_external_event(OrderCompleted, "Ordering.OrderCompleted.v1")
inventory.register_external_event(ReturnRequested, "Ordering.ReturnRequested.v1")
inventory.register_external_event(ReturnApproved, "Ordering.ReturnApproved.v1")
inventory.register_external_event(OrderReturned, "Ordering.OrderReturned.v1")
inventory.register_external_event(OrderCancelled, "Ordering.OrderCancelled.v1")
inventory.register_external_event(OrderRefunded, "Ordering.OrderRefunded.v1")


@inventory.event_handler(part_of=InventoryItem, stream_category="ordering::order")
class OrderingInventoryEventHandler:
    """Reacts to Ordering domain events to manage stock reservations and returns."""

    @handle(OrderCancelled)
    def on_order_cancelled(self, event: OrderCancelled) -> None:
        """Release active/confirmed reservations when an order is cancelled."""
        logger.info(
            "Releasing reservations for cancelled order",
            order_id=str(event.order_id),
            reason=event.reason,
        )

        # Find active or confirmed reservations for this order
        reservations = current_domain.view_for(ReservationStatus).query.filter(order_id=str(event.order_id)).all().items

        releasable = [r for r in reservations if r.status in ("Active", "Confirmed")]

        if not releasable:
            logger.info(
                "No releasable reservations for cancelled order",
                order_id=str(event.order_id),
            )
            return

        from inventory.stock.reservation import ReleaseReservation

        for reservation in releasable:
            current_domain.process(
                ReleaseReservation(
                    inventory_item_id=str(reservation.inventory_item_id),
                    reservation_id=str(reservation.reservation_id),
                    reason=f"order_cancelled: {event.reason}",
                ),
                asynchronous=False,
            )
            logger.info(
                "Released reservation for cancelled order",
                reservation_id=str(reservation.reservation_id),
                inventory_item_id=str(reservation.inventory_item_id),
                order_id=str(event.order_id),
            )

    @handle(OrderReturned)
    def on_order_returned(self, event: OrderReturned) -> None:
        """Return items to stock when an order is returned.

        Note: OrderReturned carries returned_item_ids (order item UUIDs),
        not product/variant details needed for stock lookup. Restocking
        requires a separate enrichment step or a query back to the order.
        For now we log the return for auditing.
        """
        logger.info(
            "Order returned — items noted for restocking",
            order_id=str(event.order_id),
            returned_item_ids=event.returned_item_ids,
        )
