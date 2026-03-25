## Command Handlers: InventoryItem

```mermaid
flowchart LR
    subgraph command_handlers["Command Handlers"]
        ch_inventory_stock_adjustment_StockAdjustmentHandler[StockAdjustmentHandler]
        ch_inventory_stock_damage_DamageHandler[DamageHandler]
        ch_inventory_stock_expiry_ExpireStaleReservationsHandler[ExpireStaleReservationsHandler]
        ch_inventory_stock_initialization_InitializeStockHandler[InitializeStockHandler]
        ch_inventory_stock_receiving_ReceiveStockHandler[ReceiveStockHandler]
        ch_inventory_stock_reservation_ReservationHandler[ReservationHandler]
        ch_inventory_stock_returns_ReturnToStockHandler[ReturnToStockHandler]
        ch_inventory_stock_shipping_CommitStockHandler[CommitStockHandler]
    end
    cmd_inventory_stock_adjustment_AdjustStock[/AdjustStock/] --> ch_inventory_stock_adjustment_StockAdjustmentHandler
    cmd_inventory_stock_adjustment_RecordStockCheck[/RecordStockCheck/] --> ch_inventory_stock_adjustment_StockAdjustmentHandler
    ch_inventory_stock_adjustment_StockAdjustmentHandler --> agg_inventory_stock_stock_InventoryItem[InventoryItem]
    cmd_inventory_stock_damage_MarkDamaged[/MarkDamaged/] --> ch_inventory_stock_damage_DamageHandler
    cmd_inventory_stock_damage_WriteOffDamaged[/WriteOffDamaged/] --> ch_inventory_stock_damage_DamageHandler
    ch_inventory_stock_damage_DamageHandler --> agg_inventory_stock_stock_InventoryItem[InventoryItem]
    cmd_inventory_stock_expiry_ExpireStaleReservations[/ExpireStaleReservations/] --> ch_inventory_stock_expiry_ExpireStaleReservationsHandler
    ch_inventory_stock_expiry_ExpireStaleReservationsHandler --> agg_inventory_stock_stock_InventoryItem[InventoryItem]
    cmd_inventory_stock_initialization_InitializeStock[/InitializeStock/] --> ch_inventory_stock_initialization_InitializeStockHandler
    ch_inventory_stock_initialization_InitializeStockHandler --> agg_inventory_stock_stock_InventoryItem[InventoryItem]
    cmd_inventory_stock_receiving_ReceiveStock[/ReceiveStock/] --> ch_inventory_stock_receiving_ReceiveStockHandler
    ch_inventory_stock_receiving_ReceiveStockHandler --> agg_inventory_stock_stock_InventoryItem[InventoryItem]
    cmd_inventory_stock_reservation_ConfirmReservation[/ConfirmReservation/] --> ch_inventory_stock_reservation_ReservationHandler
    cmd_inventory_stock_reservation_ReleaseReservation[/ReleaseReservation/] --> ch_inventory_stock_reservation_ReservationHandler
    cmd_inventory_stock_reservation_ReserveStock[/ReserveStock/] --> ch_inventory_stock_reservation_ReservationHandler
    ch_inventory_stock_reservation_ReservationHandler --> agg_inventory_stock_stock_InventoryItem[InventoryItem]
    cmd_inventory_stock_returns_ReturnToStock[/ReturnToStock/] --> ch_inventory_stock_returns_ReturnToStockHandler
    ch_inventory_stock_returns_ReturnToStockHandler --> agg_inventory_stock_stock_InventoryItem[InventoryItem]
    cmd_inventory_stock_shipping_CommitStock[/CommitStock/] --> ch_inventory_stock_shipping_CommitStockHandler
    ch_inventory_stock_shipping_CommitStockHandler --> agg_inventory_stock_stock_InventoryItem[InventoryItem]
```

## Command Handlers: Warehouse

```mermaid
flowchart LR
    subgraph command_handlers["Command Handlers"]
        ch_inventory_warehouse_management_WarehouseManagementHandler[WarehouseManagementHandler]
    end
    cmd_inventory_warehouse_management_AddZone[/AddZone/] --> ch_inventory_warehouse_management_WarehouseManagementHandler
    cmd_inventory_warehouse_management_CreateWarehouse[/CreateWarehouse/] --> ch_inventory_warehouse_management_WarehouseManagementHandler
    cmd_inventory_warehouse_management_DeactivateWarehouse[/DeactivateWarehouse/] --> ch_inventory_warehouse_management_WarehouseManagementHandler
    cmd_inventory_warehouse_management_RemoveZone[/RemoveZone/] --> ch_inventory_warehouse_management_WarehouseManagementHandler
    cmd_inventory_warehouse_management_UpdateWarehouse[/UpdateWarehouse/] --> ch_inventory_warehouse_management_WarehouseManagementHandler
    ch_inventory_warehouse_management_WarehouseManagementHandler --> agg_inventory_warehouse_warehouse_Warehouse[Warehouse]
```

## Subscribers

```mermaid
flowchart TD
    subgraph subscribers["Subscribers"]
        sub_inventory_stock_catalogue_subscriber_CatalogueVariantSubscriber[CatalogueVariantSubscriber\nstream: catalogue::product]
        sub_inventory_stock_fulfillment_subscriber_FulfillmentEventsSubscriber[FulfillmentEventsSubscriber\nstream: fulfillment::fulfillment]
        sub_inventory_stock_ordering_subscriber_OrderingEventsSubscriber[OrderingEventsSubscriber\nstream: ordering::order]
    end
```

## Projector: InventoryLevel

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_inventory_projections_inventory_level_InventoryLevelProjector[InventoryLevelProjector → InventoryLevel]
    end
    evt_inventory_stock_events_DamagedStockWrittenOff([DamagedStockWrittenOff]) --> proj_inventory_projections_inventory_level_InventoryLevelProjector
    evt_inventory_stock_events_ReservationReleased([ReservationReleased]) --> proj_inventory_projections_inventory_level_InventoryLevelProjector
    evt_inventory_stock_events_StockAdjusted([StockAdjusted]) --> proj_inventory_projections_inventory_level_InventoryLevelProjector
    evt_inventory_stock_events_StockCommitted([StockCommitted]) --> proj_inventory_projections_inventory_level_InventoryLevelProjector
    evt_inventory_stock_events_StockInitialized([StockInitialized]) --> proj_inventory_projections_inventory_level_InventoryLevelProjector
    evt_inventory_stock_events_StockMarkedDamaged([StockMarkedDamaged]) --> proj_inventory_projections_inventory_level_InventoryLevelProjector
    evt_inventory_stock_events_StockReceived([StockReceived]) --> proj_inventory_projections_inventory_level_InventoryLevelProjector
    evt_inventory_stock_events_StockReserved([StockReserved]) --> proj_inventory_projections_inventory_level_InventoryLevelProjector
    evt_inventory_stock_events_StockReturned([StockReturned]) --> proj_inventory_projections_inventory_level_InventoryLevelProjector
```

## Projector: InventoryValuation

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_inventory_projections_inventory_valuation_InventoryValuationProjector[InventoryValuationProjector → InventoryValuation]
    end
    evt_inventory_stock_events_DamagedStockWrittenOff([DamagedStockWrittenOff]) --> proj_inventory_projections_inventory_valuation_InventoryValuationProjector
    evt_inventory_stock_events_StockAdjusted([StockAdjusted]) --> proj_inventory_projections_inventory_valuation_InventoryValuationProjector
    evt_inventory_stock_events_StockCommitted([StockCommitted]) --> proj_inventory_projections_inventory_valuation_InventoryValuationProjector
    evt_inventory_stock_events_StockInitialized([StockInitialized]) --> proj_inventory_projections_inventory_valuation_InventoryValuationProjector
    evt_inventory_stock_events_StockReceived([StockReceived]) --> proj_inventory_projections_inventory_valuation_InventoryValuationProjector
    evt_inventory_stock_events_StockReturned([StockReturned]) --> proj_inventory_projections_inventory_valuation_InventoryValuationProjector
```

## Projector: LowStockReport

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_inventory_projections_low_stock_report_LowStockReportProjector[LowStockReportProjector → LowStockReport]
    end
    evt_inventory_stock_events_LowStockDetected([LowStockDetected]) --> proj_inventory_projections_low_stock_report_LowStockReportProjector
    evt_inventory_stock_events_StockReceived([StockReceived]) --> proj_inventory_projections_low_stock_report_LowStockReportProjector
    evt_inventory_stock_events_StockReturned([StockReturned]) --> proj_inventory_projections_low_stock_report_LowStockReportProjector
```

## Projector: ProductAvailability

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_inventory_projections_product_availability_ProductAvailabilityProjector[ProductAvailabilityProjector → ProductAvailability]
    end
    evt_inventory_stock_events_ReservationReleased([ReservationReleased]) --> proj_inventory_projections_product_availability_ProductAvailabilityProjector
    evt_inventory_stock_events_StockAdjusted([StockAdjusted]) --> proj_inventory_projections_product_availability_ProductAvailabilityProjector
    evt_inventory_stock_events_StockCommitted([StockCommitted]) --> proj_inventory_projections_product_availability_ProductAvailabilityProjector
    evt_inventory_stock_events_StockInitialized([StockInitialized]) --> proj_inventory_projections_product_availability_ProductAvailabilityProjector
    evt_inventory_stock_events_StockMarkedDamaged([StockMarkedDamaged]) --> proj_inventory_projections_product_availability_ProductAvailabilityProjector
    evt_inventory_stock_events_StockReceived([StockReceived]) --> proj_inventory_projections_product_availability_ProductAvailabilityProjector
    evt_inventory_stock_events_StockReserved([StockReserved]) --> proj_inventory_projections_product_availability_ProductAvailabilityProjector
    evt_inventory_stock_events_StockReturned([StockReturned]) --> proj_inventory_projections_product_availability_ProductAvailabilityProjector
```

## Projector: ReservationStatus

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_inventory_projections_reservation_status_ReservationStatusProjector[ReservationStatusProjector → ReservationStatus]
    end
    evt_inventory_stock_events_ReservationConfirmed([ReservationConfirmed]) --> proj_inventory_projections_reservation_status_ReservationStatusProjector
    evt_inventory_stock_events_ReservationReleased([ReservationReleased]) --> proj_inventory_projections_reservation_status_ReservationStatusProjector
    evt_inventory_stock_events_StockCommitted([StockCommitted]) --> proj_inventory_projections_reservation_status_ReservationStatusProjector
    evt_inventory_stock_events_StockReserved([StockReserved]) --> proj_inventory_projections_reservation_status_ReservationStatusProjector
```

## Projector: ShrinkageReport

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_inventory_projections_shrinkage_report_ShrinkageReportProjector[ShrinkageReportProjector → ShrinkageReport]
    end
    evt_inventory_stock_events_DamagedStockWrittenOff([DamagedStockWrittenOff]) --> proj_inventory_projections_shrinkage_report_ShrinkageReportProjector
    evt_inventory_stock_events_StockAdjusted([StockAdjusted]) --> proj_inventory_projections_shrinkage_report_ShrinkageReportProjector
    evt_inventory_stock_events_StockMarkedDamaged([StockMarkedDamaged]) --> proj_inventory_projections_shrinkage_report_ShrinkageReportProjector
```

## Projector: StockMovementLog

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_inventory_projections_stock_movement_log_StockMovementLogProjector[StockMovementLogProjector → StockMovementLog]
    end
    evt_inventory_stock_events_DamagedStockWrittenOff([DamagedStockWrittenOff]) --> proj_inventory_projections_stock_movement_log_StockMovementLogProjector
    evt_inventory_stock_events_ReservationConfirmed([ReservationConfirmed]) --> proj_inventory_projections_stock_movement_log_StockMovementLogProjector
    evt_inventory_stock_events_ReservationReleased([ReservationReleased]) --> proj_inventory_projections_stock_movement_log_StockMovementLogProjector
    evt_inventory_stock_events_StockAdjusted([StockAdjusted]) --> proj_inventory_projections_stock_movement_log_StockMovementLogProjector
    evt_inventory_stock_events_StockCheckRecorded([StockCheckRecorded]) --> proj_inventory_projections_stock_movement_log_StockMovementLogProjector
    evt_inventory_stock_events_StockCommitted([StockCommitted]) --> proj_inventory_projections_stock_movement_log_StockMovementLogProjector
    evt_inventory_stock_events_StockInitialized([StockInitialized]) --> proj_inventory_projections_stock_movement_log_StockMovementLogProjector
    evt_inventory_stock_events_StockMarkedDamaged([StockMarkedDamaged]) --> proj_inventory_projections_stock_movement_log_StockMovementLogProjector
    evt_inventory_stock_events_StockReceived([StockReceived]) --> proj_inventory_projections_stock_movement_log_StockMovementLogProjector
    evt_inventory_stock_events_StockReserved([StockReserved]) --> proj_inventory_projections_stock_movement_log_StockMovementLogProjector
    evt_inventory_stock_events_StockReturned([StockReturned]) --> proj_inventory_projections_stock_movement_log_StockMovementLogProjector
```

## Projector: WarehouseDirectory

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_inventory_projections_warehouse_directory_WarehouseDirectoryProjector[WarehouseDirectoryProjector → WarehouseDirectory]
    end
    evt_inventory_warehouse_events_WarehouseCreated([WarehouseCreated]) --> proj_inventory_projections_warehouse_directory_WarehouseDirectoryProjector
    evt_inventory_warehouse_events_WarehouseDeactivated([WarehouseDeactivated]) --> proj_inventory_projections_warehouse_directory_WarehouseDirectoryProjector
    evt_inventory_warehouse_events_WarehouseUpdated([WarehouseUpdated]) --> proj_inventory_projections_warehouse_directory_WarehouseDirectoryProjector
    evt_inventory_warehouse_events_ZoneAdded([ZoneAdded]) --> proj_inventory_projections_warehouse_directory_WarehouseDirectoryProjector
    evt_inventory_warehouse_events_ZoneRemoved([ZoneRemoved]) --> proj_inventory_projections_warehouse_directory_WarehouseDirectoryProjector
```

## Projector: WarehouseStock

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_inventory_projections_warehouse_stock_WarehouseStockProjector[WarehouseStockProjector → WarehouseStock]
    end
    evt_inventory_stock_events_DamagedStockWrittenOff([DamagedStockWrittenOff]) --> proj_inventory_projections_warehouse_stock_WarehouseStockProjector
    evt_inventory_stock_events_ReservationReleased([ReservationReleased]) --> proj_inventory_projections_warehouse_stock_WarehouseStockProjector
    evt_inventory_stock_events_StockAdjusted([StockAdjusted]) --> proj_inventory_projections_warehouse_stock_WarehouseStockProjector
    evt_inventory_stock_events_StockCommitted([StockCommitted]) --> proj_inventory_projections_warehouse_stock_WarehouseStockProjector
    evt_inventory_stock_events_StockInitialized([StockInitialized]) --> proj_inventory_projections_warehouse_stock_WarehouseStockProjector
    evt_inventory_stock_events_StockMarkedDamaged([StockMarkedDamaged]) --> proj_inventory_projections_warehouse_stock_WarehouseStockProjector
    evt_inventory_stock_events_StockReceived([StockReceived]) --> proj_inventory_projections_warehouse_stock_WarehouseStockProjector
    evt_inventory_stock_events_StockReserved([StockReserved]) --> proj_inventory_projections_warehouse_stock_WarehouseStockProjector
    evt_inventory_stock_events_StockReturned([StockReturned]) --> proj_inventory_projections_warehouse_stock_WarehouseStockProjector
```
