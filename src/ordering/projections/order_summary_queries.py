"""Queries for the OrderSummary projection."""

from protean import read
from protean.fields import Identifier
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.projections.order_summary import OrderSummary


@ordering.query(part_of=OrderSummary)
class GetOrderSummary:
    order_id = Identifier(required=True)


@ordering.query_handler(part_of=OrderSummary)
class OrderSummaryQueryHandler:
    @read(GetOrderSummary)
    def get_order_summary(self, query):
        return current_domain.view_for(OrderSummary).get(query.order_id)
