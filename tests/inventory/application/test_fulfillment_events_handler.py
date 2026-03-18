"""Application tests for FulfillmentEventsSubscriber — Inventory reacts to Fulfillment events.

Tests the subscriber ACL pattern: raw dict payloads are filtered by event type
and translated into CommitStock commands.

Covers:
- ShipmentHandedOff: commits confirmed reserved stock when shipment leaves warehouse
- ShipmentHandedOff: no-op when no inventory items exist
- ShipmentHandedOff: skips items with no matching reservation
"""

from datetime import UTC, datetime

from protean import current_domain

from inventory.stock.fulfillment_subscriber import FulfillmentEventsSubscriber
from inventory.stock.initialization import InitializeStock
from inventory.stock.reservation import ConfirmReservation, ReserveStock
from inventory.stock.stock import InventoryItem


def _build_message(event_type: str, data: dict) -> dict:
    """Build a broker message payload with metadata and data."""
    return {
        "data": data,
        "metadata": {"headers": {"type": event_type}},
    }


def _initialize_stock(**overrides):
    defaults = {
        "product_id": "prod-001",
        "variant_id": "var-001",
        "warehouse_id": "wh-001",
        "sku": "TSHIRT-BLK-M",
        "initial_quantity": 100,
        "reorder_point": 10,
        "reorder_quantity": 50,
    }
    defaults.update(overrides)
    return current_domain.process(InitializeStock(**defaults), asynchronous=False)


def _reserve_and_confirm(item_id, order_id, quantity):
    """Reserve and confirm stock for an order (Confirmed status)."""
    current_domain.process(
        ReserveStock(inventory_item_id=item_id, order_id=order_id, quantity=quantity),
        asynchronous=False,
    )
    item = current_domain.repository_for(InventoryItem).get(item_id)
    reservation = next(r for r in item.reservations if str(r.order_id) == order_id)
    current_domain.process(
        ConfirmReservation(inventory_item_id=item_id, reservation_id=str(reservation.id)),
        asynchronous=False,
    )


class TestShipmentHandedOffSubscriber:
    def test_commits_confirmed_reservation_on_handoff(self):
        """When a shipment is handed off, Confirmed reservations should be committed."""
        order_id = "ord-ship-001"
        item_id = _initialize_stock(initial_quantity=100)

        _reserve_and_confirm(item_id, order_id, 20)

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 100
        assert item.levels.reserved == 20
        assert item.levels.available == 80

        subscriber = FulfillmentEventsSubscriber()
        subscriber(
            _build_message(
                "Fulfillment.ShipmentHandedOff.v1",
                {
                    "fulfillment_id": "ff-001",
                    "order_id": order_id,
                    "carrier": "FakeCarrier",
                    "tracking_number": "TRACK-001",
                    "shipped_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 80
        assert item.levels.reserved == 0
        assert item.levels.available == 80

    def test_no_inventory_items_is_noop(self):
        """If no inventory items exist, subscriber returns without error."""
        subscriber = FulfillmentEventsSubscriber()
        subscriber(
            _build_message(
                "Fulfillment.ShipmentHandedOff.v1",
                {
                    "fulfillment_id": "ff-none",
                    "order_id": "ord-none",
                    "carrier": "FakeCarrier",
                    "tracking_number": "TRACK-NONE",
                    "shipped_at": datetime.now(UTC).isoformat(),
                },
            )
        )

    def test_skips_items_without_matching_reservation(self):
        """Items with reservations for a different order should not be committed."""
        item_id = _initialize_stock(initial_quantity=50)

        _reserve_and_confirm(item_id, "ord-other", 10)

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 50
        assert item.levels.reserved == 10

        subscriber = FulfillmentEventsSubscriber()
        subscriber(
            _build_message(
                "Fulfillment.ShipmentHandedOff.v1",
                {
                    "fulfillment_id": "ff-002",
                    "order_id": "ord-ship-002",
                    "carrier": "FakeCarrier",
                    "tracking_number": "TRACK-002",
                    "shipped_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 50
        assert item.levels.reserved == 10

    def test_ignores_non_shipment_events(self):
        """Non-ShipmentHandedOff events on the fulfillment stream are ignored."""
        subscriber = FulfillmentEventsSubscriber()
        subscriber(
            _build_message(
                "Fulfillment.PickerAssigned.v1",
                {
                    "fulfillment_id": "ff-ignore",
                    "picker_name": "Alice",
                },
            )
        )

    def test_handles_reservation_query_failure(self):
        """When the ReservationStatus query fails, handler treats it as no reservations."""
        from unittest.mock import MagicMock, patch

        subscriber = FulfillmentEventsSubscriber()
        with patch("inventory.stock.fulfillment_subscriber.current_domain") as mock_domain:
            mock_view = MagicMock()
            mock_view.query.filter.side_effect = Exception("DB connection error")
            mock_domain.view_for.return_value = mock_view

            subscriber(
                _build_message(
                    "Fulfillment.ShipmentHandedOff.v1",
                    {
                        "fulfillment_id": "ff-err",
                        "order_id": "ord-err",
                        "carrier": "FakeCarrier",
                        "tracking_number": "TRACK-ERR",
                    },
                )
            )
