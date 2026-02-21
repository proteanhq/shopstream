"""Application tests for cross-domain OrderDelivered event handler."""

import json
from datetime import UTC, datetime

from protean import current_domain
from reviews.projections.verified_purchases import VerifiedPurchases
from reviews.review.ordering_events import OrderingEventsHandler
from shared.events.ordering import OrderDelivered


class TestOrderDeliveredHandler:
    def test_creates_verified_purchase_records(self):
        event = OrderDelivered(
            order_id="order-001",
            customer_id="cust-001",
            items=json.dumps(
                [
                    {"product_id": "prod-001", "variant_id": "var-001"},
                    {"product_id": "prod-002"},
                ]
            ),
            delivered_at=datetime.now(UTC),
        )

        handler = OrderingEventsHandler()
        handler.on_order_delivered(event)

        vps = current_domain.repository_for(VerifiedPurchases)._dao.query.filter(customer_id="cust-001").all()
        assert len(vps.items) == 2

    def test_skips_when_no_customer_id(self):
        event = OrderDelivered(
            order_id="order-002",
            delivered_at=datetime.now(UTC),
        )
        handler = OrderingEventsHandler()
        handler.on_order_delivered(event)
        # Should not raise, just log and skip
        vps = current_domain.repository_for(VerifiedPurchases)._dao.query.filter(order_id="order-002").all()
        assert len(vps.items) == 0

    def test_skips_when_no_items(self):
        event = OrderDelivered(
            order_id="order-003",
            customer_id="cust-003",
            delivered_at=datetime.now(UTC),
        )
        handler = OrderingEventsHandler()
        handler.on_order_delivered(event)
        # Should log and skip, no records created
        vps = current_domain.repository_for(VerifiedPurchases)._dao.query.filter(order_id="order-003").all()
        assert len(vps.items) == 0

    def test_handles_malformed_items_gracefully(self):
        """Items with missing product_id should be handled gracefully."""
        event = OrderDelivered(
            order_id="order-004",
            customer_id="cust-004",
            items=json.dumps(
                [
                    {"variant_id": "var-only"},  # Missing product_id
                ]
            ),
            delivered_at=datetime.now(UTC),
        )
        handler = OrderingEventsHandler()
        handler.on_order_delivered(event)
        # Should not crash, the except block in the handler catches KeyError
