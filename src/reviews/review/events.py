"""Domain events for the Review aggregate.

All events are versioned, immutable facts representing state changes.
Events are used for:
- Updating projections via projectors
- Cross-domain communication via Redis Streams
"""

from datetime import datetime

from protean.fields import DateTime, Identifier, Integer, List, String, Text

from reviews.domain import reviews


@reviews.event(part_of="Review")
class ReviewSubmitted:
    """A customer submitted a new product review."""

    review_id: str = Identifier(required=True)
    product_id: str = Identifier(required=True)
    variant_id: str | None = Identifier()
    customer_id: str = Identifier(required=True)
    order_id: str | None = Identifier()
    rating: int = Integer(required=True)
    title: str = String(required=True)
    body: str = Text(required=True)
    pros: list[str] = List(String())
    cons: list[str] = List(String())
    verified_purchase: str = String(required=True)  # "True"/"False"
    image_count: int = Integer(default=0)
    submitted_at: datetime = DateTime(required=True)


@reviews.event(part_of="Review")
class ReviewEdited:
    """A customer edited their review content."""

    review_id: str = Identifier(required=True)
    title: str | None = String()
    body: str | None = Text()
    rating: int | None = Integer()
    edited_at: datetime = DateTime(required=True)


@reviews.event(part_of="Review", published=True)
class ReviewApproved:
    """A moderator approved the review for publication."""

    review_id: str = Identifier(required=True)
    product_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    rating: int = Integer(required=True)
    moderator_id: str = Identifier(required=True)
    approved_at: datetime = DateTime(required=True)


@reviews.event(part_of="Review", published=True)
class ReviewRejected:
    """A moderator rejected the review."""

    review_id: str = Identifier(required=True)
    product_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    moderator_id: str = Identifier(required=True)
    reason: str = String(required=True)
    rejected_at: datetime = DateTime(required=True)


@reviews.event(part_of="Review")
class HelpfulVoteRecorded:
    """A customer voted on whether a review was helpful."""

    review_id: str = Identifier(required=True)
    voter_id: str = Identifier(required=True)
    vote_type: str = String(required=True)
    helpful_count: int = Integer(required=True)
    unhelpful_count: int = Integer(required=True)
    voted_at: datetime = DateTime(required=True)


@reviews.event(part_of="Review")
class ReviewReported:
    """A customer reported a review for moderation."""

    review_id: str = Identifier(required=True)
    reporter_id: str = Identifier(required=True)
    reason: str = String(required=True)
    detail: str | None = String()
    report_count: int = Integer(required=True)
    reported_at: datetime = DateTime(required=True)


@reviews.event(part_of="Review")
class ReviewRemoved:
    """A published review was removed."""

    review_id: str = Identifier(required=True)
    product_id: str = Identifier(required=True)
    customer_id: str = Identifier(required=True)
    rating: int = Integer(required=True)
    removed_by: str = String(required=True)
    reason: str = String(required=True)
    removed_at: datetime = DateTime(required=True)


@reviews.event(part_of="Review")
class SellerReplyAdded:
    """A seller added a reply to a review."""

    review_id: str = Identifier(required=True)
    seller_id: str = Identifier(required=True)
    body: str = Text(required=True)
    replied_at: datetime = DateTime(required=True)
