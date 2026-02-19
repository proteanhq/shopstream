"""Domain events for the InventoryItem aggregate.

All events are versioned, immutable facts representing stock movements.
Events are persisted to the event store and used for:
- Rebuilding aggregate state via @apply (event sourcing)
- Updating projections via projectors
- Cross-domain communication via Redis Streams
"""

from protean.fields import DateTime, Identifier, Integer, String

from inventory.domain import inventory


@inventory.event(part_of="InventoryItem")
class StockInitialized:
    """A new inventory record was created for a product variant at a warehouse."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    warehouse_id = Identifier(required=True)
    sku = String(required=True)
    initial_quantity = Integer(required=True)
    reorder_point = Integer(required=True)
    reorder_quantity = Integer(required=True)
    initialized_at = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class StockReceived:
    """Stock was received into the warehouse, increasing on-hand quantity."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    quantity = Integer(required=True)
    previous_on_hand = Integer(required=True)
    new_on_hand = Integer(required=True)
    new_available = Integer(required=True)
    reference = String()  # Receiving document number
    received_at = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class StockReserved:
    """Stock was reserved for an order, decreasing available quantity."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    reservation_id = Identifier(required=True)
    order_id = Identifier(required=True)
    quantity = Integer(required=True)
    previous_available = Integer(required=True)
    new_available = Integer(required=True)
    reserved_at = DateTime(required=True)
    expires_at = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class ReservationReleased:
    """A stock reservation was released, returning quantity to available."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    reservation_id = Identifier(required=True)
    order_id = Identifier(required=True)
    quantity = Integer(required=True)
    reason = String(required=True)  # timeout, order_cancelled, payment_failed
    previous_available = Integer(required=True)
    new_available = Integer(required=True)
    released_at = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class ReservationConfirmed:
    """A stock reservation was confirmed after order payment."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    reservation_id = Identifier(required=True)
    order_id = Identifier(required=True)
    quantity = Integer(required=True)
    confirmed_at = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class StockCommitted:
    """Reserved stock was committed (shipped), reducing on-hand quantity."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    reservation_id = Identifier(required=True)
    order_id = Identifier(required=True)
    quantity = Integer(required=True)
    previous_on_hand = Integer(required=True)
    new_on_hand = Integer(required=True)
    previous_reserved = Integer(required=True)
    new_reserved = Integer(required=True)
    committed_at = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class StockAdjusted:
    """Stock was manually adjusted (count, shrinkage, correction)."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    adjustment_type = String(required=True)  # Count, Shrinkage, Correction, Receiving_Error
    quantity_change = Integer(required=True)  # Can be negative
    reason = String(required=True)
    adjusted_by = String(required=True)
    previous_on_hand = Integer(required=True)
    new_on_hand = Integer(required=True)
    new_available = Integer(required=True)
    adjusted_at = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class StockMarkedDamaged:
    """Stock was identified as damaged, moving from on-hand to damaged."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    quantity = Integer(required=True)
    reason = String(required=True)
    previous_on_hand = Integer(required=True)
    new_on_hand = Integer(required=True)
    previous_damaged = Integer(required=True)
    new_damaged = Integer(required=True)
    new_available = Integer(required=True)
    marked_at = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class DamagedStockWrittenOff:
    """Damaged stock was written off (removed from inventory)."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    quantity = Integer(required=True)
    approved_by = String(required=True)
    previous_damaged = Integer(required=True)
    new_damaged = Integer(required=True)
    written_off_at = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class StockReturned:
    """Returned items were added back to on-hand inventory."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    quantity = Integer(required=True)
    order_id = Identifier(required=True)
    previous_on_hand = Integer(required=True)
    new_on_hand = Integer(required=True)
    new_available = Integer(required=True)
    returned_at = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class StockCheckRecorded:
    """A physical stock count was recorded."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    counted_quantity = Integer(required=True)
    expected_quantity = Integer(required=True)
    discrepancy = Integer(required=True)  # counted - expected
    checked_by = String(required=True)
    checked_at = DateTime(required=True)


@inventory.event(part_of="InventoryItem")
class LowStockDetected:
    """Available stock dropped below the reorder point."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    sku = String(required=True)
    current_available = Integer(required=True)
    reorder_point = Integer(required=True)
    detected_at = DateTime(required=True)
