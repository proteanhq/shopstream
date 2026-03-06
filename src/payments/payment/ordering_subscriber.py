"""Inbound cross-domain subscriber — Payments reacts to Ordering stream.

Listens for OrderReturned messages from the Ordering domain's broker stream
to automatically initiate a refund for the returned order's payment.

Uses the subscriber (ACL) pattern: receives raw dict payloads from the broker,
filters by event type, and dispatches a RequestRefund command.
No dependency on shared event classes or register_external_event.
"""

import structlog
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.projections.payment_status import PaymentStatusView

logger = structlog.get_logger(__name__)


@payments.subscriber(stream="ordering::order")
class OrderReturnedSubscriber:
    """Reacts to OrderReturned events to initiate refunds.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, looks up the succeeded payment for the order,
    and dispatches a RequestRefund command. Ignores all other event types.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        if "OrderReturned" not in event_type:
            return

        data = payload.get("data", {})
        order_id = str(data["order_id"])

        logger.info(
            "Initiating refund for returned order",
            order_id=order_id,
        )

        # Find the payment for this order
        payment_records = (
            current_domain.view_for(PaymentStatusView)
            .query.filter(
                order_id=order_id,
                status="Succeeded",
            )
            .all()
            .items
        )

        if not payment_records:
            logger.info(
                "No succeeded payment found for returned order",
                order_id=order_id,
            )
            return

        payment_record = payment_records[0]

        from payments.payment.refund import RequestRefund

        current_domain.process(
            RequestRefund(
                payment_id=str(payment_record.payment_id),
                amount=payment_record.amount,
                reason=f"Order returned: {order_id}",
            ),
            asynchronous=False,
        )

        logger.info(
            "Refund initiated for returned order",
            payment_id=str(payment_record.payment_id),
            order_id=order_id,
        )
