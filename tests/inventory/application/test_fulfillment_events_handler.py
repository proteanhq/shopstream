"""Application tests for FulfillmentInventoryEventHandler — Inventory reacts to Fulfillment events.

Covers:
- on_shipment_handed_off: commits confirmed reserved stock when shipment leaves warehouse
- on_shipment_handed_off: no-op when no inventory items exist
- on_shipment_handed_off: skips items with no matching reservation
"""

from datetime import UTC, datetime

from inventory.stock.fulfillment_events import FulfillmentInventoryEventHandler
from inventory.stock.initialization import InitializeStock
from inventory.stock.reservation import ConfirmReservation, ReserveStock
from inventory.stock.stock import InventoryItem
from protean import current_domain
from shared.events.fulfillment import ShipmentHandedOff


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


class TestShipmentHandedOffHandler:
    def test_commits_confirmed_reservation_on_handoff(self):
        """When a shipment is handed off, Confirmed reservations should be committed."""
        order_id = "ord-ship-001"
        item_id = _initialize_stock(initial_quantity=100)

        # Reserve and confirm 20 units for the order
        _reserve_and_confirm(item_id, order_id, 20)

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 100
        assert item.levels.reserved == 20
        assert item.levels.available == 80

        # Simulate the event handler receiving ShipmentHandedOff
        handler = FulfillmentInventoryEventHandler()
        handler.on_shipment_handed_off(
            ShipmentHandedOff(
                fulfillment_id="ff-001",
                order_id=order_id,
                carrier="FakeCarrier",
                tracking_number="TRACK-001",
                shipped_at=datetime.now(UTC),
            )
        )

        # After committing, on_hand should decrease and reservation should be cleared
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 80
        assert item.levels.reserved == 0
        assert item.levels.available == 80

    def test_no_inventory_items_is_noop(self):
        """If no inventory items exist, handler returns without error."""
        handler = FulfillmentInventoryEventHandler()
        # Should not raise
        handler.on_shipment_handed_off(
            ShipmentHandedOff(
                fulfillment_id="ff-none",
                order_id="ord-none",
                carrier="FakeCarrier",
                tracking_number="TRACK-NONE",
                shipped_at=datetime.now(UTC),
            )
        )

    def test_skips_items_without_matching_reservation(self):
        """Items with reservations for a different order should not be committed."""
        item_id = _initialize_stock(initial_quantity=50)

        # Reserve and confirm for a different order
        _reserve_and_confirm(item_id, "ord-other", 10)

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 50
        assert item.levels.reserved == 10

        # Fire event for a different order
        handler = FulfillmentInventoryEventHandler()
        handler.on_shipment_handed_off(
            ShipmentHandedOff(
                fulfillment_id="ff-002",
                order_id="ord-ship-002",
                carrier="FakeCarrier",
                tracking_number="TRACK-002",
                shipped_at=datetime.now(UTC),
            )
        )

        # Stock should remain unchanged
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 50
        assert item.levels.reserved == 10
