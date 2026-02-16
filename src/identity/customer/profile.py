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
    first_name: String(required=True, max_length=100)
    last_name: String(required=True, max_length=100)
    phone: String(max_length=20)
    date_of_birth: String(max_length=10)


@identity.command_handler(part_of=Customer)
class ManageProfileHandler:
    @handle(UpdateProfile)
    def update_profile(self, command):
        dob = None
        if command.date_of_birth:
            dob = date.fromisoformat(command.date_of_birth)

        repo = current_domain.repository_for(Customer)
        customer = repo.get(command.customer_id)
        customer.update_profile(
            first_name=command.first_name,
            last_name=command.last_name,
            phone=command.phone,
            date_of_birth=dob,
        )
        repo.add(customer)
