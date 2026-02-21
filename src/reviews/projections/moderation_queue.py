"""ModerationQueue — pending and reported reviews awaiting moderator action."""

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String, Text
from protean.utils.globals import current_domain

from reviews.domain import reviews
from reviews.review.events import (
    ReviewApproved,
    ReviewRejected,
    ReviewRemoved,
    ReviewReported,
    ReviewSubmitted,
)
from reviews.review.review import Review


@reviews.projection
class ModerationQueue:
    review_id = Identifier(identifier=True, required=True)
    product_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    rating = Integer(required=True)
    title = String(required=True)
    body = Text(required=True)
    verified_purchase = String()
    report_count = Integer(default=0)
    status = String(required=True)
    submitted_at = DateTime()
    last_reported_at = DateTime()


@reviews.projector(projector_for=ModerationQueue, aggregates=[Review])
class ModerationQueueProjector:
    @on(ReviewSubmitted)
    def on_review_submitted(self, event):
        current_domain.repository_for(ModerationQueue).add(
            ModerationQueue(
                review_id=event.review_id,
                product_id=event.product_id,
                customer_id=event.customer_id,
                rating=event.rating,
                title=event.title,
                body=event.body,
                verified_purchase=event.verified_purchase,
                report_count=0,
                status="Pending",
                submitted_at=event.submitted_at,
            )
        )

    @on(ReviewApproved)
    def on_review_approved(self, event):
        repo = current_domain.repository_for(ModerationQueue)
        try:
            mq = repo.get(event.review_id)
            repo.remove(mq)
        except Exception:
            pass

    @on(ReviewRejected)
    def on_review_rejected(self, event):
        repo = current_domain.repository_for(ModerationQueue)
        try:
            mq = repo.get(event.review_id)
            repo.remove(mq)
        except Exception:
            pass

    @on(ReviewReported)
    def on_review_reported(self, event):
        repo = current_domain.repository_for(ModerationQueue)
        try:
            mq = repo.get(event.review_id)
            mq.report_count = event.report_count
            mq.last_reported_at = event.reported_at
            repo.add(mq)
        except Exception:
            # Review was published (not in queue). Enrich from aggregate and re-add.
            try:
                review = current_domain.repository_for(Review).get(event.review_id)
                mq = ModerationQueue(
                    review_id=event.review_id,
                    product_id=str(review.product_id),
                    customer_id=str(review.customer_id),
                    rating=review.rating.score,
                    title=review.title,
                    body=review.body,
                    verified_purchase=str(review.verified_purchase),
                    report_count=event.report_count,
                    status="Reported",
                    last_reported_at=event.reported_at,
                )
                repo.add(mq)
            except Exception:
                pass  # Cannot enrich — skip silently

    @on(ReviewRemoved)
    def on_review_removed(self, event):
        repo = current_domain.repository_for(ModerationQueue)
        try:
            mq = repo.get(event.review_id)
            repo.remove(mq)
        except Exception:
            pass
