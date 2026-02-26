"""Queries for the OrderDetail projection."""

from protean import read
from protean.fields import Identifier
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.projections.order_detail import OrderDetail


@ordering.query(part_of=OrderDetail)
class GetOrderDetail:
    order_id = Identifier(required=True)


@ordering.query_handler(part_of=OrderDetail)
class OrderDetailQueryHandler:
    @read(GetOrderDetail)
    def get_order_detail(self, query):
        return current_domain.view_for(OrderDetail).get(query.order_id)
