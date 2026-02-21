"""ProductReviews — published reviews for a product detail page."""

from protean.core.projector import on
from protean.fields import DateTime, Identifier, Integer, String, Text
from protean.utils.globals import current_domain

from reviews.domain import reviews
from reviews.review.events import (
    HelpfulVoteRecorded,
    ReviewApproved,
    ReviewRemoved,
    SellerReplyAdded,
)
from reviews.review.review import Review


@reviews.projection
class ProductReviews:
    review_id = Identifier(identifier=True, required=True)
    product_id = Identifier(required=True)
    variant_id = Identifier()
    customer_id = Identifier(required=True)
    rating = Integer(required=True)
    title = String(required=True)
    body = Text(required=True)
    pros = Text()
    cons = Text()
    images = Text()  # JSON array
    verified_purchase = String()
    helpful_count = Integer(default=0)
    unhelpful_count = Integer(default=0)
    has_seller_reply = String(default="False")
    seller_reply_body = Text()
    is_edited = String(default="False")
    published_at = DateTime()


@reviews.projector(projector_for=ProductReviews, aggregates=[Review])
class ProductReviewsProjector:
    @on(ReviewApproved)
    def on_review_approved(self, event):
        repo = current_domain.repository_for(Review)
        review = repo.get(event.review_id)

        current_domain.repository_for(ProductReviews).add(
            ProductReviews(
                review_id=event.review_id,
                product_id=event.product_id,
                variant_id=str(review.variant_id) if review.variant_id else None,
                customer_id=event.customer_id,
                rating=event.rating,
                title=review.title,
                body=review.body,
                pros=review.pros,
                cons=review.cons,
                images=None,  # Could serialize review.images if needed
                verified_purchase=str(review.verified_purchase),
                helpful_count=review.helpful_count,
                unhelpful_count=review.unhelpful_count,
                has_seller_reply="True" if review.reply else "False",
                is_edited=str(review.is_edited),
                published_at=event.approved_at,
            )
        )

    @on(HelpfulVoteRecorded)
    def on_helpful_vote_recorded(self, event):
        repo = current_domain.repository_for(ProductReviews)
        try:
            pr = repo.get(event.review_id)
        except Exception:
            return  # Review not yet published
        pr.helpful_count = event.helpful_count
        pr.unhelpful_count = event.unhelpful_count
        repo.add(pr)

    @on(ReviewRemoved)
    def on_review_removed(self, event):
        repo = current_domain.repository_for(ProductReviews)
        try:
            pr = repo.get(event.review_id)
            repo.remove(pr)
        except Exception:
            pass  # Already removed or never published

    @on(SellerReplyAdded)
    def on_seller_reply_added(self, event):
        repo = current_domain.repository_for(ProductReviews)
        try:
            pr = repo.get(event.review_id)
        except Exception:
            return
        pr.has_seller_reply = "True"
        pr.seller_reply_body = event.body
        repo.add(pr)
