"""Inbound cross-domain event handler — Payments reacts to Ordering events.

Listens for OrderReturned events from the Ordering domain to automatically
initiate a refund for the returned order's payment.

Cross-domain events are imported from shared.events.ordering and registered
as external events via payments.register_external_event().
"""

import structlog
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from payments.domain import payments
from payments.payment.payment import Payment
from payments.projections.payment_status import PaymentStatusView
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
payments.register_external_event(OrderCreated, "Ordering.OrderCreated.v1")
payments.register_external_event(ItemAdded, "Ordering.ItemAdded.v1")
payments.register_external_event(ItemRemoved, "Ordering.ItemRemoved.v1")
payments.register_external_event(ItemQuantityUpdated, "Ordering.ItemQuantityUpdated.v1")
payments.register_external_event(CouponApplied, "Ordering.CouponApplied.v1")
payments.register_external_event(OrderConfirmed, "Ordering.OrderConfirmed.v1")
payments.register_external_event(PaymentPending, "Ordering.PaymentPending.v1")
payments.register_external_event(PaymentSucceeded, "Ordering.PaymentSucceeded.v1")
payments.register_external_event(PaymentFailed, "Ordering.PaymentFailed.v1")
payments.register_external_event(OrderProcessing, "Ordering.OrderProcessing.v1")
payments.register_external_event(OrderShipped, "Ordering.OrderShipped.v1")
payments.register_external_event(OrderPartiallyShipped, "Ordering.OrderPartiallyShipped.v1")
payments.register_external_event(OrderDelivered, "Ordering.OrderDelivered.v1")
payments.register_external_event(OrderCompleted, "Ordering.OrderCompleted.v1")
payments.register_external_event(ReturnRequested, "Ordering.ReturnRequested.v1")
payments.register_external_event(ReturnApproved, "Ordering.ReturnApproved.v1")
payments.register_external_event(OrderReturned, "Ordering.OrderReturned.v1")
payments.register_external_event(OrderCancelled, "Ordering.OrderCancelled.v1")
payments.register_external_event(OrderRefunded, "Ordering.OrderRefunded.v1")


@payments.event_handler(part_of=Payment, stream_category="ordering::order")
class OrderingPaymentEventHandler:
    """Reacts to Ordering domain events to process refunds."""

    @handle(OrderReturned)
    def on_order_returned(self, event: OrderReturned) -> None:
        """Initiate a refund when an order is returned."""
        logger.info(
            "Initiating refund for returned order",
            order_id=str(event.order_id),
        )

        # Find the payment for this order
        payment_records = (
            current_domain.view_for(PaymentStatusView)
            .query.filter(
                order_id=str(event.order_id),
                status="Succeeded",
            )
            .all()
            .items
        )

        if not payment_records:
            logger.info(
                "No succeeded payment found for returned order",
                order_id=str(event.order_id),
            )
            return

        payment_record = payment_records[0]

        from payments.payment.refund import RequestRefund

        current_domain.process(
            RequestRefund(
                payment_id=str(payment_record.payment_id),
                amount=payment_record.amount,
                reason=f"Order returned: {event.order_id}",
            ),
            asynchronous=False,
        )
        logger.info(
            "Refund initiated for returned order",
            payment_id=str(payment_record.payment_id),
            order_id=str(event.order_id),
        )
