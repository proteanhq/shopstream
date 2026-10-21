## Command Handlers: Fulfillment

```mermaid
flowchart LR
    subgraph command_handlers["Command Handlers"]
        ch_fulfillment_fulfillment_cancellation_CancelFulfillmentHandler[CancelFulfillmentHandler]
        ch_fulfillment_fulfillment_creation_CreateFulfillmentHandler[CreateFulfillmentHandler]
        ch_fulfillment_fulfillment_delivery_DeliveryHandler[DeliveryHandler]
        ch_fulfillment_fulfillment_packing_PackingHandler[PackingHandler]
        ch_fulfillment_fulfillment_picking_PickingHandler[PickingHandler]
        ch_fulfillment_fulfillment_shipping_ShippingHandler[ShippingHandler]
        ch_fulfillment_fulfillment_tracking_TrackingHandler[TrackingHandler]
    end
    cmd_fulfillment_fulfillment_cancellation_CancelFulfillment[/CancelFulfillment/] --> ch_fulfillment_fulfillment_cancellation_CancelFulfillmentHandler
    ch_fulfillment_fulfillment_cancellation_CancelFulfillmentHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment[Fulfillment]
    cmd_fulfillment_fulfillment_creation_CreateFulfillment[/CreateFulfillment/] --> ch_fulfillment_fulfillment_creation_CreateFulfillmentHandler
    ch_fulfillment_fulfillment_creation_CreateFulfillmentHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment[Fulfillment]
    cmd_fulfillment_fulfillment_delivery_RecordDeliveryConfirmation[/RecordDeliveryConfirmation/] --> ch_fulfillment_fulfillment_delivery_DeliveryHandler
    cmd_fulfillment_fulfillment_delivery_RecordDeliveryException[/RecordDeliveryException/] --> ch_fulfillment_fulfillment_delivery_DeliveryHandler
    ch_fulfillment_fulfillment_delivery_DeliveryHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment[Fulfillment]
    cmd_fulfillment_fulfillment_packing_GenerateShippingLabel[/GenerateShippingLabel/] --> ch_fulfillment_fulfillment_packing_PackingHandler
    cmd_fulfillment_fulfillment_packing_RecordPacking[/RecordPacking/] --> ch_fulfillment_fulfillment_packing_PackingHandler
    ch_fulfillment_fulfillment_packing_PackingHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment[Fulfillment]
    cmd_fulfillment_fulfillment_picking_AssignPicker[/AssignPicker/] --> ch_fulfillment_fulfillment_picking_PickingHandler
    cmd_fulfillment_fulfillment_picking_CompletePickList[/CompletePickList/] --> ch_fulfillment_fulfillment_picking_PickingHandler
    cmd_fulfillment_fulfillment_picking_RecordItemPicked[/RecordItemPicked/] --> ch_fulfillment_fulfillment_picking_PickingHandler
    ch_fulfillment_fulfillment_picking_PickingHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment[Fulfillment]
    cmd_fulfillment_fulfillment_shipping_RecordHandoff[/RecordHandoff/] --> ch_fulfillment_fulfillment_shipping_ShippingHandler
    ch_fulfillment_fulfillment_shipping_ShippingHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment[Fulfillment]
    cmd_fulfillment_fulfillment_tracking_UpdateTrackingEvent[/UpdateTrackingEvent/] --> ch_fulfillment_fulfillment_tracking_TrackingHandler
    ch_fulfillment_fulfillment_tracking_TrackingHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment[Fulfillment]
```

## Subscribers

```mermaid
flowchart TD
    subgraph subscribers["Subscribers"]
        sub_fulfillment_fulfillment_order_subscriber_OrderEventsSubscriber[OrderEventsSubscriber\nstream: ordering::order]
        sub_fulfillment_fulfillment_payment_subscriber_PaymentEventsSubscriber[PaymentEventsSubscriber\nstream: payments::payment]
    end
```

## Projector: DailyShipmentsView

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_fulfillment_projections_daily_shipments_DailyShipmentsProjector[DailyShipmentsProjector → DailyShipmentsView]
    end
    evt_fulfillment_fulfillment_events_DeliveryConfirmed([DeliveryConfirmed]) --> proj_fulfillment_projections_daily_shipments_DailyShipmentsProjector
    evt_fulfillment_fulfillment_events_DeliveryException([DeliveryException]) --> proj_fulfillment_projections_daily_shipments_DailyShipmentsProjector
    evt_fulfillment_fulfillment_events_FulfillmentCreated([FulfillmentCreated]) --> proj_fulfillment_projections_daily_shipments_DailyShipmentsProjector
    evt_fulfillment_fulfillment_events_ShipmentHandedOff([ShipmentHandedOff]) --> proj_fulfillment_projections_daily_shipments_DailyShipmentsProjector
```

## Projector: DeliveryPerformanceView

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_fulfillment_projections_delivery_performance_DeliveryPerformanceProjector[DeliveryPerformanceProjector → DeliveryPerformanceView]
    end
    evt_fulfillment_fulfillment_events_DeliveryConfirmed([DeliveryConfirmed]) --> proj_fulfillment_projections_delivery_performance_DeliveryPerformanceProjector
    evt_fulfillment_fulfillment_events_DeliveryException([DeliveryException]) --> proj_fulfillment_projections_delivery_performance_DeliveryPerformanceProjector
    evt_fulfillment_fulfillment_events_ShipmentHandedOff([ShipmentHandedOff]) --> proj_fulfillment_projections_delivery_performance_DeliveryPerformanceProjector
```

## Projector: FulfillmentStatusView

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector[FulfillmentStatusProjector → FulfillmentStatusView]
    end
    evt_fulfillment_fulfillment_events_DeliveryConfirmed([DeliveryConfirmed]) --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_DeliveryException([DeliveryException]) --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_FulfillmentCancelled([FulfillmentCancelled]) --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_FulfillmentCreated([FulfillmentCreated]) --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_ItemPicked([ItemPicked]) --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_PackingCompleted([PackingCompleted]) --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_PickerAssigned([PickerAssigned]) --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_PickingCompleted([PickingCompleted]) --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_ShipmentHandedOff([ShipmentHandedOff]) --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_ShippingLabelGenerated([ShippingLabelGenerated]) --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_TrackingEventReceived([TrackingEventReceived]) --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
```

## Projector: ShipmentTrackingView

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_fulfillment_projections_shipment_tracking_ShipmentTrackingProjector[ShipmentTrackingProjector → ShipmentTrackingView]
    end
    evt_fulfillment_fulfillment_events_DeliveryConfirmed([DeliveryConfirmed]) --> proj_fulfillment_projections_shipment_tracking_ShipmentTrackingProjector
    evt_fulfillment_fulfillment_events_DeliveryException([DeliveryException]) --> proj_fulfillment_projections_shipment_tracking_ShipmentTrackingProjector
    evt_fulfillment_fulfillment_events_ShipmentHandedOff([ShipmentHandedOff]) --> proj_fulfillment_projections_shipment_tracking_ShipmentTrackingProjector
    evt_fulfillment_fulfillment_events_TrackingEventReceived([TrackingEventReceived]) --> proj_fulfillment_projections_shipment_tracking_ShipmentTrackingProjector
```

## Projector: WarehouseQueueView

```mermaid
flowchart LR
    subgraph projectors["Projectors"]
        proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector[WarehouseQueueProjector → WarehouseQueueView]
    end
    evt_fulfillment_fulfillment_events_FulfillmentCancelled([FulfillmentCancelled]) --> proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector
    evt_fulfillment_fulfillment_events_FulfillmentCreated([FulfillmentCreated]) --> proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector
    evt_fulfillment_fulfillment_events_PackingCompleted([PackingCompleted]) --> proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector
    evt_fulfillment_fulfillment_events_PickerAssigned([PickerAssigned]) --> proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector
    evt_fulfillment_fulfillment_events_PickingCompleted([PickingCompleted]) --> proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector
    evt_fulfillment_fulfillment_events_ShipmentHandedOff([ShipmentHandedOff]) --> proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector
```
