"""Shipment tracking — customer-facing tracking page view."""

from datetime import datetime
from typing import Any

from protean import Index
from protean.core.projector import on
from protean.fields import DateTime, Dict, Identifier, List, String
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.events import (
    DeliveryConfirmed,
    DeliveryException,
    ShipmentHandedOff,
    TrackingEventReceived,
)
from fulfillment.fulfillment.fulfillment import Fulfillment


# Read path: tracking timeline for an order (filter by order_id).
@fulfillment.projection(indexes=[Index("order_id")])
class ShipmentTrackingView:
    fulfillment_id: str = Identifier(identifier=True, required=True)
    order_id: str = Identifier(required=True)
    carrier: str | None = String()
    tracking_number: str | None = String()
    current_status: str = String(required=True)
    current_location: str | None = String()
    events: list[dict[str, Any]] = List(Dict())
    shipped_at: datetime | None = DateTime()
    delivered_at: datetime | None = DateTime()


@fulfillment.projector(projector_for=ShipmentTrackingView, aggregates=[Fulfillment])
class ShipmentTrackingProjector:
    @on(ShipmentHandedOff)
    def on_shipment_handed_off(self, event: ShipmentHandedOff) -> None:
        current_domain.repository_for(ShipmentTrackingView).add(
            ShipmentTrackingView(
                fulfillment_id=event.fulfillment_id,
                order_id=event.order_id,
                carrier=event.carrier,
                tracking_number=event.tracking_number,
                current_status="Shipped",
                events=[],
                shipped_at=event.shipped_at,
            )
        )

    @on(TrackingEventReceived)
    def on_tracking_event_received(self, event: TrackingEventReceived) -> None:
        repo = current_domain.repository_for(ShipmentTrackingView)
        view = repo.get(event.fulfillment_id)
        view.current_status = event.status
        view.current_location = event.location

        # Append tracking event to the log
        existing = list(view.events or [])
        existing.append(
            {
                "status": event.status,
                "location": event.location,
                "description": event.description,
                "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            }
        )
        view.events = existing
        repo.add(view)

    @on(DeliveryConfirmed)
    def on_delivery_confirmed(self, event: DeliveryConfirmed) -> None:
        repo = current_domain.repository_for(ShipmentTrackingView)
        view = repo.get(event.fulfillment_id)
        view.current_status = "Delivered"
        view.delivered_at = event.delivered_at

        existing = list(view.events or [])
        existing.append(
            {
                "status": "Delivered",
                "location": "",
                "description": "Package delivered",
                "occurred_at": event.delivered_at.isoformat() if event.delivered_at else None,
            }
        )
        view.events = existing
        repo.add(view)

    @on(DeliveryException)
    def on_delivery_exception(self, event: DeliveryException) -> None:
        repo = current_domain.repository_for(ShipmentTrackingView)
        view = repo.get(event.fulfillment_id)
        view.current_status = "Exception"
        view.current_location = event.location

        existing = list(view.events or [])
        existing.append(
            {
                "status": "Exception",
                "location": event.location,
                "description": event.reason,
                "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            }
        )
        view.events = existing
        repo.add(view)
