# Event & Command Catalog

## InventoryItem (`inventory.stock.stock.InventoryItem`)

### Events

#### DamagedStockWrittenOff

- **Type**: `Inventory.DamagedStockWrittenOff.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| approved_by | String | Yes | max_length=255, min_length=1 |
| inventory_item_id | Identifier | Yes | min_length=1 |
| new_damaged | Integer | Yes | — |
| previous_damaged | Integer | Yes | — |
| product_id | Identifier | Yes | min_length=1 |
| quantity | Integer | Yes | — |
| written_off_at | DateTime | Yes | — |

#### LowStockDetected

- **Type**: `Inventory.LowStockDetected.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| current_available | Integer | Yes | — |
| detected_at | DateTime | Yes | — |
| inventory_item_id | Identifier | Yes | min_length=1 |
| product_id | Identifier | Yes | min_length=1 |
| reorder_point | Integer | Yes | — |
| sku | String | Yes | max_length=255, min_length=1 |
| variant_id | Identifier | Yes | min_length=1 |

#### ReservationConfirmed

- **Type**: `Inventory.ReservationConfirmed.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| confirmed_at | DateTime | Yes | — |
| inventory_item_id | Identifier | Yes | min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| quantity | Integer | Yes | — |
| reservation_id | Identifier | Yes | min_length=1 |

#### ReservationReleased

- **Type**: `Inventory.ReservationReleased.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| inventory_item_id | Identifier | Yes | min_length=1 |
| new_available | Integer | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| previous_available | Integer | Yes | — |
| quantity | Integer | Yes | — |
| reason | String | Yes | max_length=255, min_length=1 |
| released_at | DateTime | Yes | — |
| reservation_id | Identifier | Yes | min_length=1 |

#### StockAdjusted

- **Type**: `Inventory.StockAdjusted.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| adjusted_at | DateTime | Yes | — |
| adjusted_by | String | Yes | max_length=255, min_length=1 |
| adjustment_type | String | Yes | max_length=255, min_length=1 |
| inventory_item_id | Identifier | Yes | min_length=1 |
| new_available | Integer | Yes | — |
| new_on_hand | Integer | Yes | — |
| previous_on_hand | Integer | Yes | — |
| product_id | Identifier | Yes | min_length=1 |
| quantity_change | Integer | Yes | — |
| reason | String | Yes | max_length=255, min_length=1 |

#### StockCheckRecorded

- **Type**: `Inventory.StockCheckRecorded.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| checked_at | DateTime | Yes | — |
| checked_by | String | Yes | max_length=255, min_length=1 |
| counted_quantity | Integer | Yes | — |
| discrepancy | Integer | Yes | — |
| expected_quantity | Integer | Yes | — |
| inventory_item_id | Identifier | Yes | min_length=1 |

#### StockCommitted

- **Type**: `Inventory.StockCommitted.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| committed_at | DateTime | Yes | — |
| inventory_item_id | Identifier | Yes | min_length=1 |
| new_on_hand | Integer | Yes | — |
| new_reserved | Integer | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| previous_on_hand | Integer | Yes | — |
| previous_reserved | Integer | Yes | — |
| quantity | Integer | Yes | — |
| reservation_id | Identifier | Yes | min_length=1 |

#### StockInitialized

- **Type**: `Inventory.StockInitialized.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| initial_quantity | Integer | Yes | — |
| initialized_at | DateTime | Yes | — |
| inventory_item_id | Identifier | Yes | min_length=1 |
| product_id | Identifier | Yes | min_length=1 |
| reorder_point | Integer | Yes | — |
| reorder_quantity | Integer | Yes | — |
| sku | String | Yes | max_length=255, min_length=1 |
| variant_id | Identifier | Yes | min_length=1 |
| warehouse_id | Identifier | Yes | min_length=1 |

#### StockMarkedDamaged

- **Type**: `Inventory.StockMarkedDamaged.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| inventory_item_id | Identifier | Yes | min_length=1 |
| marked_at | DateTime | Yes | — |
| new_available | Integer | Yes | — |
| new_damaged | Integer | Yes | — |
| new_on_hand | Integer | Yes | — |
| previous_damaged | Integer | Yes | — |
| previous_on_hand | Integer | Yes | — |
| product_id | Identifier | Yes | min_length=1 |
| quantity | Integer | Yes | — |
| reason | String | Yes | max_length=255, min_length=1 |

#### StockReceived

- **Type**: `Inventory.StockReceived.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| inventory_item_id | Identifier | Yes | min_length=1 |
| new_available | Integer | Yes | — |
| new_on_hand | Integer | Yes | — |
| previous_on_hand | Integer | Yes | — |
| quantity | Integer | Yes | — |
| received_at | DateTime | Yes | — |
| reference | String | No | max_length=255 |

#### StockReserved

- **Type**: `Inventory.StockReserved.v1`
- **Version**: 1
- **Published**: Yes
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| expires_at | DateTime | Yes | — |
| inventory_item_id | Identifier | Yes | min_length=1 |
| new_available | Integer | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| previous_available | Integer | Yes | — |
| quantity | Integer | Yes | — |
| reservation_id | Identifier | Yes | min_length=1 |
| reserved_at | DateTime | Yes | — |

#### StockReturned

- **Type**: `Inventory.StockReturned.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| inventory_item_id | Identifier | Yes | min_length=1 |
| new_available | Integer | Yes | — |
| new_on_hand | Integer | Yes | — |
| order_id | Identifier | Yes | min_length=1 |
| previous_on_hand | Integer | Yes | — |
| quantity | Integer | Yes | — |
| returned_at | DateTime | Yes | — |

### Commands

#### AdjustStock

- **Type**: `Inventory.AdjustStock.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| adjusted_by | String | Yes | max_length=255, min_length=1 |
| adjustment_type | String | Yes | max_length=255, min_length=1 |
| inventory_item_id | Identifier | Yes | min_length=1 |
| quantity_change | Integer | Yes | — |
| reason | String | Yes | max_length=255, min_length=1 |

#### RecordStockCheck

- **Type**: `Inventory.RecordStockCheck.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| checked_by | String | Yes | max_length=255, min_length=1 |
| counted_quantity | Integer | Yes | — |
| inventory_item_id | Identifier | Yes | min_length=1 |

#### MarkDamaged

- **Type**: `Inventory.MarkDamaged.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| inventory_item_id | Identifier | Yes | min_length=1 |
| quantity | Integer | Yes | — |
| reason | String | Yes | max_length=255, min_length=1 |

#### WriteOffDamaged

- **Type**: `Inventory.WriteOffDamaged.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| approved_by | String | Yes | max_length=255, min_length=1 |
| inventory_item_id | Identifier | Yes | min_length=1 |
| quantity | Integer | Yes | — |

#### ExpireStaleReservations

- **Type**: `Inventory.ExpireStaleReservations.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| as_of | DateTime | No | — |
| older_than_minutes | Integer | No | — |

#### InitializeStock

- **Type**: `Inventory.InitializeStock.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| initial_quantity | Integer | No | — |
| product_id | Identifier | Yes | min_length=1 |
| reorder_point | Integer | No | — |
| reorder_quantity | Integer | No | — |
| sku | String | Yes | max_length=50, min_length=1 |
| variant_id | Identifier | Yes | min_length=1 |
| warehouse_id | Identifier | Yes | min_length=1 |

#### ReceiveStock

- **Type**: `Inventory.ReceiveStock.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| inventory_item_id | Identifier | Yes | min_length=1 |
| quantity | Integer | Yes | — |
| reference | String | No | max_length=255 |

#### ConfirmReservation

- **Type**: `Inventory.ConfirmReservation.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| inventory_item_id | Identifier | Yes | min_length=1 |
| reservation_id | Identifier | Yes | min_length=1 |

#### ReleaseReservation

- **Type**: `Inventory.ReleaseReservation.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| inventory_item_id | Identifier | Yes | min_length=1 |
| reason | String | Yes | max_length=255, min_length=1 |
| reservation_id | Identifier | Yes | min_length=1 |

#### ReserveStock

- **Type**: `Inventory.ReserveStock.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| expires_at | DateTime | No | — |
| inventory_item_id | Identifier | Yes | min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| quantity | Integer | Yes | — |

#### ReturnToStock

- **Type**: `Inventory.ReturnToStock.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| inventory_item_id | Identifier | Yes | min_length=1 |
| order_id | Identifier | Yes | min_length=1 |
| quantity | Integer | Yes | — |

#### CommitStock

- **Type**: `Inventory.CommitStock.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| inventory_item_id | Identifier | Yes | min_length=1 |
| reservation_id | Identifier | Yes | min_length=1 |

## Warehouse (`inventory.warehouse.warehouse.Warehouse`)

### Events

#### WarehouseCreated

- **Type**: `Inventory.WarehouseCreated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| address | Dict | Yes | — |
| capacity | Integer | Yes | — |
| created_at | DateTime | Yes | — |
| name | String | Yes | max_length=255, min_length=1 |
| warehouse_id | Identifier | Yes | min_length=1 |

#### WarehouseDeactivated

- **Type**: `Inventory.WarehouseDeactivated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| deactivated_at | DateTime | Yes | — |
| warehouse_id | Identifier | Yes | min_length=1 |

#### WarehouseUpdated

- **Type**: `Inventory.WarehouseUpdated.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| capacity | Integer | Yes | — |
| name | String | Yes | max_length=255, min_length=1 |
| updated_at | DateTime | Yes | — |
| warehouse_id | Identifier | Yes | min_length=1 |

#### ZoneAdded

- **Type**: `Inventory.ZoneAdded.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| added_at | DateTime | Yes | — |
| warehouse_id | Identifier | Yes | min_length=1 |
| zone_id | Identifier | Yes | min_length=1 |
| zone_name | String | Yes | max_length=255, min_length=1 |
| zone_type | String | Yes | max_length=255, min_length=1 |

#### ZoneRemoved

- **Type**: `Inventory.ZoneRemoved.v1`
- **Version**: 1
- **Published**: No
- **Fact Event**: No

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| removed_at | DateTime | Yes | — |
| warehouse_id | Identifier | Yes | min_length=1 |
| zone_id | Identifier | Yes | min_length=1 |

### Commands

#### AddZone

- **Type**: `Inventory.AddZone.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| warehouse_id | Identifier | Yes | min_length=1 |
| zone_name | String | Yes | max_length=100, min_length=1 |
| zone_type | String | No | max_length=50 |

#### CreateWarehouse

- **Type**: `Inventory.CreateWarehouse.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| address | Dict | Yes | — |
| capacity | Integer | No | — |
| name | String | Yes | max_length=255, min_length=1 |

#### DeactivateWarehouse

- **Type**: `Inventory.DeactivateWarehouse.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| warehouse_id | Identifier | Yes | min_length=1 |

#### RemoveZone

- **Type**: `Inventory.RemoveZone.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| warehouse_id | Identifier | Yes | min_length=1 |
| zone_id | Identifier | Yes | min_length=1 |

#### UpdateWarehouse

- **Type**: `Inventory.UpdateWarehouse.v1`
- **Version**: 1

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| capacity | Integer | No | — |
| name | String | No | max_length=255 |
| warehouse_id | Identifier | Yes | min_length=1 |

---

## Published Event Contracts

| Event | Type | Version |
|-------|------|---------|
| LowStockDetected | `Inventory.LowStockDetected.v1` | 1 |
| ReservationReleased | `Inventory.ReservationReleased.v1` | 1 |
| StockReserved | `Inventory.StockReserved.v1` | 1 |
