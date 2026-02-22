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
