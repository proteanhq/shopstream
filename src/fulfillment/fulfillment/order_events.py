"""Inbound cross-domain event handler — Fulfillment reacts to Ordering events.

Listens for OrderCancelled events from the Ordering domain to cancel
in-progress fulfillments. Fulfillment creation is triggered via the API
(CreateFulfillment command) rather than by event, because the event handler
would need order item details that aren't available in payment events.

Cross-domain events are imported from shared.events module and registered
as external events via fulfillment.register_external_event().
"""

import structlog
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment
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
fulfillment.register_external_event(OrderCreated, "Ordering.OrderCreated.v1")
fulfillment.register_external_event(ItemAdded, "Ordering.ItemAdded.v1")
fulfillment.register_external_event(ItemRemoved, "Ordering.ItemRemoved.v1")
fulfillment.register_external_event(ItemQuantityUpdated, "Ordering.ItemQuantityUpdated.v1")
fulfillment.register_external_event(CouponApplied, "Ordering.CouponApplied.v1")
fulfillment.register_external_event(OrderConfirmed, "Ordering.OrderConfirmed.v1")
fulfillment.register_external_event(PaymentPending, "Ordering.PaymentPending.v1")
fulfillment.register_external_event(PaymentSucceeded, "Ordering.PaymentSucceeded.v1")
fulfillment.register_external_event(PaymentFailed, "Ordering.PaymentFailed.v1")
fulfillment.register_external_event(OrderProcessing, "Ordering.OrderProcessing.v1")
fulfillment.register_external_event(OrderShipped, "Ordering.OrderShipped.v1")
fulfillment.register_external_event(OrderPartiallyShipped, "Ordering.OrderPartiallyShipped.v1")
fulfillment.register_external_event(OrderDelivered, "Ordering.OrderDelivered.v1")
fulfillment.register_external_event(OrderCompleted, "Ordering.OrderCompleted.v1")
fulfillment.register_external_event(ReturnRequested, "Ordering.ReturnRequested.v1")
fulfillment.register_external_event(ReturnApproved, "Ordering.ReturnApproved.v1")
fulfillment.register_external_event(OrderReturned, "Ordering.OrderReturned.v1")
fulfillment.register_external_event(OrderCancelled, "Ordering.OrderCancelled.v1")
fulfillment.register_external_event(OrderRefunded, "Ordering.OrderRefunded.v1")


@fulfillment.event_handler(part_of=Fulfillment, stream_category="ordering::order")
class OrderEventHandler:
    """Reacts to events from the Ordering domain."""

    @handle(OrderCancelled)
    def on_order_cancelled(self, event: OrderCancelled) -> None:
        """Cancel in-progress fulfillment when order is cancelled."""
        repo = current_domain.repository_for(Fulfillment)

        # Find fulfillment by order_id
        results = repo.query.filter(order_id=str(event.order_id)).all()
        if not results or not results.items:
            logger.info(
                "No fulfillment found for cancelled order",
                order_id=str(event.order_id),
            )
            return

        ff = results.first
        # Only cancel if still cancellable
        from fulfillment.fulfillment.fulfillment import _CANCELLABLE_STATUSES, FulfillmentStatus

        if FulfillmentStatus(ff.status) in _CANCELLABLE_STATUSES:
            ff.cancel(reason=f"Order cancelled: {event.reason}")
            repo.add(ff)
            logger.info(
                "Fulfillment cancelled due to order cancellation",
                fulfillment_id=str(ff.id),
                order_id=str(event.order_id),
            )
        else:
            logger.warning(
                "Cannot cancel fulfillment — already shipped",
                fulfillment_id=str(ff.id),
                order_id=str(event.order_id),
                status=ff.status,
            )
