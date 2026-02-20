"""Cross-domain event contracts for Payments domain events.

These classes define the event shape for consumption by other domains
(e.g., the OrderCheckoutSaga in the ordering domain). They are registered
as external events via domain.register_external_event() with matching
__type__ strings so Protean's stream deserialization works correctly.

The source-of-truth events are in src/payments/payment/events.py.
"""

from protean.core.event import BaseEvent
from protean.fields import Boolean, DateTime, Float, Identifier, Integer, String


class PaymentSucceeded(BaseEvent):
    """Payment was successfully captured by the gateway."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    amount = Float(required=True)
    currency = String(required=True)
    gateway_transaction_id = String(required=True)
    succeeded_at = DateTime(required=True)


class PaymentFailed(BaseEvent):
    """Payment processing failed at the gateway."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    reason = String(required=True)
    attempt_number = Integer(required=True)
    can_retry = Boolean(required=True)
    failed_at = DateTime(required=True)
