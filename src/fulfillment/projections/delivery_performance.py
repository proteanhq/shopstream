"""Delivery performance — carrier SLA monitoring view."""

from datetime import datetime

from protean.core.projector import on
from protean.fields import DateTime, Float, Identifier, Integer, String
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.events import (
    DeliveryConfirmed,
    DeliveryException,
    ShipmentHandedOff,
)
from fulfillment.fulfillment.fulfillment import Fulfillment


@fulfillment.projection
class DeliveryPerformanceView:
    """Carrier delivery performance aggregated by carrier and date."""

    id = Identifier(identifier=True)
    carrier = String(required=True)
    date = String(required=True)  # ISO date string YYYY-MM-DD
    total_shipments = Integer(default=0)
    delivered_count = Integer(default=0)
    exception_count = Integer(default=0)
    total_delivery_hours = Float(default=0.0)
    updated_at = DateTime()


def _date_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d") if dt else ""


@fulfillment.projector(projector_for=DeliveryPerformanceView, aggregates=[Fulfillment])
class DeliveryPerformanceProjector:
    @on(ShipmentHandedOff)
    def on_shipment_handed_off(self, event):
        date_str = _date_key(event.shipped_at)
        carrier = event.carrier
        record_id = f"{carrier}-{date_str}"

        repo = current_domain.repository_for(DeliveryPerformanceView)
        try:
            view = repo.get(record_id)
            view.total_shipments = (view.total_shipments or 0) + 1
            view.updated_at = event.shipped_at
        except Exception:
            view = DeliveryPerformanceView(
                id=record_id,
                carrier=carrier,
                date=date_str,
                total_shipments=1,
                delivered_count=0,
                exception_count=0,
                total_delivery_hours=0.0,
                updated_at=event.shipped_at,
            )
        repo.add(view)

    @on(DeliveryConfirmed)
    def on_delivery_confirmed(self, event):
        date_str = _date_key(event.delivered_at)
        # We try all carriers for this date — in practice we'd key by fulfillment_id
        repo = current_domain.repository_for(DeliveryPerformanceView)
        results = repo._dao.query.filter(date=date_str).all()
        if results and results.items:
            view = results.first
            view.delivered_count = (view.delivered_count or 0) + 1
            view.updated_at = event.delivered_at
            repo.add(view)

    @on(DeliveryException)
    def on_delivery_exception(self, event):
        date_str = _date_key(event.occurred_at)
        repo = current_domain.repository_for(DeliveryPerformanceView)
        results = repo._dao.query.filter(date=date_str).all()
        if results and results.items:
            view = results.first
            view.exception_count = (view.exception_count or 0) + 1
            view.updated_at = event.occurred_at
            repo.add(view)
