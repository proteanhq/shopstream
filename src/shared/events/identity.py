"""Cross-domain event contracts for Identity domain events.

These classes define the event shape for consumption by other domains
(e.g., the Notifications domain to send welcome emails). They are
registered as external events via domain.register_external_event()
with matching __type__ strings so Protean's stream deserialization
works correctly.

The source-of-truth events are in src/identity/customer/events.py.
"""

from protean.core.event import BaseEvent
from protean.fields import DateTime, Identifier, String


class CustomerRegistered(BaseEvent):
    """A new customer account was created on the platform."""

    customer_id = Identifier(required=True)
    external_id = String(required=True)
    email = String(required=True)
    first_name = String(required=True)
    last_name = String(required=True)
    registered_at = DateTime(required=True)


class AccountSuspended(BaseEvent):
    """A customer account was suspended, blocking further activity."""

    customer_id = Identifier(required=True)
    reason = String(required=True)
    suspended_at = DateTime(required=True)


class AccountReactivated(BaseEvent):
    """A previously suspended customer account was restored to active status."""

    customer_id = Identifier(required=True)
    reactivated_at = DateTime(required=True)


class ProfileUpdated(BaseEvent):
    """A customer's personal profile information was changed."""

    customer_id = Identifier(required=True)
    first_name = String(required=True)
    last_name = String(required=True)
    phone = String()
    date_of_birth = String()


class AddressAdded(BaseEvent):
    """A new address was added to a customer's address book."""

    customer_id = Identifier(required=True)
    address_id = Identifier(required=True)
    label = String(required=True)
    street = String(required=True)
    city = String(required=True)
    state = String()
    postal_code = String(required=True)
    country = String(required=True)
    is_default = String(required=True)


class AddressUpdated(BaseEvent):
    """An existing address in a customer's address book was modified."""

    customer_id = Identifier(required=True)
    address_id = Identifier(required=True)
    label = String()
    street = String()
    city = String()
    state = String()
    postal_code = String()
    country = String()


class AddressRemoved(BaseEvent):
    """An address was removed from a customer's address book."""

    customer_id = Identifier(required=True)
    address_id = Identifier(required=True)


class DefaultAddressChanged(BaseEvent):
    """A different address was designated as the customer's default."""

    customer_id = Identifier(required=True)
    address_id = Identifier(required=True)
    previous_default_address_id = Identifier()


class AccountClosed(BaseEvent):
    """A customer account was permanently closed."""

    customer_id = Identifier(required=True)
    closed_at = DateTime(required=True)


class TierUpgraded(BaseEvent):
    """A customer was promoted to a higher loyalty tier."""

    customer_id = Identifier(required=True)
    previous_tier = String(required=True)
    new_tier = String(required=True)
    upgraded_at = DateTime(required=True)
