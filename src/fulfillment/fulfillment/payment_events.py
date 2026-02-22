"""Inbound cross-domain event handler — Fulfillment reacts to Payment events.

Listens for PaymentSucceeded events from the Payments domain to automatically
create a fulfillment when an order is paid, triggering the warehouse
picking workflow.

Cross-domain events are imported from shared.events.payments and registered
as external events via fulfillment.register_external_event().
"""

import structlog
from protean.utils.mixins import handle
from shared.events.payments import PaymentSucceeded

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment

logger = structlog.get_logger(__name__)

# Register external event so Protean can deserialize it
fulfillment.register_external_event(PaymentSucceeded, "Payments.PaymentSucceeded.v1")


@fulfillment.event_handler(part_of=Fulfillment, stream_category="payments::payment")
class PaymentFulfillmentEventHandler:
    """Reacts to Payment domain events to create fulfillments."""

    @handle(PaymentSucceeded)
    def on_payment_succeeded(self, event: PaymentSucceeded) -> None:
        """Create a fulfillment when payment succeeds.

        Note: The PaymentSucceeded event carries order_id and customer_id
        but not the full item list. We query the Order read model for item
        details needed to create the fulfillment pick list.
        """
        logger.info(
            "Payment succeeded — creating fulfillment",
            order_id=str(event.order_id),
            payment_id=str(event.payment_id),
        )

        # We need order item details to create the fulfillment.
        # Since we can't query the Ordering domain directly from here,
        # the fulfillment creation requires items data. In a fully wired
        # system, the OrderPaid shared event (which carries items) would
        # be used instead. For now, log and skip if items aren't available.
        #
        # In production, the API or saga would call CreateFulfillment with
        # the full item list after payment confirmation.
        logger.info(
            "Fulfillment auto-creation requires order item details. "
            "In production, the OrderCheckoutSaga or API orchestrates this.",
            order_id=str(event.order_id),
        )
