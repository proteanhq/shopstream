"""Queries for the CustomerCard projection."""

from protean import read
from protean.fields import Identifier
from protean.utils.globals import current_domain

from identity.domain import identity
from identity.projections.customer_card import CustomerCard


@identity.query(part_of=CustomerCard)
class GetCustomerCard:
    customer_id = Identifier(required=True)


@identity.query_handler(part_of=CustomerCard)
class CustomerCardQueryHandler:
    @read(GetCustomerCard)
    def get_customer_card(self, query):
        return current_domain.view_for(CustomerCard).get(query.customer_id)
