"""Customer profile management — command and handler."""

from datetime import date

from protean import handle
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from identity.customer.customer import Customer
from identity.domain import identity


@identity.command(part_of="Customer")
class UpdateProfile:
    customer_id: Identifier(required=True)
    first_name: String(max_length=100)
    last_name: String(max_length=100)
    phone: String(max_length=20)
    date_of_birth: String(max_length=10)


@identity.command_handler(part_of=Customer)
class ManageProfileHandler:
    @handle(UpdateProfile)
    def update_profile(self, command):
        kwargs = {}
        if command.first_name is not None:
            kwargs["first_name"] = command.first_name
        if command.last_name is not None:
            kwargs["last_name"] = command.last_name
        if command.phone is not None:
            kwargs["phone"] = command.phone
        if command.date_of_birth is not None:
            kwargs["date_of_birth"] = date.fromisoformat(command.date_of_birth)

        repo = current_domain.repository_for(Customer)
        customer = repo.get(command.customer_id)
        customer.update_profile(**kwargs)
        repo.add(customer)
