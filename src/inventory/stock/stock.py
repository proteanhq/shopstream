"""InventoryItem aggregate (Event Sourced) — the core of the inventory domain.

The InventoryItem aggregate uses event sourcing: all state changes are captured
as domain events, and the current state is rebuilt by replaying events via
@apply decorators. This provides a complete audit trail for stock movements,
temporal queries for reconciliation, and reliable concurrent reservation handling.

Stock Level Model:
    on_hand:   Physical count in the warehouse
    reserved:  Held for orders (not yet shipped)
    available: on_hand - reserved (what can be sold)
    in_transit: Ordered from supplier (not yet received)
    damaged:   Write-off pending
"""

from datetime import UTC, datetime, timedelta
from enum import Enum
from uuid import uuid4

from protean import apply
from protean.exceptions import ValidationError
from protean.fields import (
    DateTime,
    HasMany,
    Identifier,
    Integer,
    String,
    ValueObject,
)

from inventory.domain import inventory
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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class ReservationStatus(Enum):
    ACTIVE = "Active"
    CONFIRMED = "Confirmed"
    RELEASED = "Released"
    EXPIRED = "Expired"


class AdjustmentType(Enum):
    COUNT = "Count"
    SHRINKAGE = "Shrinkage"
    CORRECTION = "Correction"
    RECEIVING_ERROR = "Receiving_Error"


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------
@inventory.value_object(part_of="InventoryItem")
class StockLevels:
    """Tracks all stock quantities.

    Available is always equal to on_hand - reserved. It is denormalized
    here for query convenience.
    """

    on_hand = Integer(default=0)
    reserved = Integer(default=0)
    available = Integer(default=0)
    in_transit = Integer(default=0)
    damaged = Integer(default=0)


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
@inventory.entity(part_of="InventoryItem")
class Reservation:
    """A hold on inventory for a specific order.

    Reservations transition through: ACTIVE → CONFIRMED → (committed via
    CommitStock), or ACTIVE → RELEASED (cancelled/expired).
    """

    order_id = Identifier(required=True)
    quantity = Integer(required=True, min_value=1)
    status = String(
        choices=ReservationStatus,
        default=ReservationStatus.ACTIVE.value,
    )
    reserved_at = DateTime(required=True)
    expires_at = DateTime(required=True)


# ---------------------------------------------------------------------------
# Aggregate Root (Event Sourced)
# ---------------------------------------------------------------------------
@inventory.aggregate(is_event_sourced=True)
class InventoryItem:
    """Event-sourced aggregate tracking stock for one product variant at one warehouse."""

    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    warehouse_id = Identifier(required=True)
    sku = String(required=True, max_length=50)
    levels = ValueObject(StockLevels)
    reorder_point = Integer(default=10)
    reorder_quantity = Integer(default=50)
    reservations = HasMany(Reservation)
    last_stock_check = DateTime()
    created_at = DateTime()
    updated_at = DateTime()

    # -------------------------------------------------------------------
    # Factory method
    # -------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        product_id,
        variant_id,
        warehouse_id,
        sku,
        initial_quantity=0,
        reorder_point=10,
        reorder_quantity=50,
    ):
        """Create a new inventory record for a product variant at a warehouse.

        Uses _create_new() to get a blank aggregate with auto-generated
        identity. All state is established by the StockInitialized event's
        @apply handler.
        """
        item = cls._create_new()
        item.raise_(
            StockInitialized(
                inventory_item_id=str(item.id),
                product_id=str(product_id),
                variant_id=str(variant_id),
                warehouse_id=str(warehouse_id),
                sku=sku,
                initial_quantity=initial_quantity,
                reorder_point=reorder_point,
                reorder_quantity=reorder_quantity,
                initialized_at=datetime.now(UTC),
            )
        )
        return item

    # -------------------------------------------------------------------
    # Helper
    # -------------------------------------------------------------------
    def _check_low_stock(self):
        """Raise LowStockDetected if available is at or below reorder point."""
        if self.levels and self.levels.available <= self.reorder_point:
            self.raise_(
                LowStockDetected(
                    inventory_item_id=str(self.id),
                    product_id=str(self.product_id),
                    variant_id=str(self.variant_id),
                    sku=self.sku,
                    current_available=self.levels.available,
                    reorder_point=self.reorder_point,
                    detected_at=datetime.now(UTC),
                )
            )

    # -------------------------------------------------------------------
    # Stock receiving
    # -------------------------------------------------------------------
    def receive_stock(self, quantity, reference=None):
        """Receive stock into the warehouse."""
        if quantity <= 0:
            raise ValidationError({"quantity": ["Quantity must be positive"]})

        prev_on_hand = self.levels.on_hand if self.levels else 0
        new_on_hand = prev_on_hand + quantity
        reserved = self.levels.reserved if self.levels else 0
        new_available = new_on_hand - reserved

        self.raise_(
            StockReceived(
                inventory_item_id=str(self.id),
                quantity=quantity,
                previous_on_hand=prev_on_hand,
                new_on_hand=new_on_hand,
                new_available=new_available,
                reference=reference,
                received_at=datetime.now(UTC),
            )
        )

    # -------------------------------------------------------------------
    # Reservations
    # -------------------------------------------------------------------
    def reserve(self, order_id, quantity, expires_at=None):
        """Reserve stock for an order."""
        if quantity <= 0:
            raise ValidationError({"quantity": ["Quantity must be positive"]})

        available = self.levels.available if self.levels else 0
        if available < quantity:
            raise ValidationError({"quantity": [f"Insufficient stock: {available} available, {quantity} requested"]})

        if expires_at is None:
            expires_at = datetime.now(UTC) + timedelta(minutes=15)

        reservation_id = str(uuid4())
        new_available = available - quantity

        reservation = Reservation(
            id=reservation_id,
            order_id=order_id,
            quantity=quantity,
            reserved_at=datetime.now(UTC),
            expires_at=expires_at,
        )
        self.add_reservations(reservation)

        self.raise_(
            StockReserved(
                inventory_item_id=str(self.id),
                reservation_id=reservation_id,
                order_id=str(order_id),
                quantity=quantity,
                previous_available=available,
                new_available=new_available,
                reserved_at=datetime.now(UTC),
                expires_at=expires_at,
            )
        )
        self._check_low_stock()

    def release_reservation(self, reservation_id, reason):
        """Release a reservation, returning stock to available."""
        reservation = next(
            (r for r in (self.reservations or []) if str(r.id) == str(reservation_id)),
            None,
        )
        if reservation is None:
            raise ValidationError({"reservation_id": ["Reservation not found"]})

        if ReservationStatus(reservation.status) != ReservationStatus.ACTIVE:
            raise ValidationError({"reservation_id": [f"Cannot release reservation in {reservation.status} state"]})

        available = self.levels.available if self.levels else 0
        new_available = available + reservation.quantity

        reservation.status = ReservationStatus.RELEASED.value

        self.raise_(
            ReservationReleased(
                inventory_item_id=str(self.id),
                reservation_id=str(reservation_id),
                order_id=str(reservation.order_id),
                quantity=reservation.quantity,
                reason=reason,
                previous_available=available,
                new_available=new_available,
                released_at=datetime.now(UTC),
            )
        )

    def confirm_reservation(self, reservation_id):
        """Confirm a reservation after order payment."""
        reservation = next(
            (r for r in (self.reservations or []) if str(r.id) == str(reservation_id)),
            None,
        )
        if reservation is None:
            raise ValidationError({"reservation_id": ["Reservation not found"]})

        if ReservationStatus(reservation.status) != ReservationStatus.ACTIVE:
            raise ValidationError({"reservation_id": [f"Cannot confirm reservation in {reservation.status} state"]})

        reservation.status = ReservationStatus.CONFIRMED.value

        self.raise_(
            ReservationConfirmed(
                inventory_item_id=str(self.id),
                reservation_id=str(reservation_id),
                order_id=str(reservation.order_id),
                quantity=reservation.quantity,
                confirmed_at=datetime.now(UTC),
            )
        )

    # -------------------------------------------------------------------
    # Stock commitment (shipping)
    # -------------------------------------------------------------------
    def commit_stock(self, reservation_id):
        """Commit reserved stock when an order ships. Reduces on-hand."""
        reservation = next(
            (r for r in (self.reservations or []) if str(r.id) == str(reservation_id)),
            None,
        )
        if reservation is None:
            raise ValidationError({"reservation_id": ["Reservation not found"]})

        if ReservationStatus(reservation.status) != ReservationStatus.CONFIRMED:
            raise ValidationError({"reservation_id": ["Only confirmed reservations can be committed"]})

        prev_on_hand = self.levels.on_hand if self.levels else 0
        prev_reserved = self.levels.reserved if self.levels else 0

        self.raise_(
            StockCommitted(
                inventory_item_id=str(self.id),
                reservation_id=str(reservation_id),
                order_id=str(reservation.order_id),
                quantity=reservation.quantity,
                previous_on_hand=prev_on_hand,
                new_on_hand=prev_on_hand - reservation.quantity,
                previous_reserved=prev_reserved,
                new_reserved=prev_reserved - reservation.quantity,
                committed_at=datetime.now(UTC),
            )
        )

    # -------------------------------------------------------------------
    # Stock adjustment
    # -------------------------------------------------------------------
    def adjust_stock(self, quantity_change, adjustment_type, reason, adjusted_by):
        """Manually adjust stock levels."""
        if not reason:
            raise ValidationError({"reason": ["Reason is required for stock adjustments"]})

        prev_on_hand = self.levels.on_hand if self.levels else 0
        new_on_hand = prev_on_hand + quantity_change
        if new_on_hand < 0:
            raise ValidationError({"quantity_change": [f"Adjustment would result in negative on-hand: {new_on_hand}"]})

        reserved = self.levels.reserved if self.levels else 0
        new_available = new_on_hand - reserved

        self.raise_(
            StockAdjusted(
                inventory_item_id=str(self.id),
                adjustment_type=adjustment_type,
                quantity_change=quantity_change,
                reason=reason,
                adjusted_by=adjusted_by,
                previous_on_hand=prev_on_hand,
                new_on_hand=new_on_hand,
                new_available=new_available,
                adjusted_at=datetime.now(UTC),
            )
        )
        self._check_low_stock()

    def record_stock_check(self, counted_quantity, checked_by):
        """Record a physical stock count."""
        expected = self.levels.on_hand if self.levels else 0
        discrepancy = counted_quantity - expected

        self.raise_(
            StockCheckRecorded(
                inventory_item_id=str(self.id),
                counted_quantity=counted_quantity,
                expected_quantity=expected,
                discrepancy=discrepancy,
                checked_by=checked_by,
                checked_at=datetime.now(UTC),
            )
        )

        # Auto-adjust if there's a discrepancy
        if discrepancy != 0:
            self.adjust_stock(
                quantity_change=discrepancy,
                adjustment_type=AdjustmentType.COUNT.value,
                reason=f"Stock check adjustment: counted {counted_quantity}, expected {expected}",
                adjusted_by=checked_by,
            )

    # -------------------------------------------------------------------
    # Damage tracking
    # -------------------------------------------------------------------
    def mark_damaged(self, quantity, reason):
        """Flag stock as damaged. Moves from on-hand to damaged."""
        if quantity <= 0:
            raise ValidationError({"quantity": ["Quantity must be positive"]})
        if not reason:
            raise ValidationError({"reason": ["Reason is required"]})

        on_hand = self.levels.on_hand if self.levels else 0
        reserved = self.levels.reserved if self.levels else 0
        unreserved = on_hand - reserved

        if quantity > unreserved:
            raise ValidationError({"quantity": [f"Cannot damage more than unreserved stock: {unreserved} available"]})

        prev_damaged = self.levels.damaged if self.levels else 0
        new_on_hand = on_hand - quantity
        new_available = new_on_hand - reserved

        self.raise_(
            StockMarkedDamaged(
                inventory_item_id=str(self.id),
                quantity=quantity,
                reason=reason,
                previous_on_hand=on_hand,
                new_on_hand=new_on_hand,
                previous_damaged=prev_damaged,
                new_damaged=prev_damaged + quantity,
                new_available=new_available,
                marked_at=datetime.now(UTC),
            )
        )
        self._check_low_stock()

    def write_off_damaged(self, quantity, approved_by):
        """Write off damaged stock (remove from inventory)."""
        if quantity <= 0:
            raise ValidationError({"quantity": ["Quantity must be positive"]})

        damaged = self.levels.damaged if self.levels else 0
        if quantity > damaged:
            raise ValidationError({"quantity": [f"Cannot write off more than damaged: {damaged} damaged"]})

        self.raise_(
            DamagedStockWrittenOff(
                inventory_item_id=str(self.id),
                quantity=quantity,
                approved_by=approved_by,
                previous_damaged=damaged,
                new_damaged=damaged - quantity,
                written_off_at=datetime.now(UTC),
            )
        )

    # -------------------------------------------------------------------
    # Returns
    # -------------------------------------------------------------------
    def return_to_stock(self, quantity, order_id):
        """Add returned items back to on-hand inventory."""
        if quantity <= 0:
            raise ValidationError({"quantity": ["Quantity must be positive"]})

        prev_on_hand = self.levels.on_hand if self.levels else 0
        new_on_hand = prev_on_hand + quantity
        reserved = self.levels.reserved if self.levels else 0
        new_available = new_on_hand - reserved

        self.raise_(
            StockReturned(
                inventory_item_id=str(self.id),
                quantity=quantity,
                order_id=str(order_id),
                previous_on_hand=prev_on_hand,
                new_on_hand=new_on_hand,
                new_available=new_available,
                returned_at=datetime.now(UTC),
            )
        )

    # -------------------------------------------------------------------
    # @apply methods — rebuild state during event replay
    # -------------------------------------------------------------------
    @apply
    def _on_stock_initialized(self, event: StockInitialized):
        self.id = event.inventory_item_id
        self.product_id = event.product_id
        self.variant_id = event.variant_id
        self.warehouse_id = event.warehouse_id
        self.sku = event.sku
        self.reorder_point = event.reorder_point
        self.reorder_quantity = event.reorder_quantity
        self.levels = StockLevels(
            on_hand=event.initial_quantity,
            reserved=0,
            available=event.initial_quantity,
            in_transit=0,
            damaged=0,
        )
        self.created_at = event.initialized_at
        self.updated_at = event.initialized_at

    @apply
    def _on_stock_received(self, event: StockReceived):
        self.levels = StockLevels(
            on_hand=event.new_on_hand,
            reserved=self.levels.reserved if self.levels else 0,
            available=event.new_available,
            in_transit=self.levels.in_transit if self.levels else 0,
            damaged=self.levels.damaged if self.levels else 0,
        )
        self.updated_at = event.received_at

    @apply
    def _on_stock_reserved(self, event: StockReserved):
        # Idempotent: skip if reservation already exists (live path pre-mutates)
        existing = next(
            (r for r in (self.reservations or []) if str(r.id) == str(event.reservation_id)),
            None,
        )
        if not existing:
            self.add_reservations(
                Reservation(
                    id=event.reservation_id,
                    order_id=event.order_id,
                    quantity=event.quantity,
                    reserved_at=event.reserved_at,
                    expires_at=event.expires_at,
                )
            )

        on_hand = self.levels.on_hand if self.levels else 0
        new_reserved = (self.levels.reserved if self.levels else 0) + event.quantity
        # Use the event's new_available for consistency during replay
        self.levels = StockLevels(
            on_hand=on_hand,
            reserved=new_reserved,
            available=event.new_available,
            in_transit=self.levels.in_transit if self.levels else 0,
            damaged=self.levels.damaged if self.levels else 0,
        )
        self.updated_at = event.reserved_at

    @apply
    def _on_reservation_released(self, event: ReservationReleased):
        reservation = next(
            (r for r in (self.reservations or []) if str(r.id) == str(event.reservation_id)),
            None,
        )
        if reservation:
            reservation.status = ReservationStatus.RELEASED.value

        on_hand = self.levels.on_hand if self.levels else 0
        new_reserved = (self.levels.reserved if self.levels else 0) - event.quantity
        self.levels = StockLevels(
            on_hand=on_hand,
            reserved=new_reserved,
            available=event.new_available,
            in_transit=self.levels.in_transit if self.levels else 0,
            damaged=self.levels.damaged if self.levels else 0,
        )
        self.updated_at = event.released_at

    @apply
    def _on_reservation_confirmed(self, event: ReservationConfirmed):
        reservation = next(
            (r for r in (self.reservations or []) if str(r.id) == str(event.reservation_id)),
            None,
        )
        if reservation:
            reservation.status = ReservationStatus.CONFIRMED.value
        self.updated_at = event.confirmed_at

    @apply
    def _on_stock_committed(self, event: StockCommitted):
        # Remove the reservation after commitment
        reservation = next(
            (r for r in (self.reservations or []) if str(r.id) == str(event.reservation_id)),
            None,
        )
        if reservation:
            self.remove_reservations(reservation)

        self.levels = StockLevels(
            on_hand=event.new_on_hand,
            reserved=event.new_reserved,
            available=event.new_on_hand - event.new_reserved,
            in_transit=self.levels.in_transit if self.levels else 0,
            damaged=self.levels.damaged if self.levels else 0,
        )
        self.updated_at = event.committed_at

    @apply
    def _on_stock_adjusted(self, event: StockAdjusted):
        self.levels = StockLevels(
            on_hand=event.new_on_hand,
            reserved=self.levels.reserved if self.levels else 0,
            available=event.new_available,
            in_transit=self.levels.in_transit if self.levels else 0,
            damaged=self.levels.damaged if self.levels else 0,
        )
        self.updated_at = event.adjusted_at

    @apply
    def _on_stock_marked_damaged(self, event: StockMarkedDamaged):
        self.levels = StockLevels(
            on_hand=event.new_on_hand,
            reserved=self.levels.reserved if self.levels else 0,
            available=event.new_available,
            in_transit=self.levels.in_transit if self.levels else 0,
            damaged=event.new_damaged,
        )
        self.updated_at = event.marked_at

    @apply
    def _on_damaged_stock_written_off(self, event: DamagedStockWrittenOff):
        self.levels = StockLevels(
            on_hand=self.levels.on_hand if self.levels else 0,
            reserved=self.levels.reserved if self.levels else 0,
            available=self.levels.available if self.levels else 0,
            in_transit=self.levels.in_transit if self.levels else 0,
            damaged=event.new_damaged,
        )
        self.updated_at = event.written_off_at

    @apply
    def _on_stock_returned(self, event: StockReturned):
        self.levels = StockLevels(
            on_hand=event.new_on_hand,
            reserved=self.levels.reserved if self.levels else 0,
            available=event.new_available,
            in_transit=self.levels.in_transit if self.levels else 0,
            damaged=self.levels.damaged if self.levels else 0,
        )
        self.updated_at = event.returned_at

    @apply
    def _on_stock_check_recorded(self, event: StockCheckRecorded):
        self.last_stock_check = event.checked_at
        self.updated_at = event.checked_at

    @apply
    def _on_low_stock_detected(self, event: LowStockDetected):  # noqa: ARG002
        # Notification-only event — no state change
        pass
