"""Application tests for PaymentFulfillmentEventHandler — Fulfillment reacts to Payment events.

Covers:
- on_payment_succeeded: logs only (documented limitation — fulfillment creation
  requires order item details not available in the PaymentSucceeded event)
"""

from datetime import UTC, datetime

from fulfillment.fulfillment.payment_events import PaymentFulfillmentEventHandler
from shared.events.payments import PaymentSucceeded


class TestPaymentSucceededHandler:
    def test_payment_succeeded_logs_without_error(self):
        """PaymentSucceeded handler logs info and completes without error.

        The handler is a documented placeholder — in production, the API or saga
        orchestrates fulfillment creation with the full item list.
        """
        handler = PaymentFulfillmentEventHandler()
        handler.on_payment_succeeded(
            PaymentSucceeded(
                payment_id="pay-001",
                order_id="ord-001",
                customer_id="cust-001",
                amount=99.99,
                currency="USD",
                gateway_transaction_id="gw-txn-001",
                succeeded_at=datetime.now(UTC),
            )
        )

    def test_payment_succeeded_with_different_orders(self):
        """Handler should work for multiple different orders without error."""
        handler = PaymentFulfillmentEventHandler()

        for i in range(3):
            handler.on_payment_succeeded(
                PaymentSucceeded(
                    payment_id=f"pay-{i:03d}",
                    order_id=f"ord-{i:03d}",
                    customer_id=f"cust-{i:03d}",
                    amount=50.0 + i * 10,
                    currency="USD",
                    gateway_transaction_id=f"gw-txn-{i:03d}",
                    succeeded_at=datetime.now(UTC),
                )
            )
