"""Queries for the OrderTimeline projection."""

from protean import read
from protean.fields import Identifier
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.projections.order_timeline import OrderTimeline


@ordering.query(part_of=OrderTimeline)
class GetOrderTimeline:
    order_id = Identifier(required=True)


@ordering.query_handler(part_of=OrderTimeline)
class OrderTimelineQueryHandler:
    @read(GetOrderTimeline)
    def get_order_timeline(self, query):
        return (
            current_domain.view_for(OrderTimeline).query.filter(order_id=query.order_id).order_by("occurred_at").all()
        )
