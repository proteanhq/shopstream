"""Stock movement log — append-only audit trail of all stock changes."""

import uuid
from datetime import datetime

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.events import (
    DamagedStockWrittenOff,
    ReservationConfirmed,
    ReservationReleased,
    StockAdjusted,
    StockCheckRecorded,
    StockCommitted,
    StockInitialized,
    StockMarkedDamaged,
    StockReceived,
    StockReserved,
    StockReturned,
)
from inventory.stock.stock import InventoryItem


@inventory.projection
class StockMovementLog:
    entry_id: str = Identifier(identifier=True, required=True)
    inventory_item_id: str = Identifier(required=True)
    event_type: str = String(required=True)
    description: str = String(required=True)
    quantity_change: int = Integer(default=0)
    previous_level: int = Integer(default=0)
    new_level: int = Integer(default=0)
    actor: str | None = String()
    occurred_at: datetime = DateTime(required=True)


def _add_entry(
    inventory_item_id: str,
    event_type: str,
    description: str,
    occurred_at: datetime,
    quantity_change: int = 0,
    previous_level: int = 0,
    new_level: int = 0,
    actor: str | None = None,
) -> None:
    current_domain.repository_for(StockMovementLog).add(
        StockMovementLog(
            entry_id=str(uuid.uuid4()),
            inventory_item_id=inventory_item_id,
            event_type=event_type,
            description=description,
            quantity_change=quantity_change,
            previous_level=previous_level,
            new_level=new_level,
            actor=actor,
            occurred_at=occurred_at,
        )
    )


@inventory.projector(projector_for=StockMovementLog, aggregates=[InventoryItem])
class StockMovementLogProjector:
    @on(StockInitialized)
    def on_stock_initialized(self, event: StockInitialized) -> None:
        _add_entry(
            event.inventory_item_id,
            "StockInitialized",
            f"Stock initialized for SKU {event.sku} with {event.initial_quantity} units",
            event.initialized_at,
            quantity_change=event.initial_quantity,
            new_level=event.initial_quantity,
        )

    @on(StockReceived)
    def on_stock_received(self, event: StockReceived) -> None:
        _add_entry(
            event.inventory_item_id,
            "StockReceived",
            f"Received {event.quantity} units",
            event.received_at,
            quantity_change=event.quantity,
            previous_level=event.previous_on_hand,
            new_level=event.new_on_hand,
        )

    @on(StockReserved)
    def on_stock_reserved(self, event: StockReserved) -> None:
        _add_entry(
            event.inventory_item_id,
            "StockReserved",
            f"Reserved {event.quantity} units for order {event.order_id}",
            event.reserved_at,
            quantity_change=-event.quantity,
            previous_level=event.previous_available,
            new_level=event.new_available,
        )

    @on(ReservationReleased)
    def on_reservation_released(self, event: ReservationReleased) -> None:
        _add_entry(
            event.inventory_item_id,
            "ReservationReleased",
            f"Released {event.quantity} units ({event.reason})",
            event.released_at,
            quantity_change=event.quantity,
            previous_level=event.previous_available,
            new_level=event.new_available,
        )

    @on(ReservationConfirmed)
    def on_reservation_confirmed(self, event: ReservationConfirmed) -> None:
        _add_entry(
            event.inventory_item_id,
            "ReservationConfirmed",
            f"Confirmed reservation for order {event.order_id}",
            event.confirmed_at,
        )

    @on(StockCommitted)
    def on_stock_committed(self, event: StockCommitted) -> None:
        _add_entry(
            event.inventory_item_id,
            "StockCommitted",
            f"Committed {event.quantity} units for order {event.order_id}",
            event.committed_at,
            quantity_change=-event.quantity,
            previous_level=event.previous_on_hand,
            new_level=event.new_on_hand,
        )

    @on(StockAdjusted)
    def on_stock_adjusted(self, event: StockAdjusted) -> None:
        _add_entry(
            event.inventory_item_id,
            "StockAdjusted",
            f"Adjusted by {event.quantity_change}: {event.reason}",
            event.adjusted_at,
            quantity_change=event.quantity_change,
            previous_level=event.previous_on_hand,
            new_level=event.new_on_hand,
            actor=event.adjusted_by,
        )

    @on(StockMarkedDamaged)
    def on_stock_marked_damaged(self, event: StockMarkedDamaged) -> None:
        _add_entry(
            event.inventory_item_id,
            "StockMarkedDamaged",
            f"Marked {event.quantity} units as damaged: {event.reason}",
            event.marked_at,
            quantity_change=-event.quantity,
            previous_level=event.previous_on_hand,
            new_level=event.new_on_hand,
        )

    @on(DamagedStockWrittenOff)
    def on_damaged_stock_written_off(self, event: DamagedStockWrittenOff) -> None:
        _add_entry(
            event.inventory_item_id,
            "DamagedStockWrittenOff",
            f"Written off {event.quantity} damaged units",
            event.written_off_at,
            quantity_change=-event.quantity,
            previous_level=event.previous_damaged,
            new_level=event.new_damaged,
            actor=event.approved_by,
        )

    @on(StockReturned)
    def on_stock_returned(self, event: StockReturned) -> None:
        _add_entry(
            event.inventory_item_id,
            "StockReturned",
            f"Returned {event.quantity} units from order {event.order_id}",
            event.returned_at,
            quantity_change=event.quantity,
            previous_level=event.previous_on_hand,
            new_level=event.new_on_hand,
        )

    @on(StockCheckRecorded)
    def on_stock_check_recorded(self, event: StockCheckRecorded) -> None:
        _add_entry(
            event.inventory_item_id,
            "StockCheckRecorded",
            f"Physical count: {event.counted_quantity} (expected {event.expected_quantity}, discrepancy {event.discrepancy})",
            event.checked_at,
            quantity_change=event.discrepancy,
            previous_level=event.expected_quantity,
            new_level=event.counted_quantity,
            actor=event.checked_by,
        )
