"""Inbound cross-domain subscriber — Ordering reacts to Payment events.

Listens for PaymentSucceeded and PaymentFailed events from the Payments
domain's external bus and translates them into Ordering domain commands.

This subscriber replaces the direct stream subscription that the
OrderCheckoutSaga previously had to payments::payment. The saga now
reacts only to internal ordering events.

Flow:
- PaymentSucceeded → dispatches RecordPaymentSuccess
- PaymentFailed → dispatches RecordPaymentFailure
"""

from typing import Any

import structlog
from protean.exceptions import ValidationError
from protean.utils.globals import current_domain

from ordering.domain import ordering
from shared.money import parse_money

logger = structlog.get_logger(__name__)


@ordering.subscriber(broker="global", stream="payments::payment")
class PaymentEventsSubscriber:
    """Translates Payment domain events into Ordering domain commands.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and dispatches domain commands. Ignores all
    event types not relevant to the Ordering domain's checkout flow.
    """

    def __call__(self, payload: dict[str, Any]) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "PaymentSucceeded" in event_type:
            self._on_payment_succeeded(data)
        elif "PaymentFailed" in event_type:
            self._on_payment_failed(data)

    def _on_payment_succeeded(self, data: dict[str, Any]) -> None:
        """Payment succeeded — record success on the order."""
        order_id = data.get("order_id")
        if not order_id:
            return

        try:
            amount = parse_money(data["amount"]) if data.get("amount") is not None else None
        except ValueError:
            amount = None
        if amount is None:
            # A message without a readable amount is malformed. Recording it
            # would mark the order paid with an amount nobody charged.
            logger.warning(
                "PaymentSucceeded has no readable amount; leaving the order pending",
                order_id=str(order_id),
                amount=repr(data.get("amount")),
            )
            return

        logger.info(
            "Payment succeeded for order — recording success",
            order_id=str(order_id),
            payment_id=str(data.get("payment_id", "")),
        )

        from ordering.order.payment import RecordPaymentSuccess

        try:
            current_domain.process(
                RecordPaymentSuccess(
                    order_id=order_id,
                    payment_id=data.get("payment_id", ""),
                    amount=amount,
                    payment_method="credit_card",
                ),
                asynchronous=False,
            )
        except ValidationError:
            logger.info(
                "Order %s already transitioned; skipping RecordPaymentSuccess",
                order_id,
            )

    def _on_payment_failed(self, data: dict[str, Any]) -> None:
        """Payment failed — record failure on the order.

        The order transitions back to Confirmed, allowing the saga to
        track retries and eventually cancel if max retries exceeded.
        """
        order_id = data.get("order_id")
        if not order_id:
            return

        reason = data.get("reason", "Payment failed")
        logger.info(
            "Payment failed for order — recording failure",
            order_id=str(order_id),
            reason=reason,
        )

        from ordering.order.payment import RecordPaymentFailure

        try:
            current_domain.process(
                RecordPaymentFailure(
                    order_id=order_id,
                    payment_id=data.get("payment_id", ""),
                    reason=reason,
                ),
                asynchronous=False,
            )
        except ValidationError:
            logger.info(
                "Order %s already transitioned; skipping RecordPaymentFailure",
                order_id,
            )
