"""Cross-domain event contracts for Reviews domain events.

These classes define the event shape for consumption by other domains
(e.g., the Catalogue domain to update product average ratings, or the
Notifications domain to thank reviewers). They are registered as external
events via domain.register_external_event() with matching __type__ strings
so Protean's stream deserialization works correctly.

The source-of-truth events are in src/reviews/review/events.py.
"""

from protean.core.event import BaseEvent
from protean.fields import DateTime, Identifier, Integer, String


class ReviewApproved(BaseEvent):
    """A review was approved for publication."""

    __version__ = "v1"

    review_id = Identifier(required=True)
    product_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    rating = Integer(required=True)
    moderator_id = Identifier(required=True)
    approved_at = DateTime(required=True)


class ReviewRemoved(BaseEvent):
    """A published review was removed."""

    __version__ = "v1"

    review_id = Identifier(required=True)
    product_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    rating = Integer(required=True)
    removed_by = String(required=True)
    reason = String(required=True)
    removed_at = DateTime(required=True)
