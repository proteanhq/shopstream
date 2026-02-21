"""ReviewDetail — full detail view of a single review."""

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String, Text
from protean.utils.globals import current_domain

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
from reviews.review.review import Review


@reviews.projection
class ReviewDetail:
    review_id = Identifier(identifier=True, required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier()
    customer_id = Identifier(required=True)
    order_id = Identifier()
    rating = Integer(required=True)
    title = String(required=True)
    body = Text(required=True)
    pros = Text()
    cons = Text()
    images = Text()
    verified_purchase = String()
    status = String(required=True)
    moderation_notes = Text()
    helpful_count = Integer(default=0)
    unhelpful_count = Integer(default=0)
    report_count = Integer(default=0)
    has_seller_reply = String(default="False")
    seller_reply_body = Text()
    seller_reply_at = DateTime()
    is_edited = String(default="False")
    created_at = DateTime()
    updated_at = DateTime()


@reviews.projector(projector_for=ReviewDetail, aggregates=[Review])
class ReviewDetailProjector:
    @on(ReviewSubmitted)
    def on_review_submitted(self, event):
        current_domain.repository_for(ReviewDetail).add(
            ReviewDetail(
                review_id=event.review_id,
                product_id=event.product_id,
                variant_id=event.variant_id,
                customer_id=event.customer_id,
                order_id=event.order_id,
                rating=event.rating,
                title=event.title,
                body=event.body,
                pros=event.pros,
                cons=event.cons,
                verified_purchase=event.verified_purchase,
                status="Pending",
                created_at=event.submitted_at,
                updated_at=event.submitted_at,
            )
        )

    @on(ReviewEdited)
    def on_review_edited(self, event):
        repo = current_domain.repository_for(ReviewDetail)
        try:
            rd = repo.get(event.review_id)
        except Exception:
            return
        if event.title:
            rd.title = event.title
        if event.body:
            rd.body = event.body
        if event.rating:
            rd.rating = event.rating
        rd.is_edited = "True"
        rd.status = "Pending"
        rd.updated_at = event.edited_at
        repo.add(rd)

    @on(ReviewApproved)
    def on_review_approved(self, event):
        repo = current_domain.repository_for(ReviewDetail)
        try:
            rd = repo.get(event.review_id)
        except Exception:
            return
        rd.status = "Published"
        rd.updated_at = event.approved_at
        repo.add(rd)

    @on(ReviewRejected)
    def on_review_rejected(self, event):
        repo = current_domain.repository_for(ReviewDetail)
        try:
            rd = repo.get(event.review_id)
        except Exception:
            return
        rd.status = "Rejected"
        rd.moderation_notes = event.reason
        rd.updated_at = event.rejected_at
        repo.add(rd)

    @on(HelpfulVoteRecorded)
    def on_helpful_vote_recorded(self, event):
        repo = current_domain.repository_for(ReviewDetail)
        try:
            rd = repo.get(event.review_id)
        except Exception:
            return
        rd.helpful_count = event.helpful_count
        rd.unhelpful_count = event.unhelpful_count
        repo.add(rd)

    @on(ReviewReported)
    def on_review_reported(self, event):
        repo = current_domain.repository_for(ReviewDetail)
        try:
            rd = repo.get(event.review_id)
        except Exception:
            return
        rd.report_count = event.report_count
        repo.add(rd)

    @on(ReviewRemoved)
    def on_review_removed(self, event):
        repo = current_domain.repository_for(ReviewDetail)
        try:
            rd = repo.get(event.review_id)
        except Exception:
            return
        rd.status = "Removed"
        rd.moderation_notes = event.reason
        rd.updated_at = event.removed_at
        repo.add(rd)

    @on(SellerReplyAdded)
    def on_seller_reply_added(self, event):
        repo = current_domain.repository_for(ReviewDetail)
        try:
            rd = repo.get(event.review_id)
        except Exception:
            return
        rd.has_seller_reply = "True"
        rd.seller_reply_body = event.body
        rd.seller_reply_at = event.replied_at
        repo.add(rd)
