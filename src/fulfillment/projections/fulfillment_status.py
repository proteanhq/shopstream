"""Fulfillment status — real-time fulfillment state view for order tracking."""

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.events import (
    DeliveryConfirmed,
    DeliveryException,
    FulfillmentCancelled,
    FulfillmentCreated,
    PackingCompleted,
    PickerAssigned,
    PickingCompleted,
    ShipmentHandedOff,
    ShippingLabelGenerated,
    TrackingEventReceived,
)
from fulfillment.fulfillment.fulfillment import Fulfillment


@fulfillment.projection
class FulfillmentStatusView:
    fulfillment_id = Identifier(identifier=True, required=True)
    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    warehouse_id = String()
    status = String(required=True)
    carrier = String()
    tracking_number = String()
    item_count = Integer(default=0)
    assigned_to = String()
    created_at = DateTime()
    updated_at = DateTime()


@fulfillment.projector(projector_for=FulfillmentStatusView, aggregates=[Fulfillment])
class FulfillmentStatusProjector:
    @on(FulfillmentCreated)
    def on_fulfillment_created(self, event):
        current_domain.repository_for(FulfillmentStatusView).add(
            FulfillmentStatusView(
                fulfillment_id=event.fulfillment_id,
                order_id=event.order_id,
                customer_id=event.customer_id,
                warehouse_id=event.warehouse_id,
                status="Pending",
                item_count=event.item_count,
                created_at=event.created_at,
                updated_at=event.created_at,
            )
        )

    @on(PickerAssigned)
    def on_picker_assigned(self, event):
        repo = current_domain.repository_for(FulfillmentStatusView)
        view = repo.get(event.fulfillment_id)
        view.status = "Picking"
        view.assigned_to = event.assigned_to
        view.updated_at = event.assigned_at
        repo.add(view)

    @on(PickingCompleted)
    def on_picking_completed(self, event):
        repo = current_domain.repository_for(FulfillmentStatusView)
        view = repo.get(event.fulfillment_id)
        view.status = "Packing"
        view.updated_at = event.completed_at
        repo.add(view)

    @on(PackingCompleted)
    def on_packing_completed(self, event):
        repo = current_domain.repository_for(FulfillmentStatusView)
        view = repo.get(event.fulfillment_id)
        view.updated_at = event.packed_at
        repo.add(view)

    @on(ShippingLabelGenerated)
    def on_shipping_label_generated(self, event):
        repo = current_domain.repository_for(FulfillmentStatusView)
        view = repo.get(event.fulfillment_id)
        view.status = "Ready_To_Ship"
        view.carrier = event.carrier
        view.updated_at = event.generated_at
        repo.add(view)

    @on(ShipmentHandedOff)
    def on_shipment_handed_off(self, event):
        repo = current_domain.repository_for(FulfillmentStatusView)
        view = repo.get(event.fulfillment_id)
        view.status = "Shipped"
        view.carrier = event.carrier
        view.tracking_number = event.tracking_number
        view.updated_at = event.shipped_at
        repo.add(view)

    @on(TrackingEventReceived)
    def on_tracking_event_received(self, event):
        repo = current_domain.repository_for(FulfillmentStatusView)
        view = repo.get(event.fulfillment_id)
        view.status = "In_Transit"
        view.updated_at = event.occurred_at
        repo.add(view)

    @on(DeliveryConfirmed)
    def on_delivery_confirmed(self, event):
        repo = current_domain.repository_for(FulfillmentStatusView)
        view = repo.get(event.fulfillment_id)
        view.status = "Delivered"
        view.updated_at = event.delivered_at
        repo.add(view)

    @on(DeliveryException)
    def on_delivery_exception(self, event):
        repo = current_domain.repository_for(FulfillmentStatusView)
        view = repo.get(event.fulfillment_id)
        view.status = "Exception"
        view.updated_at = event.occurred_at
        repo.add(view)

    @on(FulfillmentCancelled)
    def on_fulfillment_cancelled(self, event):
        repo = current_domain.repository_for(FulfillmentStatusView)
        view = repo.get(event.fulfillment_id)
        view.status = "Cancelled"
        view.updated_at = event.cancelled_at
        repo.add(view)
