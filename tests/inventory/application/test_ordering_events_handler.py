"""Application tests for OrderingInventoryEventHandler — Inventory reacts to Ordering events.

Covers:
- on_order_cancelled: releases active reservations for the cancelled order
- on_order_cancelled: no-op when no reservations exist
- on_order_returned: restocks items when an order is returned
- on_order_returned: no-op with empty items
"""

import json
from datetime import UTC, datetime

from inventory.projections.inventory_level import InventoryLevel
from inventory.projections.reservation_status import ReservationStatus as ReservationStatusProjection
from inventory.stock.initialization import InitializeStock
from inventory.stock.ordering_events import OrderingInventoryEventHandler
from inventory.stock.reservation import ConfirmReservation, ReserveStock
from inventory.stock.stock import InventoryItem
from protean import current_domain
from shared.events.ordering import OrderCancelled, OrderReturned


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


def _reserve_stock(item_id, order_id, quantity):
    """Reserve stock for an order (Active status)."""
    current_domain.process(
        ReserveStock(inventory_item_id=item_id, order_id=order_id, quantity=quantity),
        asynchronous=False,
    )


def _reserve_and_confirm(item_id, order_id, quantity):
    """Reserve and confirm stock for an order (Confirmed status)."""
    _reserve_stock(item_id, order_id, quantity)
    item = current_domain.repository_for(InventoryItem).get(item_id)
    reservation = next(r for r in item.reservations if str(r.order_id) == order_id)
    current_domain.process(
        ConfirmReservation(inventory_item_id=item_id, reservation_id=str(reservation.id)),
        asynchronous=False,
    )


class TestOrderCancelledHandler:
    def test_releases_active_reservation_on_cancellation(self):
        """When an order is cancelled, active reservations should be released."""
        order_id = "ord-cancel-001"
        item_id = _initialize_stock(initial_quantity=100)

        # Reserve 20 units for the order (Active status)
        _reserve_stock(item_id, order_id, 20)

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.reserved == 20
        assert item.levels.available == 80

        # Verify the ReservationStatus projection shows Active
        reservation = next(r for r in item.reservations if str(r.order_id) == order_id)
        res_proj = current_domain.repository_for(ReservationStatusProjection).get(str(reservation.id))
        assert res_proj.status == "Active"

        # Handle OrderCancelled event
        handler = OrderingInventoryEventHandler()
        handler.on_order_cancelled(
            OrderCancelled(
                order_id=order_id,
                reason="Customer requested",
                cancelled_by="Customer",
                cancelled_at=datetime.now(UTC),
            )
        )

        # After release, reservation should be released and stock should be available
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.reserved == 0
        assert item.levels.available == 100

        # Check the reservation entity was marked Released
        released = next(r for r in item.reservations if str(r.order_id) == order_id)
        status = released.status.value if hasattr(released.status, "value") else released.status
        assert status == "Released"

    def test_does_not_release_already_released_reservations(self):
        """Reservations that are already released should not be affected."""
        order_id = "ord-cancel-released"
        item_id = _initialize_stock(initial_quantity=100)

        # Reserve 10 units and then release them manually
        _reserve_stock(item_id, order_id, 10)
        item = current_domain.repository_for(InventoryItem).get(item_id)
        reservation = next(r for r in item.reservations if str(r.order_id) == order_id)

        from inventory.stock.reservation import ReleaseReservation

        current_domain.process(
            ReleaseReservation(
                inventory_item_id=item_id,
                reservation_id=str(reservation.id),
                reason="manual release",
            ),
            asynchronous=False,
        )

        # Verify released
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.reserved == 0
        assert item.levels.available == 100

        # Now cancel the order -- should be a no-op since reservation is already released
        handler = OrderingInventoryEventHandler()
        handler.on_order_cancelled(
            OrderCancelled(
                order_id=order_id,
                reason="System timeout",
                cancelled_by="System",
                cancelled_at=datetime.now(UTC),
            )
        )

        # Stock should remain unchanged
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.reserved == 0
        assert item.levels.available == 100

    def test_no_reservations_is_noop(self):
        """If no reservations exist for the order, handler logs and returns without error."""
        handler = OrderingInventoryEventHandler()
        # Should not raise
        handler.on_order_cancelled(
            OrderCancelled(
                order_id="ord-no-reservations",
                reason="Customer requested",
                cancelled_by="Customer",
                cancelled_at=datetime.now(UTC),
            )
        )


class TestOrderReturnedHandler:
    def test_restocks_items_on_return(self):
        """When an order is returned, items should be restocked."""
        item_id = _initialize_stock(
            product_id="prod-ret-001",
            variant_id="var-ret-001",
            initial_quantity=50,
        )

        # Verify initial state via InventoryLevel projection
        inv_level = current_domain.repository_for(InventoryLevel).get(item_id)
        assert inv_level.on_hand == 50
        assert inv_level.available == 50

        handler = OrderingInventoryEventHandler()
        handler.on_order_returned(
            OrderReturned(
                order_id="ord-ret-001",
                customer_id="cust-001",
                items=json.dumps([{"product_id": "prod-ret-001", "variant_id": "var-ret-001", "quantity": 5}]),
                returned_at=datetime.now(UTC),
            )
        )

        # Stock should increase by the returned quantity
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 55
        assert item.levels.available == 55

    def test_empty_items_is_noop(self):
        """If the return event has no items, handler logs and returns without error."""
        handler = OrderingInventoryEventHandler()
        # Should not raise
        handler.on_order_returned(
            OrderReturned(
                order_id="ord-ret-empty",
                customer_id="cust-001",
                items="[]",
                returned_at=datetime.now(UTC),
            )
        )

    def test_no_items_field_is_noop(self):
        """If the return event has no items field, handler logs and returns without error."""
        handler = OrderingInventoryEventHandler()
        # Should not raise
        handler.on_order_returned(
            OrderReturned(
                order_id="ord-ret-none",
                returned_at=datetime.now(UTC),
            )
        )
