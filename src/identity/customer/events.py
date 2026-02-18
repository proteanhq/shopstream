"""Domain events for the Customer aggregate."""

from protean.fields import DateTime, Identifier, String

from identity.domain import identity


@identity.event(part_of="Customer")
class CustomerRegistered:
    """A new customer account was created on the platform."""

    __version__ = "v1"

    customer_id: Identifier(required=True)
    external_id: String(required=True)
    email: String(required=True)
    first_name: String(required=True)
    last_name: String(required=True)
    registered_at: DateTime(required=True)


@identity.event(part_of="Customer")
class ProfileUpdated:
    """A customer's personal profile information was changed."""

    __version__ = "v1"

    customer_id: Identifier(required=True)
    first_name: String(required=True)
    last_name: String(required=True)
    phone: String()
    date_of_birth: String()


@identity.event(part_of="Customer")
class AddressAdded:
    """A new address was added to a customer's address book."""

    __version__ = "v1"

    customer_id: Identifier(required=True)
    address_id: Identifier(required=True)
    label: String(required=True)
    street: String(required=True)
    city: String(required=True)
    state: String()
    postal_code: String(required=True)
    country: String(required=True)
    is_default: String(required=True)


@identity.event(part_of="Customer")
class AddressUpdated:
    """An existing address in a customer's address book was modified."""

    __version__ = "v1"

    customer_id: Identifier(required=True)
    address_id: Identifier(required=True)
    label: String()
    street: String()
    city: String()
    state: String()
    postal_code: String()
    country: String()


@identity.event(part_of="Customer")
class AddressRemoved:
    """An address was removed from a customer's address book."""

    __version__ = "v1"

    customer_id: Identifier(required=True)
    address_id: Identifier(required=True)


@identity.event(part_of="Customer")
class DefaultAddressChanged:
    """A different address was designated as the customer's default."""

    __version__ = "v1"

    customer_id: Identifier(required=True)
    address_id: Identifier(required=True)
    previous_default_address_id: Identifier()


@identity.event(part_of="Customer")
class AccountSuspended:
    """A customer account was suspended, blocking further activity."""

    __version__ = "v1"

    customer_id: Identifier(required=True)
    reason: String(required=True)
    suspended_at: DateTime(required=True)


@identity.event(part_of="Customer")
class AccountReactivated:
    """A previously suspended customer account was restored to active status."""

    __version__ = "v1"

    customer_id: Identifier(required=True)
    reactivated_at: DateTime(required=True)


@identity.event(part_of="Customer")
class AccountClosed:
    """A customer account was permanently closed."""

    __version__ = "v1"

    customer_id: Identifier(required=True)
    closed_at: DateTime(required=True)


@identity.event(part_of="Customer")
class TierUpgraded:
    """A customer was promoted to a higher loyalty tier."""

    __version__ = "v1"

    customer_id: Identifier(required=True)
    previous_tier: String(required=True)
    new_tier: String(required=True)
    upgraded_at: DateTime(required=True)
