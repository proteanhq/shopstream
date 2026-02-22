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

    __version__ = "v1"

    customer_id = Identifier(required=True)
    external_id = String(required=True)
    email = String(required=True)
    first_name = String(required=True)
    last_name = String(required=True)
    registered_at = DateTime(required=True)


class AccountSuspended(BaseEvent):
    """A customer account was suspended, blocking further activity."""

    __version__ = "v1"

    customer_id = Identifier(required=True)
    reason = String(required=True)
    suspended_at = DateTime(required=True)


class AccountReactivated(BaseEvent):
    """A previously suspended customer account was restored to active status."""

    __version__ = "v1"

    customer_id = Identifier(required=True)
    reactivated_at = DateTime(required=True)
