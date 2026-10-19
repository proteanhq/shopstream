"""Domain events for the Customer aggregate."""

from datetime import datetime

from protean.fields import Boolean, DateTime, Identifier, String

from identity.domain import identity


@identity.event(part_of="Customer", published=True)
class CustomerRegistered:
    """A new customer account was created on the platform."""

    customer_id: str = Identifier(required=True)
    external_id: str = String(required=True)
    email: str = String(required=True)
    first_name: str = String(required=True)
    last_name: str = String(required=True)
    registered_at: datetime = DateTime(required=True)


@identity.event(part_of="Customer")
class ProfileUpdated:
    """A customer's personal profile information was changed."""

    customer_id: str = Identifier(required=True)
    first_name: str = String(required=True)
    last_name: str = String(required=True)
    phone: str | None = String()
    date_of_birth: str | None = String(max_length=10)  # ISO date format YYYY-MM-DD


@identity.event(part_of="Customer")
class AddressAdded:
    """A new address was added to a customer's address book."""

    customer_id: str = Identifier(required=True)
    address_id: str = Identifier(required=True)
    label: str = String(required=True)
    street: str = String(required=True)
    city: str = String(required=True)
    state: str | None = String()
    postal_code: str = String(required=True)
    country: str = String(required=True)
    is_default: bool = Boolean(required=True)


@identity.event(part_of="Customer")
class AddressUpdated:
    """An existing address in a customer's address book was modified."""

    customer_id: str = Identifier(required=True)
    address_id: str = Identifier(required=True)
    label: str | None = String()
    street: str | None = String()
    city: str | None = String()
    state: str | None = String()
    postal_code: str | None = String()
    country: str | None = String()


@identity.event(part_of="Customer")
class AddressRemoved:
    """An address was removed from a customer's address book."""

    customer_id: str = Identifier(required=True)
    address_id: str = Identifier(required=True)


@identity.event(part_of="Customer")
class DefaultAddressChanged:
    """A different address was designated as the customer's default."""

    customer_id: str = Identifier(required=True)
    address_id: str = Identifier(required=True)
    previous_default_address_id: str | None = Identifier()


@identity.event(part_of="Customer", published=True)
class AccountSuspended:
    """A customer account was suspended, blocking further activity."""

    customer_id: str = Identifier(required=True)
    reason: str = String(required=True)
    suspended_at: datetime = DateTime(required=True)


@identity.event(part_of="Customer", published=True)
class AccountReactivated:
    """A previously suspended customer account was restored to active status."""

    customer_id: str = Identifier(required=True)
    reactivated_at: datetime = DateTime(required=True)


@identity.event(part_of="Customer")
class AccountClosed:
    """A customer account was permanently closed."""

    customer_id: str = Identifier(required=True)
    closed_at: datetime = DateTime(required=True)


@identity.event(part_of="Customer")
class TierUpgraded:
    """A customer was promoted to a higher loyalty tier."""

    customer_id: str = Identifier(required=True)
    previous_tier: str = String(required=True)
    new_tier: str = String(required=True)
    upgraded_at: datetime = DateTime(required=True)
