"""Tests for all 19 Order events — construction and field completeness."""

from datetime import UTC, datetime

from ordering.order.events import (
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


class TestOrderCreatedEvent:
    def test_version(self):
        assert OrderCreated.__version__ == "v1"

    def test_construction(self):
        now = datetime.now(UTC)
        event = OrderCreated(
            order_id="ord-001",
            customer_id="cust-001",
            items='[{"sku": "S1"}]',
            shipping_address='{"street": "1 St"}',
            billing_address='{"street": "2 St"}',
            subtotal=100.0,
            grand_total=110.0,
            created_at=now,
        )
        assert event.order_id == "ord-001"
        assert event.customer_id == "cust-001"
        assert event.subtotal == 100.0


class TestItemAddedEvent:
    def test_version(self):
        assert ItemAdded.__version__ == "v1"

    def test_construction(self):
        event = ItemAdded(
            order_id="ord-001",
            item_id="item-001",
            product_id="prod-001",
            variant_id="var-001",
            sku="SKU-001",
            title="Test Product",
            quantity="2",
            unit_price="29.99",
            new_subtotal=59.98,
            new_grand_total=65.97,
        )
        assert event.sku == "SKU-001"
        assert event.new_subtotal == 59.98


class TestItemRemovedEvent:
    def test_construction(self):
        event = ItemRemoved(
            order_id="ord-001",
            item_id="item-001",
            new_subtotal=0.0,
            new_grand_total=5.99,
        )
        assert event.item_id == "item-001"


class TestItemQuantityUpdatedEvent:
    def test_construction(self):
        event = ItemQuantityUpdated(
            order_id="ord-001",
            item_id="item-001",
            previous_quantity="1",
            new_quantity="3",
            new_subtotal=75.0,
            new_grand_total=80.0,
        )
        assert event.previous_quantity == "1"
        assert event.new_quantity == "3"


class TestCouponAppliedEvent:
    def test_construction(self):
        event = CouponApplied(order_id="ord-001", coupon_code="SAVE10")
        assert event.coupon_code == "SAVE10"


class TestOrderConfirmedEvent:
    def test_construction(self):
        now = datetime.now(UTC)
        event = OrderConfirmed(order_id="ord-001", confirmed_at=now)
        assert event.confirmed_at == now


class TestPaymentPendingEvent:
    def test_construction(self):
        event = PaymentPending(order_id="ord-001", payment_id="pay-001", payment_method="credit_card")
        assert event.payment_method == "credit_card"


class TestPaymentSucceededEvent:
    def test_construction(self):
        event = PaymentSucceeded(order_id="ord-001", payment_id="pay-001", amount=100.0, payment_method="credit_card")
        assert event.amount == 100.0


class TestPaymentFailedEvent:
    def test_construction(self):
        event = PaymentFailed(order_id="ord-001", payment_id="pay-001", reason="Card declined")
        assert event.reason == "Card declined"


class TestOrderProcessingEvent:
    def test_construction(self):
        now = datetime.now(UTC)
        event = OrderProcessing(order_id="ord-001", started_at=now)
        assert event.started_at == now


class TestOrderShippedEvent:
    def test_construction(self):
        now = datetime.now(UTC)
        event = OrderShipped(
            order_id="ord-001",
            shipment_id="ship-001",
            carrier="FedEx",
            tracking_number="TRACK-001",
            shipped_at=now,
        )
        assert event.carrier == "FedEx"


class TestOrderPartiallyShippedEvent:
    def test_construction(self):
        now = datetime.now(UTC)
        event = OrderPartiallyShipped(
            order_id="ord-001",
            shipment_id="ship-001",
            carrier="FedEx",
            tracking_number="TRACK-P",
            shipped_item_ids='["item-001"]',
            shipped_at=now,
        )
        assert event.shipped_item_ids == '["item-001"]'


class TestOrderDeliveredEvent:
    def test_construction(self):
        now = datetime.now(UTC)
        event = OrderDelivered(order_id="ord-001", delivered_at=now)
        assert event.delivered_at == now


class TestOrderCompletedEvent:
    def test_construction(self):
        now = datetime.now(UTC)
        event = OrderCompleted(order_id="ord-001", completed_at=now)
        assert event.completed_at == now


class TestReturnRequestedEvent:
    def test_construction(self):
        now = datetime.now(UTC)
        event = ReturnRequested(order_id="ord-001", reason="Defective", requested_at=now)
        assert event.reason == "Defective"


class TestReturnApprovedEvent:
    def test_construction(self):
        now = datetime.now(UTC)
        event = ReturnApproved(order_id="ord-001", approved_at=now)
        assert event.approved_at == now


class TestOrderReturnedEvent:
    def test_construction(self):
        now = datetime.now(UTC)
        event = OrderReturned(order_id="ord-001", returned_item_ids='["item-001"]', returned_at=now)
        assert event.returned_item_ids == '["item-001"]'


class TestOrderCancelledEvent:
    def test_construction(self):
        now = datetime.now(UTC)
        event = OrderCancelled(order_id="ord-001", reason="Changed mind", cancelled_by="Customer", cancelled_at=now)
        assert event.cancelled_by == "Customer"


class TestOrderRefundedEvent:
    def test_construction(self):
        now = datetime.now(UTC)
        event = OrderRefunded(order_id="ord-001", refund_amount=50.0, refunded_at=now)
        assert event.refund_amount == 50.0
