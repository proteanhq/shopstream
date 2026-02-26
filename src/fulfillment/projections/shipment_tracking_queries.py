"""Queries for the ShipmentTrackingView projection."""

from protean import read
from protean.fields import Identifier
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.projections.shipment_tracking import ShipmentTrackingView


@fulfillment.query(part_of=ShipmentTrackingView)
class GetShipmentTracking:
    order_id = Identifier(required=True)


@fulfillment.query_handler(part_of=ShipmentTrackingView)
class ShipmentTrackingQueryHandler:
    @read(GetShipmentTracking)
    def get_shipment_tracking(self, query):
        results = current_domain.view_for(ShipmentTrackingView).query.filter(order_id=query.order_id).all()
        if results.items:
            return results.first
        return None
