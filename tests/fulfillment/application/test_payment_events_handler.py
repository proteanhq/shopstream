"""Application tests for PaymentEventsSubscriber — Fulfillment reacts to Payment events.

Covers:
- on_payment_succeeded: logs only (documented limitation — fulfillment creation
  requires order item details not available in the PaymentSucceeded event)
"""

from fulfillment.fulfillment.payment_subscriber import PaymentEventsSubscriber


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


class TestPaymentSucceededHandler:
    def test_payment_succeeded_logs_without_error(self):
        """PaymentSucceeded handler logs info and completes without error.

        The handler is a documented placeholder — in production, the API or saga
        orchestrates fulfillment creation with the full item list.
        """
        subscriber = PaymentEventsSubscriber()
        subscriber(
            _build_message(
                "Payments.PaymentSucceeded.v1",
                {
                    "payment_id": "pay-001",
                    "order_id": "ord-001",
                    "customer_id": "cust-001",
                    "amount": 99.99,
                    "currency": "USD",
                    "gateway_transaction_id": "gw-txn-001",
                },
            )
        )

    def test_payment_succeeded_with_different_orders(self):
        """Handler should work for multiple different orders without error."""
        subscriber = PaymentEventsSubscriber()

        for i in range(3):
            subscriber(
                _build_message(
                    "Payments.PaymentSucceeded.v1",
                    {
                        "payment_id": f"pay-{i:03d}",
                        "order_id": f"ord-{i:03d}",
                        "customer_id": f"cust-{i:03d}",
                        "amount": 50.0 + i * 10,
                        "currency": "USD",
                        "gateway_transaction_id": f"gw-txn-{i:03d}",
                    },
                )
            )


class TestIgnoresUnrelatedEvents:
    def test_ignores_non_payment_succeeded_events(self):
        """Non-PaymentSucceeded events on the payments stream are ignored."""
        subscriber = PaymentEventsSubscriber()
        subscriber(
            _build_message(
                "Payments.PaymentInitiated.v1",
                {"payment_id": "pay-ignore", "order_id": "ord-ignore"},
            )
        )
