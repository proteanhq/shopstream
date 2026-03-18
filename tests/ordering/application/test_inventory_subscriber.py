"""Application tests for InventoryEventsSubscriber — Ordering reacts to Inventory events.

Tests the subscriber ACL pattern: raw dict payloads are filtered by event type
and translated into domain commands (RecordPaymentPending, CancelOrder).
"""

from protean import current_domain

from ordering.checkout.inventory_subscriber import InventoryEventsSubscriber
from ordering.order.cancellation import CancelOrder
from ordering.order.confirmation import ConfirmOrder
from ordering.order.creation import CreateOrder
from ordering.order.order import Order, OrderStatus
from ordering.order.payment import RecordPaymentPending, RecordPaymentSuccess


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


def _create_confirmed_order():
    """Create an order in CONFIRMED state."""
    order_id = current_domain.process(
        CreateOrder(
            customer_id="cust-001",
            items=[
                {
                    "product_id": "prod-001",
                    "variant_id": "var-001",
                    "sku": "SKU-001",
                    "title": "Widget",
                    "quantity": 1,
                    "unit_price": 25.0,
                },
            ],
            shipping_address={
                "street": "123 Main",
                "city": "Town",
                "state": "CA",
                "postal_code": "90210",
                "country": "US",
            },
            billing_address={
                "street": "123 Main",
                "city": "Town",
                "state": "CA",
                "postal_code": "90210",
                "country": "US",
            },
            subtotal=25.0,
            grand_total=27.5,
        ),
        asynchronous=False,
    )
    current_domain.process(ConfirmOrder(order_id=order_id), asynchronous=False)
    return order_id


class TestStockReservedSubscriber:
    def test_stock_reserved_dispatches_record_payment_pending(self):
        """StockReserved event should transition order to PAYMENT_PENDING."""
        order_id = _create_confirmed_order()

        subscriber = InventoryEventsSubscriber()
        subscriber(
            _build_message(
                "Inventory.StockReserved.v1",
                {
                    "order_id": order_id,
                    "reservation_id": "res-001",
                    "sku": "SKU-001",
                    "quantity": 1,
                },
            )
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PAYMENT_PENDING.value
        assert order.payment_id == f"saga-pay-{order_id}"
        assert order.payment_method == "credit_card"

    def test_stock_reserved_skips_when_no_order_id(self):
        """StockReserved with no order_id in data should be silently ignored."""
        subscriber = InventoryEventsSubscriber()
        # Should not raise
        subscriber(
            _build_message(
                "Inventory.StockReserved.v1",
                {
                    "reservation_id": "res-001",
                    "sku": "SKU-001",
                    "quantity": 5,
                },
            )
        )

    def test_stock_reserved_handles_already_transitioned(self):
        """StockReserved on an already-PAID order should not raise (ValidationError caught)."""
        order_id = _create_confirmed_order()

        # Walk order to PAID state
        current_domain.process(
            RecordPaymentPending(order_id=order_id, payment_id="pay-001", payment_method="credit_card"),
            asynchronous=False,
        )
        current_domain.process(
            RecordPaymentSuccess(
                order_id=order_id,
                payment_id="pay-001",
                amount=27.5,
                payment_method="credit_card",
            ),
            asynchronous=False,
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PAID.value

        subscriber = InventoryEventsSubscriber()
        # Should not raise — ValidationError is caught internally
        subscriber(
            _build_message(
                "Inventory.StockReserved.v1",
                {"order_id": order_id, "reservation_id": "res-002"},
            )
        )

        # Order should still be PAID
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.PAID.value


class TestReservationReleasedSubscriber:
    def test_reservation_released_dispatches_cancel_order(self):
        """ReservationReleased event should cancel the order."""
        order_id = _create_confirmed_order()

        subscriber = InventoryEventsSubscriber()
        subscriber(
            _build_message(
                "Inventory.ReservationReleased.v1",
                {
                    "order_id": order_id,
                    "reason": "Stock depleted",
                },
            )
        )

        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CANCELLED.value
        assert order.cancellation_reason == "Inventory reservation released: Stock depleted"
        assert order.cancelled_by == "System"

    def test_reservation_released_skips_when_no_order_id(self):
        """ReservationReleased with no order_id in data should be silently ignored."""
        subscriber = InventoryEventsSubscriber()
        # Should not raise
        subscriber(
            _build_message(
                "Inventory.ReservationReleased.v1",
                {"reason": "Stock depleted"},
            )
        )

    def test_reservation_released_handles_already_cancelled(self):
        """ReservationReleased on an already-CANCELLED order should not raise."""
        order_id = _create_confirmed_order()

        # Cancel the order first
        current_domain.process(
            CancelOrder(order_id=order_id, reason="Customer request", cancelled_by="Customer"),
            asynchronous=False,
        )
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CANCELLED.value

        subscriber = InventoryEventsSubscriber()
        # Should not raise — ValidationError is caught internally
        subscriber(
            _build_message(
                "Inventory.ReservationReleased.v1",
                {"order_id": order_id, "reason": "Stock depleted"},
            )
        )

        # Order should still be CANCELLED
        order = current_domain.repository_for(Order).get(order_id)
        assert order.status == OrderStatus.CANCELLED.value


class TestStockReservedValidationErrorCaught:
    def test_catches_validation_error_on_payment_pending(self):
        """When domain.process raises ValidationError, it's caught and logged."""
        from unittest.mock import MagicMock, patch

        from protean.exceptions import ValidationError

        subscriber = InventoryEventsSubscriber()
        mock_domain = MagicMock()
        mock_domain.process = MagicMock(side_effect=ValidationError({"order": "Already transitioned"}))
        with patch("ordering.checkout.inventory_subscriber.current_domain", mock_domain):
            subscriber(
                _build_message(
                    "Inventory.StockReserved.v1",
                    {"order_id": "ord-err-001", "reservation_id": "res-001"},
                )
            )
            mock_domain.process.assert_called_once()


class TestReservationReleasedValidationErrorCaught:
    def test_catches_validation_error_on_cancel_order(self):
        """When domain.process raises ValidationError on CancelOrder, it's caught."""
        from unittest.mock import MagicMock, patch

        from protean.exceptions import ValidationError

        subscriber = InventoryEventsSubscriber()
        mock_domain = MagicMock()
        mock_domain.process = MagicMock(side_effect=ValidationError({"order": "Already cancelled"}))
        with patch("ordering.checkout.inventory_subscriber.current_domain", mock_domain):
            subscriber(
                _build_message(
                    "Inventory.ReservationReleased.v1",
                    {"order_id": "ord-err-002", "reason": "timeout"},
                )
            )
            mock_domain.process.assert_called_once()


class TestInventorySubscriberIgnoresUnrelated:
    def test_ignores_unrelated_events(self):
        """Events that are neither StockReserved nor ReservationReleased should be ignored."""
        subscriber = InventoryEventsSubscriber()
        # Should not raise or have any effect
        subscriber(
            _build_message(
                "Inventory.StockInitialized.v1",
                {
                    "order_id": "order-999",
                    "sku": "SKU-001",
                    "quantity": 100,
                },
            )
        )
