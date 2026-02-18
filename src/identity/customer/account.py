"""Customer account lifecycle — commands and handler."""

from protean import handle
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from identity.customer.customer import Customer
from identity.domain import identity


@identity.command(part_of="Customer")
class SuspendAccount:
    """Temporarily suspend a customer account, blocking further activity."""

    customer_id: Identifier(required=True)
    reason: String(required=True, max_length=500)


@identity.command(part_of="Customer")
class ReactivateAccount:
    """Restore a suspended customer account to active status."""

    customer_id: Identifier(required=True)


@identity.command(part_of="Customer")
class CloseAccount:
    """Permanently close a customer account."""

    customer_id: Identifier(required=True)


@identity.command_handler(part_of=Customer)
class ManageAccountHandler:
    @handle(SuspendAccount)
    def suspend_account(self, command):
        repo = current_domain.repository_for(Customer)
        customer = repo.get(command.customer_id)
        customer.suspend(reason=command.reason)
        repo.add(customer)

    @handle(ReactivateAccount)
    def reactivate_account(self, command):
        repo = current_domain.repository_for(Customer)
        customer = repo.get(command.customer_id)
        customer.reactivate()
        repo.add(customer)

    @handle(CloseAccount)
    def close_account(self, command):
        repo = current_domain.repository_for(Customer)
        customer = repo.get(command.customer_id)
        customer.close()
        repo.add(customer)
