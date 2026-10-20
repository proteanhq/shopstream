"""CustomerReviews — a customer's review history across all products."""

from datetime import datetime

from protean import Index
from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String
from protean.utils.globals import current_domain

from reviews.domain import reviews
from reviews.review.events import (
    ReviewApproved,
    ReviewEdited,
    ReviewRejected,
    ReviewRemoved,
    ReviewSubmitted,
)
from reviews.review.review import Review


# Read path: list a customer's own reviews (filter by customer_id).
@reviews.projection(indexes=[Index("customer_id")])
class CustomerReviews:
    review_id: str = Identifier(identifier=True, required=True)
    customer_id: str = Identifier(required=True)
    product_id: str = Identifier(required=True)
    rating: int = Integer(required=True)
    title: str = String(required=True)
    status: str = String(required=True)
    created_at: datetime | None = DateTime()
    updated_at: datetime | None = DateTime()


@reviews.projector(projector_for=CustomerReviews, aggregates=[Review])
class CustomerReviewsProjector:
    @on(ReviewSubmitted)
    def on_review_submitted(self, event: ReviewSubmitted) -> None:
        current_domain.repository_for(CustomerReviews).add(
            CustomerReviews(
                review_id=event.review_id,
                customer_id=event.customer_id,
                product_id=event.product_id,
                rating=event.rating,
                title=event.title,
                status="Pending",
                created_at=event.submitted_at,
                updated_at=event.submitted_at,
            )
        )

    def _update_status(self, review_id: str, status: str, updated_at: datetime) -> None:
        repo = current_domain.repository_for(CustomerReviews)
        cr = repo.get_or_none(review_id)
        if cr is None:
            return
        cr.status = status
        cr.updated_at = updated_at
        repo.add(cr)

    @on(ReviewEdited)
    def on_review_edited(self, event: ReviewEdited) -> None:
        repo = current_domain.repository_for(CustomerReviews)
        cr = repo.get_or_none(event.review_id)
        if cr is None:
            return
        if event.title:
            cr.title = event.title
        if event.rating:
            cr.rating = event.rating
        cr.status = "Pending"  # Re-submitted for moderation
        cr.updated_at = event.edited_at
        repo.add(cr)

    @on(ReviewApproved)
    def on_review_approved(self, event: ReviewApproved) -> None:
        self._update_status(event.review_id, "Published", event.approved_at)

    @on(ReviewRejected)
    def on_review_rejected(self, event: ReviewRejected) -> None:
        self._update_status(event.review_id, "Rejected", event.rejected_at)

    @on(ReviewRemoved)
    def on_review_removed(self, event: ReviewRemoved) -> None:
        self._update_status(event.review_id, "Removed", event.removed_at)
