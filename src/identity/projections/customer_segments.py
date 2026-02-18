"""Customer segments — how are customers distributed by tier?"""

from protean.core.projector import on
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from identity.customer.customer import Customer
from identity.customer.events import CustomerRegistered, ProfileUpdated, TierUpgraded
from identity.domain import identity


@identity.projection
class CustomerSegments:
    customer_id: Identifier(identifier=True, required=True)
    email: String(required=True)
    first_name: String(required=True)
    last_name: String(required=True)
    tier: String(required=True)


@identity.projector(projector_for=CustomerSegments, aggregates=[Customer])
class CustomerSegmentsProjector:
    @on(CustomerRegistered)
    def on_customer_registered(self, event):
        current_domain.repository_for(CustomerSegments).add(
            CustomerSegments(
                customer_id=event.customer_id,
                email=event.email,
                first_name=event.first_name,
                last_name=event.last_name,
                tier="Standard",
            )
        )

    @on(ProfileUpdated)
    def on_profile_updated(self, event):
        repo = current_domain.repository_for(CustomerSegments)
        record = repo.get(event.customer_id)
        record.first_name = event.first_name
        record.last_name = event.last_name
        repo.add(record)

    @on(TierUpgraded)
    def on_tier_upgraded(self, event):
        repo = current_domain.repository_for(CustomerSegments)
        record = repo.get(event.customer_id)
        record.tier = event.new_tier
        repo.add(record)
