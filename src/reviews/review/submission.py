"""SubmitReview — submit a new product review.

Enforces one-review-per-customer-per-product at handler level (cross-instance
check requires repository query). Checks VerifiedPurchases projection to flag
verified purchases.
"""

import json

from protean.fields import Identifier, Integer, String, Text
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from reviews.domain import reviews
from reviews.review.review import Review, ReviewStatus


@reviews.command(part_of="Review")
class SubmitReview:
    product_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    rating = Integer(required=True)
    title = String(required=True, max_length=200)
    body = Text(required=True)
    variant_id = Identifier()
    pros = Text()  # JSON array of strings
    cons = Text()  # JSON array of strings
    images = Text()  # JSON array of {url, alt_text}


@reviews.command_handler(part_of=Review)
class SubmitReviewHandler:
    @handle(SubmitReview)
    def submit_review(self, command):
        repo = current_domain.repository_for(Review)

        # Enforce one review per customer per product (exclude removed)
        existing = repo._dao.query.filter(
            customer_id=str(command.customer_id),
            product_id=str(command.product_id),
        ).all()
        if existing.items:
            active = [r for r in existing.items if r.status != ReviewStatus.REMOVED.value]
            if active:
                from protean.exceptions import ValidationError

                raise ValidationError({"review": ["You have already reviewed this product"]})

        # Check verified purchase
        verified = False
        order_id = None
        try:
            from reviews.projections.verified_purchases import VerifiedPurchases

            vp_repo = current_domain.repository_for(VerifiedPurchases)
            vps = vp_repo._dao.query.filter(
                customer_id=str(command.customer_id),
                product_id=str(command.product_id),
            ).all()
            if vps.items:
                verified = True
                order_id = str(vps.items[0].order_id)
        except Exception:
            pass  # If projection not available, proceed unverified

        # Parse images
        images_data = json.loads(command.images) if command.images else []
        pros_data = json.loads(command.pros) if command.pros else None
        cons_data = json.loads(command.cons) if command.cons else None

        review = Review.submit(
            product_id=command.product_id,
            customer_id=command.customer_id,
            rating=command.rating,
            title=command.title,
            body=command.body,
            variant_id=command.variant_id,
            order_id=order_id,
            verified_purchase=verified,
            pros=pros_data,
            cons=cons_data,
            images=images_data,
        )
        repo.add(review)
        return str(review.id)
