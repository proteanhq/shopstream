"""Application tests for OrderDeliveredSubscriber — Reviews reacts to Ordering stream.

Tests the subscriber ACL pattern: raw dict payloads are filtered by event type
and translated into VerifiedPurchases records.
"""

from datetime import UTC, datetime

from protean import current_domain

from reviews.projections.verified_purchases import VerifiedPurchases
from reviews.review.ordering_subscriber import OrderDeliveredSubscriber


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


class TestOrderDeliveredSubscriber:
    def test_creates_verified_purchase_records(self):
        """Happy path: OrderDelivered with customer_id and items creates VP records."""
        payload = _build_message(
            "Ordering.OrderDelivered.v1",
            {
                "order_id": "order-001",
                "customer_id": "cust-001",
                "items": [
                    {"product_id": "prod-001", "variant_id": "var-001"},
                    {"product_id": "prod-002"},
                ],
                "delivered_at": datetime.now(UTC).isoformat(),
            },
        )

        subscriber = OrderDeliveredSubscriber()
        subscriber(payload)

        vps = current_domain.repository_for(VerifiedPurchases).query.filter(customer_id="cust-001").all()
        assert len(vps.items) == 2

    def test_multiple_items_create_separate_records(self):
        """Each item in the order creates a separate VerifiedPurchases record."""
        payload = _build_message(
            "Ordering.OrderDelivered.v1",
            {
                "order_id": "order-multi",
                "customer_id": "cust-multi",
                "items": [
                    {"product_id": "prod-a", "variant_id": "var-a"},
                    {"product_id": "prod-b", "variant_id": "var-b"},
                    {"product_id": "prod-c", "variant_id": "var-c"},
                ],
                "delivered_at": datetime.now(UTC).isoformat(),
            },
        )

        subscriber = OrderDeliveredSubscriber()
        subscriber(payload)

        vps = current_domain.repository_for(VerifiedPurchases).query.filter(customer_id="cust-multi").all()
        assert len(vps.items) == 3

        product_ids = {str(vp.product_id) for vp in vps.items}
        assert product_ids == {"prod-a", "prod-b", "prod-c"}

    def test_skips_when_no_customer_id(self):
        """Missing customer_id in data should be silently skipped."""
        payload = _build_message(
            "Ordering.OrderDelivered.v1",
            {
                "order_id": "order-002",
                "delivered_at": datetime.now(UTC).isoformat(),
            },
        )

        subscriber = OrderDeliveredSubscriber()
        subscriber(payload)

        vps = current_domain.repository_for(VerifiedPurchases).query.filter(order_id="order-002").all()
        assert len(vps.items) == 0

    def test_skips_when_no_items(self):
        """customer_id present but no items should be silently skipped."""
        payload = _build_message(
            "Ordering.OrderDelivered.v1",
            {
                "order_id": "order-003",
                "customer_id": "cust-003",
                "delivered_at": datetime.now(UTC).isoformat(),
            },
        )

        subscriber = OrderDeliveredSubscriber()
        subscriber(payload)

        vps = current_domain.repository_for(VerifiedPurchases).query.filter(order_id="order-003").all()
        assert len(vps.items) == 0

    def test_handles_malformed_items_gracefully(self):
        """Items with missing product_id should be handled gracefully."""
        payload = _build_message(
            "Ordering.OrderDelivered.v1",
            {
                "order_id": "order-004",
                "customer_id": "cust-004",
                "items": [
                    {"variant_id": "var-only"},  # Missing product_id
                ],
                "delivered_at": datetime.now(UTC).isoformat(),
            },
        )

        subscriber = OrderDeliveredSubscriber()
        # Should not crash — the except block catches KeyError
        subscriber(payload)

    def test_ignores_non_order_delivered_events(self):
        """Non-OrderDelivered events on the ordering stream are ignored."""
        payload = _build_message(
            "Ordering.OrderCreated.v1",
            {
                "order_id": "order-005",
                "customer_id": "cust-005",
                "items": [{"product_id": "prod-005"}],
            },
        )

        subscriber = OrderDeliveredSubscriber()
        subscriber(payload)

        vps = current_domain.repository_for(VerifiedPurchases).query.filter(customer_id="cust-005").all()
        assert len(vps.items) == 0

    def test_ignores_payload_without_metadata(self):
        """Payloads missing metadata entirely are ignored."""
        payload = {
            "data": {
                "order_id": "order-006",
                "customer_id": "cust-006",
                "items": [{"product_id": "prod-006"}],
            }
        }

        subscriber = OrderDeliveredSubscriber()
        subscriber(payload)

        vps = current_domain.repository_for(VerifiedPurchases).query.filter(customer_id="cust-006").all()
        assert len(vps.items) == 0
