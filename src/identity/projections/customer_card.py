"""Customer card — a snapshot view of a customer's key details."""

from datetime import datetime

from protean.core.projector import on
from protean.fields import DateTime, Identifier, String
from protean.utils.globals import current_domain

from identity.customer.customer import Customer
from identity.customer.events import (
    AccountClosed,
    AccountReactivated,
    AccountSuspended,
    CustomerRegistered,
    ProfileUpdated,
    TierUpgraded,
)
from identity.domain import identity


@identity.projection
class CustomerCard:
    customer_id: str = Identifier(identifier=True, required=True)
    external_id: str = String(required=True)
    email: str = String(required=True)
    first_name: str = String(required=True)
    last_name: str = String(required=True)
    phone: str | None = String()
    status: str = String(required=True)
    tier: str = String(required=True)
    registered_at: datetime | None = DateTime()


@identity.projector(projector_for=CustomerCard, aggregates=[Customer])
class CustomerCardProjector:
    @on(CustomerRegistered)
    def on_customer_registered(self, event):
        current_domain.repository_for(CustomerCard).add(
            CustomerCard(
                customer_id=event.customer_id,
                external_id=event.external_id,
                email=event.email,
                first_name=event.first_name,
                last_name=event.last_name,
                status="Active",
                tier="Standard",
                registered_at=event.registered_at,
            )
        )

    @on(ProfileUpdated)
    def on_profile_updated(self, event):
        repo = current_domain.repository_for(CustomerCard)
        card = repo.get(event.customer_id)
        card.first_name = event.first_name
        card.last_name = event.last_name
        if event.phone:
            card.phone = event.phone
        repo.add(card)

    @on(AccountSuspended)
    def on_account_suspended(self, event):
        repo = current_domain.repository_for(CustomerCard)
        card = repo.get(event.customer_id)
        card.status = "Suspended"
        repo.add(card)

    @on(AccountReactivated)
    def on_account_reactivated(self, event):
        repo = current_domain.repository_for(CustomerCard)
        card = repo.get(event.customer_id)
        card.status = "Active"
        repo.add(card)

    @on(AccountClosed)
    def on_account_closed(self, event):
        repo = current_domain.repository_for(CustomerCard)
        card = repo.get(event.customer_id)
        card.status = "Closed"
        repo.add(card)

    @on(TierUpgraded)
    def on_tier_upgraded(self, event):
        repo = current_domain.repository_for(CustomerCard)
        card = repo.get(event.customer_id)
        card.tier = event.new_tier
        repo.add(card)
