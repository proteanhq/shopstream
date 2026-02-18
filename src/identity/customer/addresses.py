"""Customer address management — commands and handler."""

from protean import handle
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from identity.customer.customer import Customer, GeoCoordinates
from identity.domain import identity


@identity.command(part_of="Customer")
class AddAddress:
    """Add a new address to a customer's address book."""

    customer_id: Identifier(required=True)
    label: String(max_length=20)
    street: String(required=True, max_length=255)
    city: String(required=True, max_length=100)
    state: String(max_length=100)
    postal_code: String(required=True, max_length=20)
    country: String(required=True, max_length=100)
    geo_lat: String()
    geo_lng: String()


@identity.command(part_of="Customer")
class UpdateAddress:
    """Modify fields of an existing address."""

    customer_id: Identifier(required=True)
    address_id: Identifier(required=True)
    label: String(max_length=20)
    street: String(max_length=255)
    city: String(max_length=100)
    state: String(max_length=100)
    postal_code: String(max_length=20)
    country: String(max_length=100)


@identity.command(part_of="Customer")
class RemoveAddress:
    """Remove an address from a customer's address book."""

    customer_id: Identifier(required=True)
    address_id: Identifier(required=True)


@identity.command(part_of="Customer")
class SetDefaultAddress:
    """Designate an existing address as the customer's default."""

    customer_id: Identifier(required=True)
    address_id: Identifier(required=True)


@identity.command_handler(part_of=Customer)
class ManageAddressesHandler:
    @handle(AddAddress)
    def add_address(self, command):
        repo = current_domain.repository_for(Customer)
        customer = repo.get(command.customer_id)

        geo = None
        if command.geo_lat and command.geo_lng:
            geo = GeoCoordinates(
                latitude=float(command.geo_lat),
                longitude=float(command.geo_lng),
            )

        kwargs = {
            "street": command.street,
            "city": command.city,
            "postal_code": command.postal_code,
            "country": command.country,
        }
        if command.label:
            kwargs["label"] = command.label
        if command.state:
            kwargs["state"] = command.state
        if geo:
            kwargs["geo_coordinates"] = geo

        customer.add_address(**kwargs)
        repo.add(customer)

    @handle(UpdateAddress)
    def update_address(self, command):
        repo = current_domain.repository_for(Customer)
        customer = repo.get(command.customer_id)

        updates = {}
        for field in ("label", "street", "city", "state", "postal_code", "country"):
            value = getattr(command, field, None)
            if value is not None:
                updates[field] = value

        customer.update_address(command.address_id, **updates)
        repo.add(customer)

    @handle(RemoveAddress)
    def remove_address(self, command):
        repo = current_domain.repository_for(Customer)
        customer = repo.get(command.customer_id)
        customer.remove_address(command.address_id)
        repo.add(customer)

    @handle(SetDefaultAddress)
    def set_default_address(self, command):
        repo = current_domain.repository_for(Customer)
        customer = repo.get(command.customer_id)
        customer.set_default_address(command.address_id)
        repo.add(customer)
