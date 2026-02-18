"""Customer registration — command and handler."""

from datetime import date

from protean import handle
from protean.fields import String
from protean.utils.globals import current_domain

from identity.customer.customer import Customer
from identity.domain import identity


@identity.command(part_of="Customer")
class RegisterCustomer:
    """Create a new customer account with profile information."""

    external_id: String(required=True, max_length=255)
    email: String(required=True, max_length=254)
    first_name: String(required=True, max_length=100)
    last_name: String(required=True, max_length=100)
    phone: String(max_length=20)
    date_of_birth: String(max_length=10)


@identity.command_handler(part_of=Customer)
class RegisterCustomerHandler:
    @handle(RegisterCustomer)
    def register_customer(self, command):
        dob = None
        if command.date_of_birth:
            dob = date.fromisoformat(command.date_of_birth)

        customer = Customer.register(
            external_id=command.external_id,
            email=command.email,
            first_name=command.first_name,
            last_name=command.last_name,
            phone=command.phone,
            date_of_birth=dob,
        )
        current_domain.repository_for(Customer).add(customer)
        return str(customer.id)
