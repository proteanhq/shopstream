# Inventory Domain

Stock management (event-sourced) and warehouse operations (CQRS).

## Domain Composition Root

`domain.py` — `inventory = Domain(name="inventory")`

All elements register via `@inventory.<element_type>` decorators.

## Configuration

`domain.toml` — PostgreSQL database, Redis broker, Message DB event store. Priority lanes enabled. Environment overlays for test (`inventory_test` DB) and production (`inventory` DB, async events).

## Aggregate: InventoryItem (Event-Sourced)

**File:** `stock/stock.py`

Root fields: `product_id`, `variant_id`, `warehouse_id`, `sku`, `levels` (StockLevels VO), `reorder_point` (default 10), `reorder_quantity` (default 50), `reservations` (HasMany Reservation), `last_stock_check`, `created_at`, `updated_at`.

### Enums
- `ReservationStatus`: Active, Confirmed, Released, Expired
- `AdjustmentType`: Count, Shrinkage, Correction, Receiving_Error

### Value Objects (part_of="InventoryItem")
- `StockLevels` — on_hand, reserved, available (on_hand - reserved, denormalized), in_transit, damaged

### Entities (part_of="InventoryItem")
- `Reservation` — order_id, quantity (min 1), status (ReservationStatus), reserved_at, expires_at. Lifecycle: Active → Confirmed → committed (via CommitStock) or Active → Released.

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `InventoryItem.create(product_id, variant_id, warehouse_id, sku, initial_quantity?, reorder_point?, reorder_quantity?)` | Factory, event-sourced `_create_new()`, raises `StockInitialized` |
| `receive_stock(quantity, reference?)` | quantity > 0, increases on_hand/available, raises `StockReceived` |
| `reserve(order_id, quantity, expires_at?)` | quantity > 0, sufficient available stock, creates Reservation, raises `StockReserved`, checks low stock |
| `release_reservation(reservation_id, reason)` | Active reservation only, marks Released, raises `ReservationReleased` |
| `confirm_reservation(reservation_id)` | Active reservation only, marks Confirmed, raises `ReservationConfirmed` |
| `commit_stock(reservation_id)` | Confirmed reservation only, reduces on_hand/reserved, raises `StockCommitted` |
| `adjust_stock(quantity_change, adjustment_type, reason, adjusted_by)` | Reason required, new_on_hand >= 0, raises `StockAdjusted`, checks low stock |
| `record_stock_check(counted_quantity, checked_by)` | Computes discrepancy, raises `StockCheckRecorded`, auto-adjusts if discrepancy != 0 |
| `mark_damaged(quantity, reason)` | Moves from on_hand to damaged, quantity <= unreserved, raises `StockMarkedDamaged`, checks low stock |
| `write_off_damaged(quantity, approved_by)` | quantity <= damaged, raises `DamagedStockWrittenOff` |
| `return_to_stock(quantity, order_id)` | Increases on_hand/available, raises `StockReturned` |

Private helper `_check_low_stock()` raises `LowStockDetected` when available <= reorder_point.

All state changes applied via `@apply` handlers for event-sourcing replay.

## Aggregate: Warehouse (CQRS)

**File:** `warehouse/warehouse.py`

Root fields: `name`, `address` (WarehouseAddress VO), `capacity` (default 0), `is_active` (default True), `zones` (HasMany Zone), `created_at`, `updated_at`.

### Enums
- `ZoneType`: Regular, Cold, Hazmat

### Value Objects (part_of="Warehouse")
- `WarehouseAddress` — street, city, state, postal_code, country

### Entities (part_of="Warehouse")
- `Zone` — zone_name, zone_type (default Regular)

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `Warehouse.create(name, address, capacity?)` | Class method, raises `WarehouseCreated` |
| `update_details(name?, capacity?)` | Partial update, raises `WarehouseUpdated` |
| `add_zone(zone_name, zone_type?)` | Creates Zone entity, raises `ZoneAdded` |
| `remove_zone(zone_id)` | Raises `ZoneRemoved` |
| `deactivate()` | Guards against double-deactivation, raises `WarehouseDeactivated` |

## Events

**InventoryItem events** (`stock/events.py`): `StockInitialized`, `StockReceived`, `StockReserved`, `ReservationReleased`, `ReservationConfirmed`, `StockCommitted`, `StockAdjusted`, `StockMarkedDamaged`, `DamagedStockWrittenOff`, `StockReturned`, `StockCheckRecorded`, `LowStockDetected`

**Warehouse events** (`warehouse/events.py`): `WarehouseCreated`, `WarehouseUpdated`, `ZoneAdded`, `ZoneRemoved`, `WarehouseDeactivated`

## Commands & Handlers

### InventoryItem Commands

| File | Commands |
|------|---------|
| `stock/initialization.py` | `InitializeStock` → `InitializeStockHandler` |
| `stock/receiving.py` | `ReceiveStock` → `ReceiveStockHandler` |
| `stock/reservation.py` | `ReserveStock`, `ReleaseReservation`, `ConfirmReservation` → `ReservationHandler` |
| `stock/adjustment.py` | `AdjustStock`, `RecordStockCheck` → `StockAdjustmentHandler` |
| `stock/damage.py` | `MarkDamaged`, `WriteOffDamaged` → `DamageHandler` |
| `stock/shipping.py` | `CommitStock` → `CommitStockHandler` |
| `stock/returns.py` | `ReturnToStock` → `ReturnToStockHandler` |

### Warehouse Commands

| File | Commands |
|------|---------|
| `warehouse/management.py` | `CreateWarehouse`, `UpdateWarehouse`, `AddZone`, `RemoveZone`, `DeactivateWarehouse` → `WarehouseManagementHandler` |

## Cross-Domain Integration

### Inbound: Fulfillment → Inventory
**File:** `stock/fulfillment_subscriber.py`

`@inventory.subscriber(broker="global", stream="fulfillment::fulfillment")` — receives raw dict payloads (ACL pattern).

Subscriber `FulfillmentEventsSubscriber`:
- `ShipmentHandedOff` → queries event store for all InventoryItem streams, finds confirmed reservations matching the order_id, dispatches `CommitStock` for each (reduces on_hand when items ship)

### Inbound: Catalogue → Inventory
**File:** `stock/catalogue_subscriber.py`

`@inventory.subscriber(broker="global", stream="catalogue::product")` — receives raw dict payloads (ACL pattern).

Subscriber `CatalogueEventsSubscriber`:
- `VariantAdded` → dispatches `InitializeStock` command

### Inbound: Ordering → Inventory
**File:** `stock/ordering_subscriber.py`

`@inventory.subscriber(broker="global", stream="ordering::order")` — receives raw dict payloads (ACL pattern).

Subscriber `OrderingEventsSubscriber`:
- `OrderCancelled` → releases reservations
- `OrderReturned` → logs for restocking

## Projections

**Directory:** `projections/`

| File | Projection | Projector | Purpose |
|------|-----------|-----------|---------|
| `inventory_level.py` | `InventoryLevel` | `InventoryLevelProjector` | Per-item stock levels for real-time display |
| `low_stock_report.py` | `LowStockReport` | `LowStockReportProjector` | Items below reorder point, auto-clears when stock recovers |
| `product_availability.py` | `ProductAvailability` | `ProductAvailabilityProjector` | Aggregated availability across warehouses (keyed by `product_id::variant_id`) |
| `reservation_status.py` | `ReservationStatus` | `ReservationStatusProjector` | Active reservations view for order status checks |
| `stock_movement_log.py` | `StockMovementLog` | `StockMovementLogProjector` | Append-only audit trail of all stock changes |
| `warehouse_stock.py` | `WarehouseStock` | `WarehouseStockProjector` | Per-warehouse stock summary for dashboard |

## API

**Package:** `api/`

| File | Contents |
|------|----------|
| `api/__init__.py` | Re-exports `inventory_router` and `warehouse_router` |
| `api/schemas.py` | Pydantic request/response models (external contract) |
| `api/routes.py` | 16 endpoints (11 inventory + 5 warehouse) |

### Inventory Endpoints (`tags=["inventory"]`)
| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| POST | `/inventory` | `InitializeStockRequest` | `InventoryItemIdResponse` (201) |
| PUT | `/inventory/{id}/receive` | `ReceiveStockRequest` | `StatusResponse` |
| POST | `/inventory/{id}/reserve` | `ReserveStockRequest` | `StatusResponse` (201) |
| PUT | `/inventory/{id}/reservations/{rid}/release` | `ReleaseReservationRequest` | `StatusResponse` |
| PUT | `/inventory/{id}/reservations/{rid}/confirm` | — | `StatusResponse` |
| PUT | `/inventory/{id}/commit/{rid}` | — | `StatusResponse` |
| PUT | `/inventory/{id}/adjust` | `AdjustStockRequest` | `StatusResponse` |
| PUT | `/inventory/{id}/damage` | `MarkDamagedRequest` | `StatusResponse` |
| PUT | `/inventory/{id}/damage/write-off` | `WriteOffDamagedRequest` | `StatusResponse` |
| PUT | `/inventory/{id}/return` | `ReturnToStockRequest` | `StatusResponse` |
| PUT | `/inventory/{id}/stock-check` | `RecordStockCheckRequest` | `StatusResponse` |

### Warehouse Endpoints (`tags=["warehouses"]`)
| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| POST | `/warehouses` | `CreateWarehouseRequest` | `WarehouseIdResponse` (201) |
| PUT | `/warehouses/{id}` | `UpdateWarehouseRequest` | `StatusResponse` |
| POST | `/warehouses/{id}/zones` | `AddZoneRequest` | `StatusResponse` (201) |
| DELETE | `/warehouses/{id}/zones/{zone_id}` | — | `StatusResponse` |
| PUT | `/warehouses/{id}/deactivate` | — | `StatusResponse` |
