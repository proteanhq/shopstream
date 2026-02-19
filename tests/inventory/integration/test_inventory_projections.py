"""Integration tests for Inventory projections — verify projectors update read models."""

import pytest
from inventory.projections.inventory_level import InventoryLevel
from inventory.projections.low_stock_report import LowStockReport
from inventory.projections.product_availability import ProductAvailability
from inventory.projections.reservation_status import ReservationStatus
from inventory.projections.stock_movement_log import StockMovementLog
from inventory.projections.warehouse_stock import WarehouseStock
from inventory.stock.adjustment import AdjustStock
from inventory.stock.damage import MarkDamaged, WriteOffDamaged
from inventory.stock.initialization import InitializeStock
from inventory.stock.receiving import ReceiveStock
from inventory.stock.reservation import ConfirmReservation, ReleaseReservation, ReserveStock
from inventory.stock.returns import ReturnToStock
from inventory.stock.shipping import CommitStock
from inventory.stock.stock import AdjustmentType, InventoryItem
from protean import current_domain


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


def _reserve(item_id, order_id="ord-001", quantity=5):
    current_domain.process(
        ReserveStock(inventory_item_id=item_id, order_id=order_id, quantity=quantity),
        asynchronous=False,
    )
    # Return the reservation_id from the aggregate
    item = current_domain.repository_for(InventoryItem).get(item_id)
    return str(item.reservations[-1].id)


# ---------------------------------------------------------------------------
# InventoryLevel projection
# ---------------------------------------------------------------------------
class TestInventoryLevelProjection:
    def test_created_on_initialization(self):
        item_id = _initialize_stock(initial_quantity=100)
        level = current_domain.repository_for(InventoryLevel).get(item_id)

        assert level.inventory_item_id == item_id
        assert level.product_id == "prod-001"
        assert level.variant_id == "var-001"
        assert level.warehouse_id == "wh-001"
        assert level.sku == "TSHIRT-BLK-M"
        assert level.on_hand == 100
        assert level.reserved == 0
        assert level.available == 100

    def test_updated_on_receive(self):
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=20),
            asynchronous=False,
        )

        level = current_domain.repository_for(InventoryLevel).get(item_id)
        assert level.on_hand == 120
        assert level.available == 120

    def test_updated_on_reserve(self):
        item_id = _initialize_stock(initial_quantity=100)
        _reserve(item_id, quantity=10)

        level = current_domain.repository_for(InventoryLevel).get(item_id)
        assert level.on_hand == 100
        assert level.reserved == 10
        assert level.available == 90

    def test_updated_through_full_lifecycle(self):
        """Initialize → Reserve → Confirm → Commit."""
        item_id = _initialize_stock(initial_quantity=100)
        reservation_id = _reserve(item_id, quantity=10)
        current_domain.process(
            ConfirmReservation(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )
        current_domain.process(
            CommitStock(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )

        level = current_domain.repository_for(InventoryLevel).get(item_id)
        assert level.on_hand == 90
        assert level.reserved == 0
        assert level.available == 90

    def test_updated_on_damage_and_write_off(self):
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            MarkDamaged(inventory_item_id=item_id, quantity=5, reason="Water damage"),
            asynchronous=False,
        )

        level = current_domain.repository_for(InventoryLevel).get(item_id)
        assert level.on_hand == 95
        assert level.damaged == 5
        assert level.available == 95

        current_domain.process(
            WriteOffDamaged(inventory_item_id=item_id, quantity=3, approved_by="mgr-001"),
            asynchronous=False,
        )
        level = current_domain.repository_for(InventoryLevel).get(item_id)
        assert level.damaged == 2

    def test_updated_on_return(self):
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            ReturnToStock(inventory_item_id=item_id, quantity=10, order_id="ord-001"),
            asynchronous=False,
        )

        level = current_domain.repository_for(InventoryLevel).get(item_id)
        assert level.on_hand == 110
        assert level.available == 110

    def test_updated_on_adjustment(self):
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            AdjustStock(
                inventory_item_id=item_id,
                quantity_change=-10,
                adjustment_type=AdjustmentType.SHRINKAGE.value,
                reason="Inventory shrinkage",
                adjusted_by="manager-001",
            ),
            asynchronous=False,
        )

        level = current_domain.repository_for(InventoryLevel).get(item_id)
        assert level.on_hand == 90
        assert level.available == 90

    def test_updated_on_release(self):
        item_id = _initialize_stock(initial_quantity=100)
        reservation_id = _reserve(item_id, quantity=10)
        current_domain.process(
            ReleaseReservation(
                inventory_item_id=item_id,
                reservation_id=reservation_id,
                reason="Customer cancelled",
            ),
            asynchronous=False,
        )

        level = current_domain.repository_for(InventoryLevel).get(item_id)
        assert level.on_hand == 100
        assert level.reserved == 0
        assert level.available == 100


# ---------------------------------------------------------------------------
# ProductAvailability projection
# ---------------------------------------------------------------------------
class TestProductAvailabilityProjection:
    def test_created_on_initialization(self):
        _initialize_stock(product_id="prod-pa-001", variant_id="var-pa-001", initial_quantity=50)

        key = "prod-pa-001::var-pa-001"
        pa = current_domain.repository_for(ProductAvailability).get(key)
        assert pa.product_id == "prod-pa-001"
        assert pa.variant_id == "var-pa-001"
        assert pa.total_on_hand == 50
        assert pa.total_available == 50
        assert pa.warehouse_count == 1
        assert pa.is_in_stock is True

    def test_updated_on_receive(self):
        item_id = _initialize_stock(
            product_id="prod-pa-rx",
            variant_id="var-pa-rx",
            initial_quantity=50,
        )
        current_domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=30),
            asynchronous=False,
        )

        key = "prod-pa-rx::var-pa-rx"
        pa = current_domain.repository_for(ProductAvailability).get(key)
        assert pa.total_on_hand == 80
        assert pa.total_available == 80

    def test_updated_on_reserve_and_release(self):
        item_id = _initialize_stock(
            product_id="prod-pa-res",
            variant_id="var-pa-res",
            initial_quantity=50,
        )
        reservation_id = _reserve(item_id, quantity=10)

        key = "prod-pa-res::var-pa-res"
        pa = current_domain.repository_for(ProductAvailability).get(key)
        assert pa.total_reserved == 10
        assert pa.total_available == 40

        # Release
        current_domain.process(
            ReleaseReservation(
                inventory_item_id=item_id,
                reservation_id=reservation_id,
                reason="Cancelled",
            ),
            asynchronous=False,
        )

        pa = current_domain.repository_for(ProductAvailability).get(key)
        assert pa.total_reserved == 0
        assert pa.total_available == 50

    def test_updated_on_commit(self):
        item_id = _initialize_stock(
            product_id="prod-pa-com",
            variant_id="var-pa-com",
            initial_quantity=50,
        )
        reservation_id = _reserve(item_id, quantity=10)
        current_domain.process(
            ConfirmReservation(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )
        current_domain.process(
            CommitStock(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )

        key = "prod-pa-com::var-pa-com"
        pa = current_domain.repository_for(ProductAvailability).get(key)
        assert pa.total_on_hand == 40
        assert pa.total_reserved == 0

    def test_updated_on_adjust(self):
        item_id = _initialize_stock(
            product_id="prod-pa-adj",
            variant_id="var-pa-adj",
            initial_quantity=50,
        )
        current_domain.process(
            AdjustStock(
                inventory_item_id=item_id,
                quantity_change=-10,
                adjustment_type=AdjustmentType.SHRINKAGE.value,
                reason="Shrinkage",
                adjusted_by="mgr",
            ),
            asynchronous=False,
        )

        key = "prod-pa-adj::var-pa-adj"
        pa = current_domain.repository_for(ProductAvailability).get(key)
        assert pa.total_on_hand == 40
        assert pa.total_available == 40

    def test_updated_on_damage(self):
        item_id = _initialize_stock(
            product_id="prod-pa-dmg",
            variant_id="var-pa-dmg",
            initial_quantity=50,
        )
        current_domain.process(
            MarkDamaged(inventory_item_id=item_id, quantity=5, reason="Broken"),
            asynchronous=False,
        )

        key = "prod-pa-dmg::var-pa-dmg"
        pa = current_domain.repository_for(ProductAvailability).get(key)
        assert pa.total_on_hand == 45
        assert pa.total_available == 45

    def test_updated_on_return(self):
        item_id = _initialize_stock(
            product_id="prod-pa-ret",
            variant_id="var-pa-ret",
            initial_quantity=50,
        )
        current_domain.process(
            ReturnToStock(inventory_item_id=item_id, quantity=10, order_id="ord-001"),
            asynchronous=False,
        )

        key = "prod-pa-ret::var-pa-ret"
        pa = current_domain.repository_for(ProductAvailability).get(key)
        assert pa.total_on_hand == 60
        assert pa.total_available == 60

    def test_aggregates_warehouses(self):
        """Two warehouses for same product variant should aggregate."""
        _initialize_stock(
            product_id="prod-pa-002",
            variant_id="var-pa-002",
            warehouse_id="wh-A",
            initial_quantity=30,
        )
        _initialize_stock(
            product_id="prod-pa-002",
            variant_id="var-pa-002",
            warehouse_id="wh-B",
            initial_quantity=20,
        )

        key = "prod-pa-002::var-pa-002"
        pa = current_domain.repository_for(ProductAvailability).get(key)
        assert pa.total_on_hand == 50
        assert pa.total_available == 50
        assert pa.warehouse_count == 2
        assert pa.is_in_stock is True


# ---------------------------------------------------------------------------
# WarehouseStock projection
# ---------------------------------------------------------------------------
class TestWarehouseStockProjection:
    def test_created_on_initialization(self):
        item_id = _initialize_stock(initial_quantity=80)
        ws = current_domain.repository_for(WarehouseStock).get(item_id)

        assert ws.warehouse_id == "wh-001"
        assert ws.on_hand == 80
        assert ws.available == 80

    def test_updated_on_receive(self):
        item_id = _initialize_stock(initial_quantity=80)
        current_domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=20),
            asynchronous=False,
        )

        ws = current_domain.repository_for(WarehouseStock).get(item_id)
        assert ws.on_hand == 100
        assert ws.available == 100


# ---------------------------------------------------------------------------
# LowStockReport projection
# ---------------------------------------------------------------------------
class TestLowStockReportProjection:
    def test_created_on_low_stock_detection(self):
        """Adjusting stock below reorder_point triggers LowStockDetected."""
        item_id = _initialize_stock(initial_quantity=15, reorder_point=10)

        # Adjust down to trigger low stock (_check_low_stock called from adjust_stock)
        current_domain.process(
            AdjustStock(
                inventory_item_id=item_id,
                quantity_change=-10,
                adjustment_type=AdjustmentType.SHRINKAGE.value,
                reason="Loss detected",
                adjusted_by="mgr-001",
            ),
            asynchronous=False,
        )

        report = current_domain.repository_for(LowStockReport).get(item_id)
        assert report.product_id == "prod-001"
        assert report.current_available == 5
        assert report.reorder_point == 10
        assert report.is_critical is False

    def test_critical_when_zero(self):
        """Reserving all stock triggers critical low stock."""
        item_id = _initialize_stock(initial_quantity=10, reorder_point=10)

        # Reserve all stock — triggers _check_low_stock
        _reserve(item_id, quantity=10)

        report = current_domain.repository_for(LowStockReport).get(item_id)
        assert report.is_critical is True
        assert report.current_available == 0

    def test_removed_when_restocked_above_threshold(self):
        item_id = _initialize_stock(initial_quantity=15, reorder_point=10)

        # Drop below threshold
        current_domain.process(
            AdjustStock(
                inventory_item_id=item_id,
                quantity_change=-10,
                adjustment_type=AdjustmentType.SHRINKAGE.value,
                reason="Shrinkage",
                adjusted_by="mgr-001",
            ),
            asynchronous=False,
        )

        # Verify it's in the report
        report = current_domain.repository_for(LowStockReport).get(item_id)
        assert report is not None

        # Restock above threshold
        current_domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=20),
            asynchronous=False,
        )

        # Should be removed from the report
        from protean.exceptions import ObjectNotFoundError

        with pytest.raises(ObjectNotFoundError):
            current_domain.repository_for(LowStockReport).get(item_id)

    def test_updated_when_still_low_after_receive(self):
        """Receive stock but still below threshold — report stays, updates available."""
        item_id = _initialize_stock(initial_quantity=15, reorder_point=10)

        # Drop below threshold
        current_domain.process(
            AdjustStock(
                inventory_item_id=item_id,
                quantity_change=-10,
                adjustment_type=AdjustmentType.SHRINKAGE.value,
                reason="Shrinkage",
                adjusted_by="mgr-001",
            ),
            asynchronous=False,
        )

        # Receive a small amount — still below threshold
        current_domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=2),
            asynchronous=False,
        )

        report = current_domain.repository_for(LowStockReport).get(item_id)
        assert report.current_available == 7
        assert report.is_critical is False

    def test_updated_on_repeated_low_stock_detection(self):
        """LowStockDetected fires twice — updates existing report."""
        item_id = _initialize_stock(initial_quantity=15, reorder_point=10)

        # First adjustment drops to 5
        current_domain.process(
            AdjustStock(
                inventory_item_id=item_id,
                quantity_change=-10,
                adjustment_type=AdjustmentType.SHRINKAGE.value,
                reason="Shrinkage",
                adjusted_by="mgr-001",
            ),
            asynchronous=False,
        )

        report = current_domain.repository_for(LowStockReport).get(item_id)
        assert report.current_available == 5

        # Second adjustment drops further to 2
        current_domain.process(
            AdjustStock(
                inventory_item_id=item_id,
                quantity_change=-3,
                adjustment_type=AdjustmentType.SHRINKAGE.value,
                reason="More shrinkage",
                adjusted_by="mgr-001",
            ),
            asynchronous=False,
        )

        report = current_domain.repository_for(LowStockReport).get(item_id)
        assert report.current_available == 2
        assert report.is_critical is False

    def test_removed_on_return_above_threshold(self):
        """Stock return brings quantity above threshold — removes from report."""
        item_id = _initialize_stock(initial_quantity=15, reorder_point=10)

        # Drop below threshold
        current_domain.process(
            AdjustStock(
                inventory_item_id=item_id,
                quantity_change=-10,
                adjustment_type=AdjustmentType.SHRINKAGE.value,
                reason="Shrinkage",
                adjusted_by="mgr-001",
            ),
            asynchronous=False,
        )

        # Return enough to go above threshold
        current_domain.process(
            ReturnToStock(inventory_item_id=item_id, quantity=20, order_id="ord-ret"),
            asynchronous=False,
        )

        from protean.exceptions import ObjectNotFoundError

        with pytest.raises(ObjectNotFoundError):
            current_domain.repository_for(LowStockReport).get(item_id)

    def test_updated_on_return_still_below_threshold(self):
        """Stock return but still below threshold — report stays, updates available."""
        item_id = _initialize_stock(initial_quantity=15, reorder_point=10)

        # Drop below threshold
        current_domain.process(
            AdjustStock(
                inventory_item_id=item_id,
                quantity_change=-10,
                adjustment_type=AdjustmentType.SHRINKAGE.value,
                reason="Shrinkage",
                adjusted_by="mgr-001",
            ),
            asynchronous=False,
        )

        # Return a small amount — still below threshold
        current_domain.process(
            ReturnToStock(inventory_item_id=item_id, quantity=2, order_id="ord-ret"),
            asynchronous=False,
        )

        report = current_domain.repository_for(LowStockReport).get(item_id)
        assert report.current_available == 7
        assert report.is_critical is False


# ---------------------------------------------------------------------------
# StockMovementLog projection
# ---------------------------------------------------------------------------
class TestStockMovementLogProjection:
    def test_entry_created_on_initialization(self):
        item_id = _initialize_stock(initial_quantity=100)

        repo = current_domain.repository_for(StockMovementLog)
        entries = repo._dao.query.filter(inventory_item_id=item_id).all().items
        assert len(entries) >= 1

        event_types = [e.event_type for e in entries]
        assert "StockInitialized" in event_types

    def test_grows_with_events(self):
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=20),
            asynchronous=False,
        )
        _reserve(item_id, quantity=10)

        repo = current_domain.repository_for(StockMovementLog)
        entries = repo._dao.query.filter(inventory_item_id=item_id).all().items

        # StockInitialized + StockReceived + StockReserved = 3 minimum
        assert len(entries) >= 3
        event_types = [e.event_type for e in entries]
        assert "StockInitialized" in event_types
        assert "StockReceived" in event_types
        assert "StockReserved" in event_types

    def test_full_lifecycle_audit_trail(self):
        """Verify audit trail for init → reserve → confirm → commit."""
        item_id = _initialize_stock(initial_quantity=100)
        reservation_id = _reserve(item_id, quantity=10)
        current_domain.process(
            ConfirmReservation(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )
        current_domain.process(
            CommitStock(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )

        repo = current_domain.repository_for(StockMovementLog)
        entries = repo._dao.query.filter(inventory_item_id=item_id).all().items

        event_types = [e.event_type for e in entries]
        assert "StockInitialized" in event_types
        assert "StockReserved" in event_types
        assert "ReservationConfirmed" in event_types
        assert "StockCommitted" in event_types


# ---------------------------------------------------------------------------
# ReservationStatus projection
# ---------------------------------------------------------------------------
class TestReservationStatusProjection:
    def test_created_on_reserve(self):
        item_id = _initialize_stock(initial_quantity=100)
        reservation_id = _reserve(item_id, order_id="ord-rs-001", quantity=10)

        rs = current_domain.repository_for(ReservationStatus).get(reservation_id)
        assert rs.inventory_item_id == item_id
        assert rs.order_id == "ord-rs-001"
        assert rs.quantity == 10
        assert rs.status == "Active"

    def test_tracks_lifecycle(self):
        """Reserve → Confirm → Commit."""
        item_id = _initialize_stock(initial_quantity=100)
        reservation_id = _reserve(item_id, order_id="ord-rs-002", quantity=10)

        # Confirm
        current_domain.process(
            ConfirmReservation(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )
        rs = current_domain.repository_for(ReservationStatus).get(reservation_id)
        assert rs.status == "Confirmed"

        # Commit
        current_domain.process(
            CommitStock(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )
        rs = current_domain.repository_for(ReservationStatus).get(reservation_id)
        assert rs.status == "Committed"

    def test_release_updates_status(self):
        item_id = _initialize_stock(initial_quantity=100)
        reservation_id = _reserve(item_id, order_id="ord-rs-003", quantity=10)

        current_domain.process(
            ReleaseReservation(
                inventory_item_id=item_id,
                reservation_id=reservation_id,
                reason="Customer cancelled",
            ),
            asynchronous=False,
        )

        rs = current_domain.repository_for(ReservationStatus).get(reservation_id)
        assert rs.status == "Released"
