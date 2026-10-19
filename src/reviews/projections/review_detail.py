"""ReviewDetail — full detail view of a single review."""

from datetime import datetime

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, List, String, Text
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
    review_id: str = Identifier(identifier=True, required=True)
    product_id: str = Identifier(required=True)
    variant_id: str | None = Identifier()
    customer_id: str = Identifier(required=True)
    order_id: str | None = Identifier()
    rating: int = Integer(required=True)
    title: str = String(required=True)
    body: str = Text(required=True)
    pros: list[str] = List(String())
    cons: list[str] = List(String())
    images: str | None = Text()
    verified_purchase: str | None = String()
    status: str = String(required=True)
    moderation_notes: str | None = Text()
    helpful_count: int = Integer(default=0)
    unhelpful_count: int = Integer(default=0)
    report_count: int = Integer(default=0)
    has_seller_reply: str = String(default="False")
    seller_reply_body: str | None = Text()
    seller_reply_at: datetime | None = DateTime()
    is_edited: str = String(default="False")
    created_at: datetime | None = DateTime()
    updated_at: datetime | None = DateTime()


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
        rd = repo.get_or_none(event.review_id)
        if rd is None:
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
        rd = repo.get_or_none(event.review_id)
        if rd is None:
            return
        rd.status = "Published"
        rd.updated_at = event.approved_at
        repo.add(rd)

    @on(ReviewRejected)
    def on_review_rejected(self, event):
        repo = current_domain.repository_for(ReviewDetail)
        rd = repo.get_or_none(event.review_id)
        if rd is None:
            return
        rd.status = "Rejected"
        rd.moderation_notes = event.reason
        rd.updated_at = event.rejected_at
        repo.add(rd)

    @on(HelpfulVoteRecorded)
    def on_helpful_vote_recorded(self, event):
        repo = current_domain.repository_for(ReviewDetail)
        rd = repo.get_or_none(event.review_id)
        if rd is None:
            return
        rd.helpful_count = event.helpful_count
        rd.unhelpful_count = event.unhelpful_count
        repo.add(rd)

    @on(ReviewReported)
    def on_review_reported(self, event):
        repo = current_domain.repository_for(ReviewDetail)
        rd = repo.get_or_none(event.review_id)
        if rd is None:
            return
        rd.report_count = event.report_count
        repo.add(rd)

    @on(ReviewRemoved)
    def on_review_removed(self, event):
        repo = current_domain.repository_for(ReviewDetail)
        rd = repo.get_or_none(event.review_id)
        if rd is None:
            return
        rd.status = "Removed"
        rd.moderation_notes = event.reason
        rd.updated_at = event.removed_at
        repo.add(rd)

    @on(SellerReplyAdded)
    def on_seller_reply_added(self, event):
        repo = current_domain.repository_for(ReviewDetail)
        rd = repo.get_or_none(event.review_id)
        if rd is None:
            return
        rd.has_seller_reply = "True"
        rd.seller_reply_body = event.body
        rd.seller_reply_at = event.replied_at
        repo.add(rd)
