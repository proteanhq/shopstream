"""Shared BDD fixtures and step definitions for the Inventory domain."""

from datetime import UTC, datetime, timedelta

import pytest
from inventory.stock.adjustment import AdjustStock, RecordStockCheck
from inventory.stock.damage import MarkDamaged, WriteOffDamaged
from inventory.stock.events import (
    DamagedStockWrittenOff,
    LowStockDetected,
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
from inventory.stock.initialization import InitializeStock
from inventory.stock.receiving import ReceiveStock
from inventory.stock.reservation import ConfirmReservation, ReleaseReservation, ReserveStock
from inventory.stock.returns import ReturnToStock
from inventory.stock.shipping import CommitStock
from inventory.stock.stock import InventoryItem
from protean.exceptions import ValidationError
from protean.testing import given as given_
from pytest_bdd import given, parsers, then

# Map event name strings to classes for dynamic lookup in Then steps
_INVENTORY_EVENT_CLASSES = {
    "StockInitialized": StockInitialized,
    "StockReceived": StockReceived,
    "StockReserved": StockReserved,
    "ReservationReleased": ReservationReleased,
    "ReservationConfirmed": ReservationConfirmed,
    "StockCommitted": StockCommitted,
    "StockAdjusted": StockAdjusted,
    "StockMarkedDamaged": StockMarkedDamaged,
    "DamagedStockWrittenOff": DamagedStockWrittenOff,
    "StockReturned": StockReturned,
    "StockCheckRecorded": StockCheckRecorded,
    "LowStockDetected": LowStockDetected,
}


# ---------------------------------------------------------------------------
# Scalar fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def inventory_item_id():
    return "inv-001"


@pytest.fixture()
def reservation_id():
    return "res-001"


# ---------------------------------------------------------------------------
# Event fixtures (past tense — what happened)
# ---------------------------------------------------------------------------
@pytest.fixture()
def stock_initialized(inventory_item_id):
    return StockInitialized(
        inventory_item_id=inventory_item_id,
        product_id="prod-001",
        variant_id="var-001",
        warehouse_id="wh-001",
        sku="TSHIRT-BLK-M",
        initial_quantity=100,
        reorder_point=10,
        reorder_quantity=50,
        initialized_at=datetime.now(UTC),
    )


@pytest.fixture()
def stock_initialized_low(inventory_item_id):
    """Stock initialized with low quantity — at reorder point."""
    return StockInitialized(
        inventory_item_id=inventory_item_id,
        product_id="prod-001",
        variant_id="var-001",
        warehouse_id="wh-001",
        sku="TSHIRT-BLK-M",
        initial_quantity=5,
        reorder_point=10,
        reorder_quantity=50,
        initialized_at=datetime.now(UTC),
    )


@pytest.fixture()
def stock_received(inventory_item_id):
    return StockReceived(
        inventory_item_id=inventory_item_id,
        quantity=50,
        previous_on_hand=100,
        new_on_hand=150,
        new_available=150,
        received_at=datetime.now(UTC),
    )


@pytest.fixture()
def stock_reserved(inventory_item_id, reservation_id):
    return StockReserved(
        inventory_item_id=inventory_item_id,
        reservation_id=reservation_id,
        order_id="ord-001",
        quantity=10,
        previous_available=100,
        new_available=90,
        reserved_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )


@pytest.fixture()
def reservation_confirmed(inventory_item_id, reservation_id):
    return ReservationConfirmed(
        inventory_item_id=inventory_item_id,
        reservation_id=reservation_id,
        order_id="ord-001",
        quantity=10,
        confirmed_at=datetime.now(UTC),
    )


@pytest.fixture()
def reservation_released(inventory_item_id, reservation_id):
    return ReservationReleased(
        inventory_item_id=inventory_item_id,
        reservation_id=reservation_id,
        order_id="ord-001",
        quantity=10,
        reason="Customer cancelled",
        previous_available=90,
        new_available=100,
        released_at=datetime.now(UTC),
    )


@pytest.fixture()
def stock_committed(inventory_item_id, reservation_id):
    return StockCommitted(
        inventory_item_id=inventory_item_id,
        reservation_id=reservation_id,
        order_id="ord-001",
        quantity=10,
        previous_on_hand=100,
        new_on_hand=90,
        previous_reserved=10,
        new_reserved=0,
        committed_at=datetime.now(UTC),
    )


@pytest.fixture()
def stock_adjusted_down(inventory_item_id):
    return StockAdjusted(
        inventory_item_id=inventory_item_id,
        product_id="prod-001",
        adjustment_type="Shrinkage",
        quantity_change=-10,
        reason="Inventory shrinkage",
        adjusted_by="manager-001",
        previous_on_hand=100,
        new_on_hand=90,
        new_available=90,
        adjusted_at=datetime.now(UTC),
    )


@pytest.fixture()
def stock_marked_damaged(inventory_item_id):
    return StockMarkedDamaged(
        inventory_item_id=inventory_item_id,
        product_id="prod-001",
        quantity=5,
        reason="Water damage",
        previous_on_hand=100,
        new_on_hand=95,
        previous_damaged=0,
        new_damaged=5,
        new_available=95,
        marked_at=datetime.now(UTC),
    )


@pytest.fixture()
def damaged_stock_written_off(inventory_item_id):
    return DamagedStockWrittenOff(
        inventory_item_id=inventory_item_id,
        product_id="prod-001",
        quantity=3,
        approved_by="manager-001",
        previous_damaged=5,
        new_damaged=2,
        written_off_at=datetime.now(UTC),
    )


@pytest.fixture()
def stock_returned(inventory_item_id):
    return StockReturned(
        inventory_item_id=inventory_item_id,
        quantity=10,
        order_id="ord-ret-001",
        previous_on_hand=100,
        new_on_hand=110,
        new_available=110,
        returned_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Command fixtures (imperative — what to do)
# ---------------------------------------------------------------------------
@pytest.fixture()
def initialize_stock():
    return InitializeStock(
        product_id="prod-001",
        variant_id="var-001",
        warehouse_id="wh-001",
        sku="TSHIRT-BLK-M",
        initial_quantity=100,
        reorder_point=10,
        reorder_quantity=50,
    )


@pytest.fixture()
def receive_stock(inventory_item_id):
    return ReceiveStock(
        inventory_item_id=inventory_item_id,
        quantity=50,
    )


@pytest.fixture()
def reserve_stock(inventory_item_id):
    return ReserveStock(
        inventory_item_id=inventory_item_id,
        order_id="ord-001",
        quantity=10,
    )


@pytest.fixture()
def release_reservation(inventory_item_id, reservation_id):
    return ReleaseReservation(
        inventory_item_id=inventory_item_id,
        reservation_id=reservation_id,
        reason="Customer cancelled",
    )


@pytest.fixture()
def confirm_reservation(inventory_item_id, reservation_id):
    return ConfirmReservation(
        inventory_item_id=inventory_item_id,
        reservation_id=reservation_id,
    )


@pytest.fixture()
def commit_stock(inventory_item_id, reservation_id):
    return CommitStock(
        inventory_item_id=inventory_item_id,
        reservation_id=reservation_id,
    )


@pytest.fixture()
def adjust_stock_down(inventory_item_id):
    return AdjustStock(
        inventory_item_id=inventory_item_id,
        quantity_change=-10,
        adjustment_type="Shrinkage",
        reason="Inventory shrinkage",
        adjusted_by="manager-001",
    )


@pytest.fixture()
def adjust_stock_up(inventory_item_id):
    return AdjustStock(
        inventory_item_id=inventory_item_id,
        quantity_change=10,
        adjustment_type="Correction",
        reason="Correction from audit",
        adjusted_by="manager-001",
    )


@pytest.fixture()
def record_stock_check(inventory_item_id):
    return RecordStockCheck(
        inventory_item_id=inventory_item_id,
        counted_quantity=95,
        checked_by="checker-001",
    )


@pytest.fixture()
def mark_damaged(inventory_item_id):
    return MarkDamaged(
        inventory_item_id=inventory_item_id,
        quantity=5,
        reason="Water damage",
    )


@pytest.fixture()
def write_off_damaged(inventory_item_id):
    return WriteOffDamaged(
        inventory_item_id=inventory_item_id,
        quantity=3,
        approved_by="manager-001",
    )


@pytest.fixture()
def return_to_stock(inventory_item_id):
    return ReturnToStock(
        inventory_item_id=inventory_item_id,
        quantity=10,
        order_id="ord-ret-001",
    )


# ---------------------------------------------------------------------------
# Given steps — InventoryItem (event sourcing via protean.testing)
# ---------------------------------------------------------------------------
@given("stock was initialized", target_fixture="item")
def _(stock_initialized):
    return given_(InventoryItem, stock_initialized)


@given("stock was initialized with low quantity", target_fixture="item")
def _(stock_initialized_low):
    return given_(InventoryItem, stock_initialized_low)


@given("stock was received", target_fixture="item")
def _(item, stock_received):
    return item.after(stock_received)


@given("stock was reserved", target_fixture="item")
def _(item, stock_reserved):
    return item.after(stock_reserved)


@given("the reservation was confirmed", target_fixture="item")
def _(item, reservation_confirmed):
    return item.after(reservation_confirmed)


@given("the reservation was released", target_fixture="item")
def _(item, reservation_released):
    return item.after(reservation_released)


@given("stock was committed", target_fixture="item")
def _(item, stock_committed):
    return item.after(stock_committed)


@given("stock was adjusted down", target_fixture="item")
def _(item, stock_adjusted_down):
    return item.after(stock_adjusted_down)


@given("stock was marked damaged", target_fixture="item")
def _(item, stock_marked_damaged):
    return item.after(stock_marked_damaged)


@given("damaged stock was written off", target_fixture="item")
def _(item, damaged_stock_written_off):
    return item.after(damaged_stock_written_off)


@given("stock was returned", target_fixture="item")
def _(item, stock_returned):
    return item.after(stock_returned)


# ---------------------------------------------------------------------------
# Then steps — shared assertions
# ---------------------------------------------------------------------------
@then(parsers.cfparse("the on-hand quantity is {qty:d}"))
def _(item, qty):
    assert item.levels.on_hand == qty


@then(parsers.cfparse("the reserved quantity is {qty:d}"))
def _(item, qty):
    assert item.levels.reserved == qty


@then(parsers.cfparse("the available quantity is {qty:d}"))
def _(item, qty):
    assert item.levels.available == qty


@then(parsers.cfparse("the damaged quantity is {qty:d}"))
def _(item, qty):
    assert item.levels.damaged == qty


@then("the action fails with a validation error")
def _(item):
    assert item.rejected
    assert isinstance(item.rejection, ValidationError)


@then(parsers.cfparse("a {event_type} event is raised"))
def _(item, event_type):
    event_cls = _INVENTORY_EVENT_CLASSES[event_type]
    assert event_cls in item.events


@then(parsers.cfparse("an {event_type} event is raised"))
def _(item, event_type):
    event_cls = _INVENTORY_EVENT_CLASSES[event_type]
    assert event_cls in item.events
