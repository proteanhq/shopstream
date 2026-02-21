"""CustomerReviews — a customer's review history across all products."""

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


@reviews.projection
class CustomerReviews:
    review_id = Identifier(identifier=True, required=True)
    customer_id = Identifier(required=True)
    product_id = Identifier(required=True)
    rating = Integer(required=True)
    title = String(required=True)
    status = String(required=True)
    created_at = DateTime()
    updated_at = DateTime()


@reviews.projector(projector_for=CustomerReviews, aggregates=[Review])
class CustomerReviewsProjector:
    @on(ReviewSubmitted)
    def on_review_submitted(self, event):
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

    def _update_status(self, review_id, status, updated_at):
        repo = current_domain.repository_for(CustomerReviews)
        try:
            cr = repo.get(review_id)
        except Exception:
            return
        cr.status = status
        cr.updated_at = updated_at
        repo.add(cr)

    @on(ReviewEdited)
    def on_review_edited(self, event):
        repo = current_domain.repository_for(CustomerReviews)
        try:
            cr = repo.get(event.review_id)
        except Exception:
            return
        if event.title:
            cr.title = event.title
        if event.rating:
            cr.rating = event.rating
        cr.status = "Pending"  # Re-submitted for moderation
        cr.updated_at = event.edited_at
        repo.add(cr)

    @on(ReviewApproved)
    def on_review_approved(self, event):
        self._update_status(event.review_id, "Published", event.approved_at)

    @on(ReviewRejected)
    def on_review_rejected(self, event):
        self._update_status(event.review_id, "Rejected", event.rejected_at)

    @on(ReviewRemoved)
    def on_review_removed(self, event):
        self._update_status(event.review_id, "Removed", event.removed_at)
