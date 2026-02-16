"""Customer lookup — find a customer by email."""

from protean.core.projector import on
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from identity.customer.customer import Customer
from identity.customer.events import CustomerRegistered
from identity.domain import identity


@identity.projection
class CustomerLookup:
    email: Identifier(identifier=True, required=True)
    customer_id: String(required=True)


@identity.projector(projector_for=CustomerLookup, aggregates=[Customer])
class CustomerLookupProjector:
    @on(CustomerRegistered)
    def on_customer_registered(self, event):
        current_domain.repository_for(CustomerLookup).add(
            CustomerLookup(
                email=event.email,
                customer_id=event.customer_id,
            )
        )
