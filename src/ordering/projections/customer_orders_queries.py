"""Queries for the CustomerOrders projection."""

from protean import read
from protean.fields import Identifier, Integer, String
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.projections.customer_orders import CustomerOrders


@ordering.query(part_of=CustomerOrders)
class ListCustomerOrders:
    customer_id = Identifier(required=True)
    status = String()
    page = Integer(default=1)
    page_size = Integer(default=20)


@ordering.query_handler(part_of=CustomerOrders)
class CustomerOrdersQueryHandler:
    @read(ListCustomerOrders)
    def list_customer_orders(self, query):
        qs = current_domain.view_for(CustomerOrders).query.filter(customer_id=query.customer_id)
        if query.status:
            qs = qs.filter(status=query.status)
        offset = (query.page - 1) * query.page_size
        return qs.offset(offset).limit(query.page_size).all()
