"""Domain events for the Review aggregate.

All events are versioned, immutable facts representing state changes.
Events are used for:
- Updating projections via projectors
- Cross-domain communication via Redis Streams
"""

from protean.fields import DateTime, Identifier, Integer, String, Text

from reviews.domain import reviews


@reviews.event(part_of="Review")
class ReviewSubmitted:
    """A customer submitted a new product review."""

    __version__ = "v1"

    review_id = Identifier(required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier()
    customer_id = Identifier(required=True)
    order_id = Identifier()
    rating = Integer(required=True)
    title = String(required=True)
    body = Text(required=True)
    pros = Text()
    cons = Text()
    verified_purchase = String(required=True)  # "True"/"False"
    image_count = Integer(default=0)
    submitted_at = DateTime(required=True)


@reviews.event(part_of="Review")
class ReviewEdited:
    """A customer edited their review content."""

    __version__ = "v1"

    review_id = Identifier(required=True)
    title = String()
    body = Text()
    rating = Integer()
    edited_at = DateTime(required=True)


@reviews.event(part_of="Review")
class ReviewApproved:
    """A moderator approved the review for publication."""

    __version__ = "v1"

    review_id = Identifier(required=True)
    product_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    rating = Integer(required=True)
    moderator_id = Identifier(required=True)
    approved_at = DateTime(required=True)


@reviews.event(part_of="Review")
class ReviewRejected:
    """A moderator rejected the review."""

    __version__ = "v1"

    review_id = Identifier(required=True)
    product_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    moderator_id = Identifier(required=True)
    reason = String(required=True)
    rejected_at = DateTime(required=True)


@reviews.event(part_of="Review")
class HelpfulVoteRecorded:
    """A customer voted on whether a review was helpful."""

    __version__ = "v1"

    review_id = Identifier(required=True)
    voter_id = Identifier(required=True)
    vote_type = String(required=True)
    helpful_count = Integer(required=True)
    unhelpful_count = Integer(required=True)
    voted_at = DateTime(required=True)


@reviews.event(part_of="Review")
class ReviewReported:
    """A customer reported a review for moderation."""

    __version__ = "v1"

    review_id = Identifier(required=True)
    reporter_id = Identifier(required=True)
    reason = String(required=True)
    detail = String()
    report_count = Integer(required=True)
    reported_at = DateTime(required=True)


@reviews.event(part_of="Review")
class ReviewRemoved:
    """A published review was removed."""

    __version__ = "v1"

    review_id = Identifier(required=True)
    product_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    rating = Integer(required=True)
    removed_by = String(required=True)
    reason = String(required=True)
    removed_at = DateTime(required=True)


@reviews.event(part_of="Review")
class SellerReplyAdded:
    """A seller added a reply to a review."""

    __version__ = "v1"

    review_id = Identifier(required=True)
    seller_id = Identifier(required=True)
    body = Text(required=True)
    replied_at = DateTime(required=True)
