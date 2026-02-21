"""Daily shipments — operations dashboard aggregate view."""

from datetime import datetime

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.events import (
    DeliveryConfirmed,
    DeliveryException,
    FulfillmentCreated,
    ShipmentHandedOff,
)
from fulfillment.fulfillment.fulfillment import Fulfillment


@fulfillment.projection
class DailyShipmentsView:
    """Daily aggregate of fulfillment operations."""

    id = Identifier(identifier=True)
    date = String(required=True)  # ISO date string YYYY-MM-DD
    total_created = Integer(default=0)
    total_shipped = Integer(default=0)
    total_delivered = Integer(default=0)
    total_exceptions = Integer(default=0)
    updated_at = DateTime()


def _date_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d") if dt else ""


def _get_or_create(date_str: str, timestamp: datetime):
    repo = current_domain.repository_for(DailyShipmentsView)
    try:
        return repo.get(date_str)
    except Exception:
        view = DailyShipmentsView(
            id=date_str,
            date=date_str,
            total_created=0,
            total_shipped=0,
            total_delivered=0,
            total_exceptions=0,
            updated_at=timestamp,
        )
        return view


@fulfillment.projector(projector_for=DailyShipmentsView, aggregates=[Fulfillment])
class DailyShipmentsProjector:
    @on(FulfillmentCreated)
    def on_fulfillment_created(self, event):
        date_str = _date_key(event.created_at)
        view = _get_or_create(date_str, event.created_at)
        view.total_created = (view.total_created or 0) + 1
        view.updated_at = event.created_at
        current_domain.repository_for(DailyShipmentsView).add(view)

    @on(ShipmentHandedOff)
    def on_shipment_handed_off(self, event):
        date_str = _date_key(event.shipped_at)
        view = _get_or_create(date_str, event.shipped_at)
        view.total_shipped = (view.total_shipped or 0) + 1
        view.updated_at = event.shipped_at
        current_domain.repository_for(DailyShipmentsView).add(view)

    @on(DeliveryConfirmed)
    def on_delivery_confirmed(self, event):
        date_str = _date_key(event.delivered_at)
        view = _get_or_create(date_str, event.delivered_at)
        view.total_delivered = (view.total_delivered or 0) + 1
        view.updated_at = event.delivered_at
        current_domain.repository_for(DailyShipmentsView).add(view)

    @on(DeliveryException)
    def on_delivery_exception(self, event):
        date_str = _date_key(event.occurred_at)
        view = _get_or_create(date_str, event.occurred_at)
        view.total_exceptions = (view.total_exceptions or 0) + 1
        view.updated_at = event.occurred_at
        current_domain.repository_for(DailyShipmentsView).add(view)
