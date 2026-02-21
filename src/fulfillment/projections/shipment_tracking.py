"""Shipment tracking — customer-facing tracking page view."""

import json

from protean.core.projector import on
from protean.fields import DateTime, Identifier, String, Text
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.events import (
    DeliveryConfirmed,
    DeliveryException,
    ShipmentHandedOff,
    TrackingEventReceived,
)
from fulfillment.fulfillment.fulfillment import Fulfillment


@fulfillment.projection
class ShipmentTrackingView:
    fulfillment_id = Identifier(identifier=True, required=True)
    order_id = Identifier(required=True)
    carrier = String()
    tracking_number = String()
    current_status = String(required=True)
    current_location = String()
    events_json = Text()  # JSON list of tracking events
    shipped_at = DateTime()
    delivered_at = DateTime()


@fulfillment.projector(projector_for=ShipmentTrackingView, aggregates=[Fulfillment])
class ShipmentTrackingProjector:
    @on(ShipmentHandedOff)
    def on_shipment_handed_off(self, event):
        current_domain.repository_for(ShipmentTrackingView).add(
            ShipmentTrackingView(
                fulfillment_id=event.fulfillment_id,
                order_id=event.order_id,
                carrier=event.carrier,
                tracking_number=event.tracking_number,
                current_status="Shipped",
                events_json=json.dumps([]),
                shipped_at=event.shipped_at,
            )
        )

    @on(TrackingEventReceived)
    def on_tracking_event_received(self, event):
        repo = current_domain.repository_for(ShipmentTrackingView)
        view = repo.get(event.fulfillment_id)
        view.current_status = event.status
        view.current_location = event.location

        # Append tracking event to the log
        existing = json.loads(view.events_json) if view.events_json else []
        existing.append(
            {
                "status": event.status,
                "location": event.location,
                "description": event.description,
                "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            }
        )
        view.events_json = json.dumps(existing)
        repo.add(view)

    @on(DeliveryConfirmed)
    def on_delivery_confirmed(self, event):
        repo = current_domain.repository_for(ShipmentTrackingView)
        view = repo.get(event.fulfillment_id)
        view.current_status = "Delivered"
        view.delivered_at = event.delivered_at

        existing = json.loads(view.events_json) if view.events_json else []
        existing.append(
            {
                "status": "Delivered",
                "location": "",
                "description": "Package delivered",
                "occurred_at": event.delivered_at.isoformat() if event.delivered_at else None,
            }
        )
        view.events_json = json.dumps(existing)
        repo.add(view)

    @on(DeliveryException)
    def on_delivery_exception(self, event):
        repo = current_domain.repository_for(ShipmentTrackingView)
        view = repo.get(event.fulfillment_id)
        view.current_status = "Exception"
        view.current_location = event.location

        existing = json.loads(view.events_json) if view.events_json else []
        existing.append(
            {
                "status": "Exception",
                "location": event.location,
                "description": event.reason,
                "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            }
        )
        view.events_json = json.dumps(existing)
        repo.add(view)
