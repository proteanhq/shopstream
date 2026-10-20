"""Domain events for the InventoryItem aggregate.

All events are versioned, immutable facts representing stock movements.
Events are persisted to the event store and used for:
- Rebuilding aggregate state via @apply (event sourcing)
- Updating projections via projectors
- Cross-domain communication via Redis Streams
"""

from datetime import datetime

from protean.fields import DateTime, Identifier, Integer, String

from inventory.domain import inventory


@inventory.event(part_of="InventoryItem")
class StockInitialized:
    """A new inventory record was created for a product variant at a warehouse."""

    inventory_item_id: str = Identifier(required=True)
    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    warehouse_id: str = Identifier(required=True)
    sku: str = String(required=True)
    initial_quantity: int = Integer(required=True)
    reorder_point: int = Integer(required=True)
    reorder_quantity: int = Integer(required=True)
    initialized_at: datetime = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class StockReceived:
    """Stock was received into the warehouse, increasing on-hand quantity."""

    inventory_item_id: str = Identifier(required=True)
    quantity: int = Integer(required=True)
    previous_on_hand: int = Integer(required=True)
    new_on_hand: int = Integer(required=True)
    new_available: int = Integer(required=True)
    reference: str | None = String()  # Receiving document number
    received_at: datetime = DateTime(required=True)


@inventory.event(part_of="InventoryItem", published=True)
class StockReserved:
    """Stock was reserved for an order, decreasing available quantity."""

    inventory_item_id: str = Identifier(required=True)
    reservation_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    quantity: int = Integer(required=True)
    previous_available: int = Integer(required=True)
    new_available: int = Integer(required=True)
    reserved_at: datetime = DateTime(required=True)
    expires_at: datetime = DateTime(required=True)


@inventory.event(part_of="InventoryItem", published=True)
class ReservationReleased:
    """A stock reservation was released, returning quantity to available."""

    inventory_item_id: str = Identifier(required=True)
    reservation_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    quantity: int = Integer(required=True)
    reason: str = String(required=True)  # timeout, order_cancelled, payment_failed
    previous_available: int = Integer(required=True)
    new_available: int = Integer(required=True)
    released_at: datetime = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class ReservationConfirmed:
    """A stock reservation was confirmed after order payment."""

    inventory_item_id: str = Identifier(required=True)
    reservation_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    quantity: int = Integer(required=True)
    confirmed_at: datetime = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class StockCommitted:
    """Reserved stock was committed (shipped), reducing on-hand quantity."""

    inventory_item_id: str = Identifier(required=True)
    reservation_id: str = Identifier(required=True)
    order_id: str = Identifier(required=True)
    quantity: int = Integer(required=True)
    previous_on_hand: int = Integer(required=True)
    new_on_hand: int = Integer(required=True)
    previous_reserved: int = Integer(required=True)
    new_reserved: int = Integer(required=True)
    committed_at: datetime = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class StockAdjusted:
    """Stock was manually adjusted (count, shrinkage, correction)."""

    inventory_item_id: str = Identifier(required=True)
    product_id: str = Identifier(required=True)
    adjustment_type: str = String(required=True)  # Count, Shrinkage, Correction, Receiving_Error
    quantity_change: int = Integer(required=True)  # Can be negative
    reason: str = String(required=True)
    adjusted_by: str = String(required=True)
    previous_on_hand: int = Integer(required=True)
    new_on_hand: int = Integer(required=True)
    new_available: int = Integer(required=True)
    adjusted_at: datetime = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class StockMarkedDamaged:
    """Stock was identified as damaged, moving from on-hand to damaged."""

    inventory_item_id: str = Identifier(required=True)
    product_id: str = Identifier(required=True)
    quantity: int = Integer(required=True)
    reason: str = String(required=True)
    previous_on_hand: int = Integer(required=True)
    new_on_hand: int = Integer(required=True)
    previous_damaged: int = Integer(required=True)
    new_damaged: int = Integer(required=True)
    new_available: int = Integer(required=True)
    marked_at: datetime = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class DamagedStockWrittenOff:
    """Damaged stock was written off (removed from inventory)."""

    inventory_item_id: str = Identifier(required=True)
    product_id: str = Identifier(required=True)
    quantity: int = Integer(required=True)
    approved_by: str = String(required=True)
    previous_damaged: int = Integer(required=True)
    new_damaged: int = Integer(required=True)
    written_off_at: datetime = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class StockReturned:
    """Returned items were added back to on-hand inventory."""

    inventory_item_id: str = Identifier(required=True)
    quantity: int = Integer(required=True)
    order_id: str = Identifier(required=True)
    previous_on_hand: int = Integer(required=True)
    new_on_hand: int = Integer(required=True)
    new_available: int = Integer(required=True)
    returned_at: datetime = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class StockCheckRecorded:
    """A physical stock count was recorded."""

    inventory_item_id: str = Identifier(required=True)
    counted_quantity: int = Integer(required=True)
    expected_quantity: int = Integer(required=True)
    discrepancy: int = Integer(required=True)  # counted - expected
    checked_by: str = String(required=True)
    checked_at: datetime = DateTime(required=True)


@inventory.event(part_of="InventoryItem", published=True)
class LowStockDetected:
    """Available stock dropped below the reorder point."""

    inventory_item_id: str = Identifier(required=True)
    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    sku: str = String(required=True)
    current_available: int = Integer(required=True)
    reorder_point: int = Integer(required=True)
    detected_at: datetime = DateTime(required=True)
