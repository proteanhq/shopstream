"""Cross-domain event contracts for Reviews domain events.

These classes define the event shape for consumption by other domains
(e.g., the Catalogue domain to update product average ratings, or the
Notifications domain to thank reviewers). They are registered as external
events via domain.register_external_event() with matching __type__ strings
so Protean's stream deserialization works correctly.

The source-of-truth events are in src/reviews/review/events.py.
"""

from protean.core.event import BaseEvent
from protean.fields import DateTime, Identifier, Integer, List, String, Text


class ReviewSubmitted(BaseEvent):
    """A customer submitted a new product review."""

    review_id = Identifier(required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier()
    customer_id = Identifier(required=True)
    order_id = Identifier()
    rating = Integer(required=True)
    title = String(required=True)
    body = Text(required=True)
    pros = List(String())
    cons = List(String())
    verified_purchase = String(required=True)
    image_count = Integer(default=0)
    submitted_at = DateTime(required=True)


class ReviewEdited(BaseEvent):
    """A customer edited their review content."""

    review_id = Identifier(required=True)
    title = String()
    body = Text()
    rating = Integer()
    edited_at = DateTime(required=True)


class ReviewApproved(BaseEvent):
    """A review was approved for publication."""

    review_id = Identifier(required=True)
    product_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    rating = Integer(required=True)
    moderator_id = Identifier(required=True)
    approved_at = DateTime(required=True)


class ReviewRemoved(BaseEvent):
    """A published review was removed."""

    review_id = Identifier(required=True)
    product_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    rating = Integer(required=True)
    removed_by = String(required=True)
    reason = String(required=True)
    removed_at = DateTime(required=True)


class ReviewRejected(BaseEvent):
    """A review was rejected by moderation.

    Consumed by the Notifications domain to inform the customer.
    """

    review_id = Identifier(required=True)
    product_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    moderator_id = Identifier(required=True)
    reason = String(required=True)
    rejected_at = DateTime(required=True)


class HelpfulVoteRecorded(BaseEvent):
    """A customer voted on whether a review was helpful."""

    review_id = Identifier(required=True)
    voter_id = Identifier(required=True)
    vote_type = String(required=True)
    helpful_count = Integer(required=True)
    unhelpful_count = Integer(required=True)
    voted_at = DateTime(required=True)


class ReviewReported(BaseEvent):
    """A customer reported a review for moderation."""

    review_id = Identifier(required=True)
    reporter_id = Identifier(required=True)
    reason = String(required=True)
    detail = String()
    report_count = Integer(required=True)
    reported_at = DateTime(required=True)


class SellerReplyAdded(BaseEvent):
    """A seller added a reply to a review."""

    review_id = Identifier(required=True)
    seller_id = Identifier(required=True)
    body = Text(required=True)
    replied_at = DateTime(required=True)
