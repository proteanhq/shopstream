"""Product availability — aggregated availability across warehouses for PDP display.

This projection uses delta-based updates from events to maintain totals,
rather than reading from InventoryLevel. This avoids cross-projection
dependencies during synchronous event processing.
"""

from protean.core.projector import on
from protean.fields import Boolean, DateTime, Identifier, Integer
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.events import (
    ReservationReleased,
    StockAdjusted,
    StockCommitted,
    StockInitialized,
    StockMarkedDamaged,
    StockReceived,
    StockReserved,
    StockReturned,
)
from inventory.stock.stock import InventoryItem


@inventory.projection
class ProductAvailability:
    product_variant_key = Identifier(identifier=True, required=True)  # "product_id::variant_id"
    product_id = Identifier(required=True)
    variant_id = Identifier(required=True)
    total_available = Integer(default=0)
    total_on_hand = Integer(default=0)
    total_reserved = Integer(default=0)
    warehouse_count = Integer(default=0)
    is_in_stock = Boolean(default=False)
    updated_at = DateTime()


def _build_key(product_id, variant_id):
    return f"{product_id}::{variant_id}"


def _get_or_create(product_id, variant_id, timestamp):
    key = _build_key(product_id, variant_id)
    repo = current_domain.repository_for(ProductAvailability)
    try:
        return repo.get(key)
    except Exception:
        return ProductAvailability(
            product_variant_key=key,
            product_id=product_id,
            variant_id=variant_id,
            total_available=0,
            total_on_hand=0,
            total_reserved=0,
            warehouse_count=0,
            is_in_stock=False,
            updated_at=timestamp,
        )


def _save(pa):
    pa.is_in_stock = pa.total_available > 0
    current_domain.repository_for(ProductAvailability).add(pa)


@inventory.projector(projector_for=ProductAvailability, aggregates=[InventoryItem])
class ProductAvailabilityProjector:
    @on(StockInitialized)
    def on_stock_initialized(self, event):
        pa = _get_or_create(event.product_id, event.variant_id, event.initialized_at)
        pa.total_on_hand = pa.total_on_hand + event.initial_quantity
        pa.total_available = pa.total_available + event.initial_quantity
        pa.warehouse_count = pa.warehouse_count + 1
        pa.updated_at = event.initialized_at
        _save(pa)

    @on(StockReceived)
    def on_stock_received(self, event):
        """Use delta: new_on_hand - previous_on_hand = quantity received."""
        from inventory.projections.inventory_level import InventoryLevel

        try:
            level = current_domain.repository_for(InventoryLevel).get(event.inventory_item_id)
            pa = _get_or_create(level.product_id, level.variant_id, event.received_at)
        except Exception:
            return

        pa.total_on_hand = pa.total_on_hand + event.quantity
        pa.total_available = pa.total_available + event.quantity
        pa.updated_at = event.received_at
        _save(pa)

    @on(StockReserved)
    def on_stock_reserved(self, event):
        from inventory.projections.inventory_level import InventoryLevel

        try:
            level = current_domain.repository_for(InventoryLevel).get(event.inventory_item_id)
            pa = _get_or_create(level.product_id, level.variant_id, event.reserved_at)
        except Exception:
            return

        pa.total_reserved = pa.total_reserved + event.quantity
        pa.total_available = pa.total_available - event.quantity
        pa.updated_at = event.reserved_at
        _save(pa)

    @on(ReservationReleased)
    def on_reservation_released(self, event):
        from inventory.projections.inventory_level import InventoryLevel

        try:
            level = current_domain.repository_for(InventoryLevel).get(event.inventory_item_id)
            pa = _get_or_create(level.product_id, level.variant_id, event.released_at)
        except Exception:
            return

        pa.total_reserved = pa.total_reserved - event.quantity
        pa.total_available = pa.total_available + event.quantity
        pa.updated_at = event.released_at
        _save(pa)

    @on(StockCommitted)
    def on_stock_committed(self, event):
        from inventory.projections.inventory_level import InventoryLevel

        try:
            level = current_domain.repository_for(InventoryLevel).get(event.inventory_item_id)
            pa = _get_or_create(level.product_id, level.variant_id, event.committed_at)
        except Exception:
            return

        pa.total_on_hand = pa.total_on_hand - event.quantity
        pa.total_reserved = pa.total_reserved - event.quantity
        pa.updated_at = event.committed_at
        _save(pa)

    @on(StockAdjusted)
    def on_stock_adjusted(self, event):
        from inventory.projections.inventory_level import InventoryLevel

        try:
            level = current_domain.repository_for(InventoryLevel).get(event.inventory_item_id)
            pa = _get_or_create(level.product_id, level.variant_id, event.adjusted_at)
        except Exception:
            return

        pa.total_on_hand = pa.total_on_hand + event.quantity_change
        pa.total_available = pa.total_available + event.quantity_change
        pa.updated_at = event.adjusted_at
        _save(pa)

    @on(StockMarkedDamaged)
    def on_stock_marked_damaged(self, event):
        from inventory.projections.inventory_level import InventoryLevel

        try:
            level = current_domain.repository_for(InventoryLevel).get(event.inventory_item_id)
            pa = _get_or_create(level.product_id, level.variant_id, event.marked_at)
        except Exception:
            return

        pa.total_on_hand = pa.total_on_hand - event.quantity
        pa.total_available = pa.total_available - event.quantity
        pa.updated_at = event.marked_at
        _save(pa)

    @on(StockReturned)
    def on_stock_returned(self, event):
        from inventory.projections.inventory_level import InventoryLevel

        try:
            level = current_domain.repository_for(InventoryLevel).get(event.inventory_item_id)
            pa = _get_or_create(level.product_id, level.variant_id, event.returned_at)
        except Exception:
            return

        pa.total_on_hand = pa.total_on_hand + event.quantity
        pa.total_available = pa.total_available + event.quantity
        pa.updated_at = event.returned_at
        _save(pa)
