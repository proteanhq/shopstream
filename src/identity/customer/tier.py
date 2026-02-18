"""Customer tier management — command and handler."""

from protean import handle
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from identity.customer.customer import Customer
from identity.domain import identity


@identity.command(part_of="Customer")
class UpgradeTier:
    """Promote a customer to a higher loyalty tier (upgrades only, no downgrades)."""

    customer_id: Identifier(required=True)
    new_tier: String(required=True, max_length=20)


@identity.command_handler(part_of=Customer)
class ManageTierHandler:
    @handle(UpgradeTier)
    def upgrade_tier(self, command):
        repo = current_domain.repository_for(Customer)
        customer = repo.get(command.customer_id)
        customer.upgrade_tier(new_tier=command.new_tier)
        repo.add(customer)
