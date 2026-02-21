"""Review aggregate (CQRS) — the core of the Reviews & Ratings domain.

The Review aggregate manages the full lifecycle of a customer product review:
submission, moderation, voting, reporting, seller replies, and removal.

CQRS (not event sourced) — reviews are write-once-mostly with simple state
transitions and no temporal query needs.

State Machine (4 states):
    PENDING → PUBLISHED | REJECTED
    REJECTED → PENDING (re-submit after edit)
    PUBLISHED → REMOVED
    REMOVED → (terminal)
"""

import json
from datetime import UTC, datetime
from enum import Enum

from protean import atomic_change, invariant
from protean.exceptions import ValidationError
from protean.fields import (
    Boolean,
    DateTime,
    HasMany,
    Identifier,
    Integer,
    String,
    Text,
    ValueObject,
)

from reviews.domain import reviews
from reviews.review.events import (
    HelpfulVoteRecorded,
    ReviewApproved,
    ReviewEdited,
    ReviewRejected,
    ReviewRemoved,
    ReviewReported,
    ReviewSubmitted,
    SellerReplyAdded,
)

# Sentinel for distinguishing "not provided" from None in partial updates
_UNSET = object()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class ReviewStatus(Enum):
    PENDING = "Pending"
    PUBLISHED = "Published"
    REJECTED = "Rejected"
    REMOVED = "Removed"


class VoteType(Enum):
    HELPFUL = "Helpful"
    UNHELPFUL = "Unhelpful"


class ReportReason(Enum):
    SPAM = "Spam"
    OFFENSIVE = "Offensive"
    IRRELEVANT = "Irrelevant"
    FAKE = "Fake"
    OTHER = "Other"


class ModerationAction(Enum):
    APPROVE = "Approve"
    REJECT = "Reject"


# ---------------------------------------------------------------------------
# State Machine
# ---------------------------------------------------------------------------
_VALID_TRANSITIONS = {
    ReviewStatus.PENDING: {ReviewStatus.PUBLISHED, ReviewStatus.REJECTED},
    ReviewStatus.PUBLISHED: {ReviewStatus.REMOVED},
    ReviewStatus.REJECTED: {ReviewStatus.PENDING},  # Re-submit after edit
    ReviewStatus.REMOVED: set(),  # Terminal state
}


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------
@reviews.value_object(part_of="Review")
class Rating:
    """A star rating from 1 to 5."""

    score = Integer(required=True)

    @invariant.post
    def score_must_be_in_range(self):
        if self.score is not None and (self.score < 1 or self.score > 5):
            raise ValidationError({"score": ["Rating must be between 1 and 5"]})


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
@reviews.entity(part_of="Review")
class ReviewImage:
    """A photo attached to a review."""

    url = String(required=True, max_length=500)
    alt_text = String(max_length=255)
    display_order = Integer(default=0)


@reviews.entity(part_of="Review")
class HelpfulVote:
    """A vote on whether a review was helpful or unhelpful."""

    customer_id = Identifier(required=True)
    vote_type = String(choices=VoteType, required=True)
    voted_at = DateTime(required=True)


@reviews.entity(part_of="Review")
class SellerReply:
    """A reply from the product seller to the review."""

    seller_id = Identifier(required=True)
    body = Text(required=True)
    replied_at = DateTime(required=True)


# ---------------------------------------------------------------------------
# Aggregate Root
# ---------------------------------------------------------------------------
@reviews.aggregate
class Review:
    """A customer's review of a product they purchased.

    The Review aggregate manages the full lifecycle: submission,
    moderation, voting, reporting, seller replies, and removal.
    """

    # Core identifiers
    product_id = Identifier(required=True)
    variant_id = Identifier()
    customer_id = Identifier(required=True)
    order_id = Identifier()

    # Content
    rating = ValueObject(Rating, required=True)
    title = String(required=True, max_length=200)
    body = Text(required=True)
    pros = Text()  # JSON array of strings
    cons = Text()  # JSON array of strings

    # Media
    images = HasMany(ReviewImage)

    # Verification
    verified_purchase = Boolean(default=False)

    # Status
    status = String(choices=ReviewStatus, default=ReviewStatus.PENDING.value)
    moderation_notes = Text()

    # Voting
    votes = HasMany(HelpfulVote)
    helpful_count = Integer(default=0)
    unhelpful_count = Integer(default=0)

    # Reporting
    report_count = Integer(default=0)
    reported_reasons = Text()  # JSON: [{customer_id, reason, detail, reported_at}]

    # Seller engagement
    reply = HasMany(SellerReply)

    # Editing
    is_edited = Boolean(default=False)
    edited_at = DateTime()

    # Timestamps
    created_at = DateTime()
    updated_at = DateTime()

    # -------------------------------------------------------------------
    # Invariants
    # -------------------------------------------------------------------
    @invariant.post
    def images_cannot_exceed_maximum(self):
        if len(self.images) > 5:
            raise ValidationError({"images": ["Cannot attach more than 5 images to a review"]})

    @invariant.post
    def at_most_one_seller_reply(self):
        if len(self.reply) > 1:
            raise ValidationError({"reply": ["A review can have at most one seller reply"]})

    @invariant.post
    def body_minimum_length(self):
        if self.body and len(self.body.strip()) < 20:
            raise ValidationError({"body": ["Review body must be at least 20 characters"]})

    @invariant.post
    def title_must_not_be_empty(self):
        if self.title is not None and len(self.title.strip()) == 0:
            raise ValidationError({"title": ["Review title cannot be empty"]})

    # -------------------------------------------------------------------
    # Factory
    # -------------------------------------------------------------------
    @classmethod
    def submit(
        cls,
        product_id,
        customer_id,
        rating,
        title,
        body,
        variant_id=None,
        order_id=None,
        verified_purchase=False,
        pros=None,
        cons=None,
        images=None,
    ):
        """Submit a new review."""
        now = datetime.now(UTC)

        review = cls(
            product_id=product_id,
            variant_id=variant_id,
            customer_id=customer_id,
            order_id=order_id,
            rating=Rating(score=rating),
            title=title,
            body=body,
            pros=json.dumps(pros) if pros else None,
            cons=json.dumps(cons) if cons else None,
            verified_purchase=verified_purchase,
            status=ReviewStatus.PENDING.value,
            helpful_count=0,
            unhelpful_count=0,
            report_count=0,
            reported_reasons=json.dumps([]),
            is_edited=False,
            created_at=now,
            updated_at=now,
        )

        # Add images if provided
        if images:
            for i, img in enumerate(images):
                review.add_images(
                    ReviewImage(
                        url=img["url"],
                        alt_text=img.get("alt_text", ""),
                        display_order=i,
                    )
                )

        review.raise_(
            ReviewSubmitted(
                review_id=str(review.id),
                product_id=str(product_id),
                variant_id=str(variant_id) if variant_id else None,
                customer_id=str(customer_id),
                order_id=str(order_id) if order_id else None,
                rating=rating,
                title=title,
                body=body,
                pros=json.dumps(pros) if pros else None,
                cons=json.dumps(cons) if cons else None,
                verified_purchase=str(verified_purchase),
                image_count=len(images) if images else 0,
                submitted_at=now,
            )
        )

        return review

    # -------------------------------------------------------------------
    # State transitions
    # -------------------------------------------------------------------
    def _assert_can_transition(self, target_status):
        """Validate state machine transition."""
        current = ReviewStatus(self.status)
        if target_status not in _VALID_TRANSITIONS.get(current, set()):
            raise ValidationError({"status": [f"Cannot transition from {current.value} to {target_status.value}"]})

    # -------------------------------------------------------------------
    # Edit
    # -------------------------------------------------------------------
    def edit(
        self,
        title=_UNSET,
        body=_UNSET,
        rating=_UNSET,
        pros=_UNSET,
        cons=_UNSET,
    ):
        """Edit review content. Only allowed in PENDING or REJECTED status."""
        current = ReviewStatus(self.status)
        if current not in (ReviewStatus.PENDING, ReviewStatus.REJECTED):
            raise ValidationError({"status": ["Reviews can only be edited in Pending or Rejected status"]})

        now = datetime.now(UTC)

        new_title = title if title is not _UNSET else self.title
        new_body = body if body is not _UNSET else self.body
        new_rating = rating if rating is not _UNSET else self.rating.score

        with atomic_change(self):
            if title is not _UNSET:
                self.title = title
            if body is not _UNSET:
                self.body = body
            if rating is not _UNSET:
                self.rating = Rating(score=rating)
            if pros is not _UNSET:
                self.pros = json.dumps(pros) if pros else None
            if cons is not _UNSET:
                self.cons = json.dumps(cons) if cons else None

            self.is_edited = True
            self.edited_at = now
            self.updated_at = now

            # Re-submit rejected reviews back to pending
            if current == ReviewStatus.REJECTED:
                self.status = ReviewStatus.PENDING.value

        self.raise_(
            ReviewEdited(
                review_id=str(self.id),
                title=new_title,
                body=new_body,
                rating=new_rating,
                edited_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Moderation
    # -------------------------------------------------------------------
    def approve(self, moderator_id, notes=None):
        """Approve the review for publication."""
        self._assert_can_transition(ReviewStatus.PUBLISHED)

        now = datetime.now(UTC)
        self.status = ReviewStatus.PUBLISHED.value
        self.moderation_notes = notes
        self.updated_at = now

        self.raise_(
            ReviewApproved(
                review_id=str(self.id),
                product_id=str(self.product_id),
                customer_id=str(self.customer_id),
                rating=self.rating.score,
                moderator_id=str(moderator_id),
                approved_at=now,
            )
        )

    def reject(self, moderator_id, reason):
        """Reject the review."""
        self._assert_can_transition(ReviewStatus.REJECTED)

        now = datetime.now(UTC)
        self.status = ReviewStatus.REJECTED.value
        self.moderation_notes = reason
        self.updated_at = now

        self.raise_(
            ReviewRejected(
                review_id=str(self.id),
                product_id=str(self.product_id),
                customer_id=str(self.customer_id),
                moderator_id=str(moderator_id),
                reason=reason,
                rejected_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Voting
    # -------------------------------------------------------------------
    def vote(self, customer_id, vote_type):
        """Record a helpful/unhelpful vote.

        Cannot vote on own review. Cannot vote twice.
        """
        if str(customer_id) == str(self.customer_id):
            raise ValidationError({"vote": ["Cannot vote on your own review"]})

        # Check for duplicate vote
        existing = next(
            (v for v in self.votes if str(v.customer_id) == str(customer_id)),
            None,
        )
        if existing:
            raise ValidationError({"vote": ["You have already voted on this review"]})

        now = datetime.now(UTC)

        vote = HelpfulVote(
            customer_id=customer_id,
            vote_type=vote_type,
            voted_at=now,
        )
        self.add_votes(vote)

        with atomic_change(self):
            if VoteType(vote_type) == VoteType.HELPFUL:
                self.helpful_count = self.helpful_count + 1
            else:
                self.unhelpful_count = self.unhelpful_count + 1
            self.updated_at = now

        self.raise_(
            HelpfulVoteRecorded(
                review_id=str(self.id),
                voter_id=str(customer_id),
                vote_type=vote_type,
                helpful_count=self.helpful_count,
                unhelpful_count=self.unhelpful_count,
                voted_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Reporting
    # -------------------------------------------------------------------
    def report(self, customer_id, reason, detail=None):
        """Report a review for moderation. Cannot report own review."""
        if str(customer_id) == str(self.customer_id):
            raise ValidationError({"report": ["Cannot report your own review"]})

        now = datetime.now(UTC)

        # Track report in JSON array
        reports = json.loads(self.reported_reasons) if self.reported_reasons else []
        reports.append(
            {
                "customer_id": str(customer_id),
                "reason": reason,
                "detail": detail,
                "reported_at": now.isoformat(),
            }
        )

        self.reported_reasons = json.dumps(reports)
        self.report_count = self.report_count + 1
        self.updated_at = now

        self.raise_(
            ReviewReported(
                review_id=str(self.id),
                reporter_id=str(customer_id),
                reason=reason,
                detail=detail,
                report_count=self.report_count,
                reported_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Removal
    # -------------------------------------------------------------------
    def remove(self, removed_by, reason):
        """Remove a published review."""
        self._assert_can_transition(ReviewStatus.REMOVED)

        now = datetime.now(UTC)
        self.status = ReviewStatus.REMOVED.value
        self.moderation_notes = reason
        self.updated_at = now

        self.raise_(
            ReviewRemoved(
                review_id=str(self.id),
                product_id=str(self.product_id),
                customer_id=str(self.customer_id),
                rating=self.rating.score,
                removed_by=removed_by,
                reason=reason,
                removed_at=now,
            )
        )

    # -------------------------------------------------------------------
    # Seller reply
    # -------------------------------------------------------------------
    def add_seller_reply(self, seller_id, body):
        """Add a reply from the seller. Only one reply allowed, only on published reviews."""
        if ReviewStatus(self.status) != ReviewStatus.PUBLISHED:
            raise ValidationError({"reply": ["Seller can only reply to published reviews"]})

        if self.reply:
            raise ValidationError({"reply": ["A review can have at most one seller reply"]})

        now = datetime.now(UTC)

        reply = SellerReply(
            seller_id=seller_id,
            body=body,
            replied_at=now,
        )
        self.add_reply(reply)
        self.updated_at = now

        self.raise_(
            SellerReplyAdded(
                review_id=str(self.id),
                seller_id=str(seller_id),
                body=body,
                replied_at=now,
            )
        )
