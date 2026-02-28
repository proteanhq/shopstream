"""Cross-domain event contracts for Inventory domain events.

These classes define the event shape for consumption by other domains
(e.g., the OrderCheckoutSaga in the ordering domain). They are registered
as external events via domain.register_external_event() with matching
__type__ strings so Protean's stream deserialization works correctly.

The source-of-truth events are in src/inventory/stock/events.py.
"""

from protean.core.event import BaseEvent
from protean.fields import DateTime, Identifier, Integer, String


class StockReserved(BaseEvent):
    """Stock was reserved for an order."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    reservation_id = Identifier(required=True)
    order_id = Identifier(required=True)
    quantity = Integer(required=True)
    previous_available = Integer(required=True)
    new_available = Integer(required=True)
    reserved_at = DateTime(required=True)
    expires_at = DateTime(required=True)


class ReservationReleased(BaseEvent):
    """A stock reservation was released."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    reservation_id = Identifier(required=True)
    order_id = Identifier(required=True)
    quantity = Integer(required=True)
    reason = String(required=True)
    previous_available = Integer(required=True)
    new_available = Integer(required=True)
    released_at = DateTime(required=True)


class StockInitialized(BaseEvent):
    """A new inventory record was created for a product variant."""

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


class StockReceived(BaseEvent):
    """Stock was received into the warehouse."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    quantity = Integer(required=True)
    previous_on_hand = Integer(required=True)
    new_on_hand = Integer(required=True)
    new_available = Integer(required=True)
    reference = String()
    received_at = DateTime(required=True)


class ReservationConfirmed(BaseEvent):
    """A stock reservation was confirmed after order payment."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    reservation_id = Identifier(required=True)
    order_id = Identifier(required=True)
    quantity = Integer(required=True)
    confirmed_at = DateTime(required=True)


class StockCommitted(BaseEvent):
    """Reserved stock was committed (shipped)."""

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


class StockAdjusted(BaseEvent):
    """Stock was manually adjusted."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    product_id = Identifier(required=True)
    adjustment_type = String(required=True)
    quantity_change = Integer(required=True)
    reason = String(required=True)
    adjusted_by = String(required=True)
    previous_on_hand = Integer(required=True)
    new_on_hand = Integer(required=True)
    new_available = Integer(required=True)
    adjusted_at = DateTime(required=True)


class StockMarkedDamaged(BaseEvent):
    """Stock was identified as damaged."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    product_id = Identifier(required=True)
    quantity = Integer(required=True)
    reason = String(required=True)
    previous_on_hand = Integer(required=True)
    new_on_hand = Integer(required=True)
    previous_damaged = Integer(required=True)
    new_damaged = Integer(required=True)
    new_available = Integer(required=True)
    marked_at = DateTime(required=True)


class DamagedStockWrittenOff(BaseEvent):
    """Damaged stock was written off."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    product_id = Identifier(required=True)
    quantity = Integer(required=True)
    approved_by = String(required=True)
    previous_damaged = Integer(required=True)
    new_damaged = Integer(required=True)
    written_off_at = DateTime(required=True)


class StockReturned(BaseEvent):
    """Returned items were added back to on-hand inventory."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    quantity = Integer(required=True)
    order_id = Identifier(required=True)
    previous_on_hand = Integer(required=True)
    new_on_hand = Integer(required=True)
    new_available = Integer(required=True)
    returned_at = DateTime(required=True)


class StockCheckRecorded(BaseEvent):
    """A physical stock count was recorded."""

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    counted_quantity = Integer(required=True)
    expected_quantity = Integer(required=True)
    discrepancy = Integer(required=True)
    checked_by = String(required=True)
    checked_at = DateTime(required=True)


class LowStockDetected(BaseEvent):
    """Available stock dropped below the reorder point.

    Consumed by the Notifications domain to send internal alerts (Slack).
    """

    __version__ = "v1"

    inventory_item_id = Identifier(required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    sku = String(required=True)
    current_available = Integer(required=True)
    reorder_point = Integer(required=True)
    detected_at = DateTime(required=True)
