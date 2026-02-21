"""Warehouse queue — picker's work queue view for warehouse operations."""

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.events import (
    FulfillmentCancelled,
    FulfillmentCreated,
    PackingCompleted,
    PickerAssigned,
    PickingCompleted,
    ShipmentHandedOff,
)
from fulfillment.fulfillment.fulfillment import Fulfillment


@fulfillment.projection
class WarehouseQueueView:
    fulfillment_id = Identifier(identifier=True, required=True)
    order_id = Identifier(required=True)
    warehouse_id = String()
    status = String(required=True)
    assigned_to = String()
    item_count = Integer(default=0)
    created_at = DateTime()
    updated_at = DateTime()


@fulfillment.projector(projector_for=WarehouseQueueView, aggregates=[Fulfillment])
class WarehouseQueueProjector:
    @on(FulfillmentCreated)
    def on_fulfillment_created(self, event):
        current_domain.repository_for(WarehouseQueueView).add(
            WarehouseQueueView(
                fulfillment_id=event.fulfillment_id,
                order_id=event.order_id,
                warehouse_id=event.warehouse_id,
                status="Pending",
                item_count=event.item_count,
                created_at=event.created_at,
                updated_at=event.created_at,
            )
        )

    @on(PickerAssigned)
    def on_picker_assigned(self, event):
        repo = current_domain.repository_for(WarehouseQueueView)
        view = repo.get(event.fulfillment_id)
        view.status = "Picking"
        view.assigned_to = event.assigned_to
        view.updated_at = event.assigned_at
        repo.add(view)

    @on(PickingCompleted)
    def on_picking_completed(self, event):
        repo = current_domain.repository_for(WarehouseQueueView)
        view = repo.get(event.fulfillment_id)
        view.status = "Packing"
        view.updated_at = event.completed_at
        repo.add(view)

    @on(PackingCompleted)
    def on_packing_completed(self, event):
        repo = current_domain.repository_for(WarehouseQueueView)
        view = repo.get(event.fulfillment_id)
        view.status = "Packed"
        view.updated_at = event.packed_at
        repo.add(view)

    @on(ShipmentHandedOff)
    def on_shipment_handed_off(self, event):
        repo = current_domain.repository_for(WarehouseQueueView)
        view = repo.get(event.fulfillment_id)
        view.status = "Shipped"
        view.updated_at = event.shipped_at
        repo.add(view)

    @on(FulfillmentCancelled)
    def on_fulfillment_cancelled(self, event):
        repo = current_domain.repository_for(WarehouseQueueView)
        view = repo.get(event.fulfillment_id)
        view.status = "Cancelled"
        view.updated_at = event.cancelled_at
        repo.add(view)
