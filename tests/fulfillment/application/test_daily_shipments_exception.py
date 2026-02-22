"""Mock-based tests for DailyShipmentsView projector exception branches.

Covers the ObjectNotFoundError branch in _get_or_create (line 41) where
repo.get() fails and a new DailyShipmentsView record is created instead.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from fulfillment.fulfillment.events import (
    DeliveryConfirmed,
    DeliveryException,
    FulfillmentCreated,
    ShipmentHandedOff,
)
from fulfillment.projections.daily_shipments import (
    DailyShipmentsProjector,
    _get_or_create,
)
from protean.exceptions import ObjectNotFoundError


class TestDailyShipmentsGetOrCreate:
    """When _get_or_create encounters ObjectNotFoundError, it should create a new view."""

    def test_creates_new_view_when_not_found(self):
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "DailyShipmentsView not found"})
        now = datetime.now(UTC)

        with patch("fulfillment.projections.daily_shipments.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            view = _get_or_create("2026-02-15", now)

        assert view is not None
        assert view.date == "2026-02-15"
        assert view.total_created == 0
        assert view.total_shipped == 0
        assert view.total_delivered == 0
        assert view.total_exceptions == 0
        assert view.updated_at == now

    def test_on_fulfillment_created_creates_view_when_not_found(self):
        projector = DailyShipmentsProjector()
        now = datetime.now(UTC)
        event = FulfillmentCreated(
            fulfillment_id="ful-new-001",
            order_id="ord-001",
            customer_id="cust-001",
            items="[]",
            item_count=2,
            created_at=now,
        )
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "DailyShipmentsView not found"})

        with patch("fulfillment.projections.daily_shipments.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            projector.on_fulfillment_created(event)
            # repo.add should be called to persist the newly created+updated view
            mock_repo.add.assert_called_once()
            saved_view = mock_repo.add.call_args[0][0]
            assert saved_view.total_created == 1

    def test_on_shipment_handed_off_creates_view_when_not_found(self):
        projector = DailyShipmentsProjector()
        now = datetime.now(UTC)
        event = ShipmentHandedOff(
            fulfillment_id="ful-new-002",
            order_id="ord-002",
            carrier="UPS",
            tracking_number="1Z999AA10123456784",
            shipped_at=now,
        )
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "DailyShipmentsView not found"})

        with patch("fulfillment.projections.daily_shipments.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            projector.on_shipment_handed_off(event)
            mock_repo.add.assert_called_once()
            saved_view = mock_repo.add.call_args[0][0]
            assert saved_view.total_shipped == 1

    def test_on_delivery_confirmed_creates_view_when_not_found(self):
        projector = DailyShipmentsProjector()
        now = datetime.now(UTC)
        event = DeliveryConfirmed(
            fulfillment_id="ful-new-003",
            order_id="ord-003",
            actual_delivery=now,
            delivered_at=now,
        )
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "DailyShipmentsView not found"})

        with patch("fulfillment.projections.daily_shipments.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            projector.on_delivery_confirmed(event)
            mock_repo.add.assert_called_once()
            saved_view = mock_repo.add.call_args[0][0]
            assert saved_view.total_delivered == 1

    def test_on_delivery_exception_creates_view_when_not_found(self):
        projector = DailyShipmentsProjector()
        now = datetime.now(UTC)
        event = DeliveryException(
            fulfillment_id="ful-new-004",
            order_id="ord-004",
            reason="Address not found",
            occurred_at=now,
        )
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "DailyShipmentsView not found"})

        with patch("fulfillment.projections.daily_shipments.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            projector.on_delivery_exception(event)
            mock_repo.add.assert_called_once()
            saved_view = mock_repo.add.call_args[0][0]
            assert saved_view.total_exceptions == 1
