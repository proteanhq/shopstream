## Event Flows

```mermaid
flowchart LR
    subgraph abc_DefaultOutbox[DefaultOutbox]
        agg_abc_DefaultOutbox[DefaultOutbox]
    end
    subgraph abc_MemoryOutbox[MemoryOutbox]
        agg_abc_MemoryOutbox[MemoryOutbox]
    end
    subgraph fulfillment_fulfillment_fulfillment_Fulfillment[Fulfillment]
        agg_fulfillment_fulfillment_fulfillment_Fulfillment[Fulfillment]
        cmd_fulfillment_fulfillment_cancellation_CancelFulfillment[/CancelFulfillment/]
        cmd_fulfillment_fulfillment_creation_CreateFulfillment[/CreateFulfillment/]
        cmd_fulfillment_fulfillment_delivery_RecordDeliveryConfirmation[/RecordDeliveryConfirmation/]
        cmd_fulfillment_fulfillment_delivery_RecordDeliveryException[/RecordDeliveryException/]
        cmd_fulfillment_fulfillment_packing_GenerateShippingLabel[/GenerateShippingLabel/]
        cmd_fulfillment_fulfillment_packing_RecordPacking[/RecordPacking/]
        cmd_fulfillment_fulfillment_picking_AssignPicker[/AssignPicker/]
        cmd_fulfillment_fulfillment_picking_CompletePickList[/CompletePickList/]
        cmd_fulfillment_fulfillment_picking_RecordItemPicked[/RecordItemPicked/]
        cmd_fulfillment_fulfillment_shipping_RecordHandoff[/RecordHandoff/]
        cmd_fulfillment_fulfillment_tracking_UpdateTrackingEvent[/UpdateTrackingEvent/]
        evt_fulfillment_fulfillment_events_DeliveryConfirmed([DeliveryConfirmed])
        evt_fulfillment_fulfillment_events_DeliveryException([DeliveryException])
        evt_fulfillment_fulfillment_events_FulfillmentCancelled([FulfillmentCancelled])
        evt_fulfillment_fulfillment_events_FulfillmentCreated([FulfillmentCreated])
        evt_fulfillment_fulfillment_events_ItemPicked([ItemPicked])
        evt_fulfillment_fulfillment_events_PackingCompleted([PackingCompleted])
        evt_fulfillment_fulfillment_events_PickerAssigned([PickerAssigned])
        evt_fulfillment_fulfillment_events_PickingCompleted([PickingCompleted])
        evt_fulfillment_fulfillment_events_ShipmentHandedOff([ShipmentHandedOff])
        evt_fulfillment_fulfillment_events_ShippingLabelGenerated([ShippingLabelGenerated])
        evt_fulfillment_fulfillment_events_TrackingEventReceived([TrackingEventReceived])
        hdlr_fulfillment_fulfillment_cancellation_CancelFulfillmentHandler[CancelFulfillmentHandler]
        hdlr_fulfillment_fulfillment_creation_CreateFulfillmentHandler[CreateFulfillmentHandler]
        hdlr_fulfillment_fulfillment_delivery_DeliveryHandler[DeliveryHandler]
        hdlr_fulfillment_fulfillment_packing_PackingHandler[PackingHandler]
        hdlr_fulfillment_fulfillment_picking_PickingHandler[PickingHandler]
        hdlr_fulfillment_fulfillment_shipping_ShippingHandler[ShippingHandler]
        hdlr_fulfillment_fulfillment_tracking_TrackingHandler[TrackingHandler]
    end
    cmd_fulfillment_fulfillment_cancellation_CancelFulfillment --> hdlr_fulfillment_fulfillment_cancellation_CancelFulfillmentHandler
    hdlr_fulfillment_fulfillment_cancellation_CancelFulfillmentHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment
    cmd_fulfillment_fulfillment_creation_CreateFulfillment --> hdlr_fulfillment_fulfillment_creation_CreateFulfillmentHandler
    hdlr_fulfillment_fulfillment_creation_CreateFulfillmentHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment
    cmd_fulfillment_fulfillment_delivery_RecordDeliveryConfirmation --> hdlr_fulfillment_fulfillment_delivery_DeliveryHandler
    cmd_fulfillment_fulfillment_delivery_RecordDeliveryException --> hdlr_fulfillment_fulfillment_delivery_DeliveryHandler
    hdlr_fulfillment_fulfillment_delivery_DeliveryHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment
    cmd_fulfillment_fulfillment_packing_GenerateShippingLabel --> hdlr_fulfillment_fulfillment_packing_PackingHandler
    cmd_fulfillment_fulfillment_packing_RecordPacking --> hdlr_fulfillment_fulfillment_packing_PackingHandler
    hdlr_fulfillment_fulfillment_packing_PackingHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment
    cmd_fulfillment_fulfillment_picking_AssignPicker --> hdlr_fulfillment_fulfillment_picking_PickingHandler
    cmd_fulfillment_fulfillment_picking_CompletePickList --> hdlr_fulfillment_fulfillment_picking_PickingHandler
    cmd_fulfillment_fulfillment_picking_RecordItemPicked --> hdlr_fulfillment_fulfillment_picking_PickingHandler
    hdlr_fulfillment_fulfillment_picking_PickingHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment
    cmd_fulfillment_fulfillment_shipping_RecordHandoff --> hdlr_fulfillment_fulfillment_shipping_ShippingHandler
    hdlr_fulfillment_fulfillment_shipping_ShippingHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment
    cmd_fulfillment_fulfillment_tracking_UpdateTrackingEvent --> hdlr_fulfillment_fulfillment_tracking_TrackingHandler
    hdlr_fulfillment_fulfillment_tracking_TrackingHandler --> agg_fulfillment_fulfillment_fulfillment_Fulfillment
    agg_fulfillment_fulfillment_fulfillment_Fulfillment --> evt_fulfillment_fulfillment_events_DeliveryConfirmed
    agg_fulfillment_fulfillment_fulfillment_Fulfillment --> evt_fulfillment_fulfillment_events_DeliveryException
    agg_fulfillment_fulfillment_fulfillment_Fulfillment --> evt_fulfillment_fulfillment_events_FulfillmentCancelled
    agg_fulfillment_fulfillment_fulfillment_Fulfillment --> evt_fulfillment_fulfillment_events_FulfillmentCreated
    agg_fulfillment_fulfillment_fulfillment_Fulfillment --> evt_fulfillment_fulfillment_events_ItemPicked
    agg_fulfillment_fulfillment_fulfillment_Fulfillment --> evt_fulfillment_fulfillment_events_PackingCompleted
    agg_fulfillment_fulfillment_fulfillment_Fulfillment --> evt_fulfillment_fulfillment_events_PickerAssigned
    agg_fulfillment_fulfillment_fulfillment_Fulfillment --> evt_fulfillment_fulfillment_events_PickingCompleted
    agg_fulfillment_fulfillment_fulfillment_Fulfillment --> evt_fulfillment_fulfillment_events_ShipmentHandedOff
    agg_fulfillment_fulfillment_fulfillment_Fulfillment --> evt_fulfillment_fulfillment_events_ShippingLabelGenerated
    agg_fulfillment_fulfillment_fulfillment_Fulfillment --> evt_fulfillment_fulfillment_events_TrackingEventReceived
    proj_fulfillment_projections_daily_shipments_DailyShipmentsProjector[DailyShipmentsProjector → DailyShipmentsView]
    evt_fulfillment_fulfillment_events_DeliveryConfirmed --> proj_fulfillment_projections_daily_shipments_DailyShipmentsProjector
    evt_fulfillment_fulfillment_events_DeliveryException --> proj_fulfillment_projections_daily_shipments_DailyShipmentsProjector
    evt_fulfillment_fulfillment_events_FulfillmentCreated --> proj_fulfillment_projections_daily_shipments_DailyShipmentsProjector
    evt_fulfillment_fulfillment_events_ShipmentHandedOff --> proj_fulfillment_projections_daily_shipments_DailyShipmentsProjector
    proj_fulfillment_projections_delivery_performance_DeliveryPerformanceProjector[DeliveryPerformanceProjector → DeliveryPerformanceView]
    evt_fulfillment_fulfillment_events_DeliveryConfirmed --> proj_fulfillment_projections_delivery_performance_DeliveryPerformanceProjector
    evt_fulfillment_fulfillment_events_DeliveryException --> proj_fulfillment_projections_delivery_performance_DeliveryPerformanceProjector
    evt_fulfillment_fulfillment_events_ShipmentHandedOff --> proj_fulfillment_projections_delivery_performance_DeliveryPerformanceProjector
    proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector[FulfillmentStatusProjector → FulfillmentStatusView]
    evt_fulfillment_fulfillment_events_DeliveryConfirmed --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_DeliveryException --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_FulfillmentCancelled --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_FulfillmentCreated --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_ItemPicked --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_PackingCompleted --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_PickerAssigned --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_PickingCompleted --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_ShipmentHandedOff --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_ShippingLabelGenerated --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    evt_fulfillment_fulfillment_events_TrackingEventReceived --> proj_fulfillment_projections_fulfillment_status_FulfillmentStatusProjector
    proj_fulfillment_projections_shipment_tracking_ShipmentTrackingProjector[ShipmentTrackingProjector → ShipmentTrackingView]
    evt_fulfillment_fulfillment_events_DeliveryConfirmed --> proj_fulfillment_projections_shipment_tracking_ShipmentTrackingProjector
    evt_fulfillment_fulfillment_events_DeliveryException --> proj_fulfillment_projections_shipment_tracking_ShipmentTrackingProjector
    evt_fulfillment_fulfillment_events_ShipmentHandedOff --> proj_fulfillment_projections_shipment_tracking_ShipmentTrackingProjector
    evt_fulfillment_fulfillment_events_TrackingEventReceived --> proj_fulfillment_projections_shipment_tracking_ShipmentTrackingProjector
    proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector[WarehouseQueueProjector → WarehouseQueueView]
    evt_fulfillment_fulfillment_events_FulfillmentCancelled --> proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector
    evt_fulfillment_fulfillment_events_FulfillmentCreated --> proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector
    evt_fulfillment_fulfillment_events_PackingCompleted --> proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector
    evt_fulfillment_fulfillment_events_PickerAssigned --> proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector
    evt_fulfillment_fulfillment_events_PickingCompleted --> proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector
    evt_fulfillment_fulfillment_events_ShipmentHandedOff --> proj_fulfillment_projections_warehouse_queue_WarehouseQueueProjector
```
