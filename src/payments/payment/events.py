"""Domain events for the Payment aggregate.

All events are versioned, immutable facts representing payment state changes.
Events are persisted to the event store and used for:
- Rebuilding aggregate state via @apply (event sourcing)
- Updating projections via projectors
- Cross-domain communication via Redis Streams (consumed by OrderCheckoutSaga)
"""

from protean.fields import Boolean, DateTime, Float, Identifier, Integer, String

from payments.domain import payments


@payments.event(part_of="Payment")
class PaymentInitiated:
    """A new payment was created for an order."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    amount = Float(required=True)
    currency = String(required=True)
    payment_method_type = String(required=True)
    last4 = String()
    gateway_name = String(required=True)
    idempotency_key = String(required=True)
    initiated_at = DateTime(required=True)


@payments.event(part_of="Payment")
class PaymentSucceeded:
    """Payment was successfully captured by the gateway."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    amount = Float(required=True)
    currency = String(required=True)
    gateway_transaction_id = String(required=True)
    succeeded_at = DateTime(required=True)


@payments.event(part_of="Payment")
class PaymentFailed:
    """Payment processing failed at the gateway."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    reason = String(required=True)
    attempt_number = Integer(required=True)
    can_retry = Boolean(required=True)
    failed_at = DateTime(required=True)


@payments.event(part_of="Payment")
class PaymentRetryInitiated:
    """A failed payment is being retried."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    order_id = Identifier(required=True)
    attempt_number = Integer(required=True)
    retried_at = DateTime(required=True)


@payments.event(part_of="Payment")
class RefundRequested:
    """A refund was requested for a successful payment."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    refund_id = Identifier(required=True)
    order_id = Identifier(required=True)
    amount = Float(required=True)
    reason = String(required=True)
    requested_at = DateTime(required=True)


@payments.event(part_of="Payment")
class RefundCompleted:
    """A refund was completed by the gateway."""

    __version__ = "v1"

    payment_id = Identifier(required=True)
    refund_id = Identifier(required=True)
    order_id = Identifier(required=True)
    amount = Float(required=True)
    gateway_refund_id = String(required=True)
    completed_at = DateTime(required=True)
