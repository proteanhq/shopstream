"""ProductRating — aggregated rating statistics per product."""

import json

from protean.core.projector import on
from protean.fields import DateTime, Float, Identifier, Integer, Text
from protean.utils.globals import current_domain

from reviews.domain import reviews
from reviews.review.events import ReviewApproved, ReviewRemoved
from reviews.review.review import Review


@reviews.projection
class ProductRating:
    product_id = Identifier(identifier=True, required=True)
    average_rating = Float(default=0.0)
    total_reviews = Integer(default=0)
    rating_distribution = Text()  # JSON: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    verified_review_count = Integer(default=0)
    updated_at = DateTime()


def _default_distribution():
    return json.dumps({"1": 0, "2": 0, "3": 0, "4": 0, "5": 0})


def _recalculate_average(distribution):
    total = sum(distribution.values())
    if total == 0:
        return 0.0
    weighted_sum = sum(int(rating) * count for rating, count in distribution.items())
    return round(weighted_sum / total, 2)


@reviews.projector(projector_for=ProductRating, aggregates=[Review])
class ProductRatingProjector:
    @on(ReviewApproved)
    def on_review_approved(self, event):
        repo = current_domain.repository_for(ProductRating)

        try:
            pr = repo.get(event.product_id)
            distribution = json.loads(pr.rating_distribution)
        except Exception:
            pr = ProductRating(
                product_id=event.product_id,
                total_reviews=0,
                rating_distribution=_default_distribution(),
                verified_review_count=0,
            )
            distribution = json.loads(pr.rating_distribution)

        # Increment count for this rating
        rating_key = str(event.rating)
        distribution[rating_key] = distribution.get(rating_key, 0) + 1

        pr.total_reviews = pr.total_reviews + 1
        pr.rating_distribution = json.dumps(distribution)
        pr.average_rating = _recalculate_average(distribution)
        pr.updated_at = event.approved_at

        # Check if verified
        try:
            review_repo = current_domain.repository_for(Review)
            review = review_repo.get(event.review_id)
            if review.verified_purchase:
                pr.verified_review_count = pr.verified_review_count + 1
        except Exception:
            pass

        repo.add(pr)

    @on(ReviewRemoved)
    def on_review_removed(self, event):
        repo = current_domain.repository_for(ProductRating)

        try:
            pr = repo.get(event.product_id)
        except Exception:
            return  # No rating record to update

        distribution = json.loads(pr.rating_distribution)
        rating_key = str(event.rating)
        distribution[rating_key] = max(0, distribution.get(rating_key, 0) - 1)

        pr.total_reviews = max(0, pr.total_reviews - 1)
        pr.rating_distribution = json.dumps(distribution)
        pr.average_rating = _recalculate_average(distribution)
        pr.updated_at = event.removed_at

        repo.add(pr)
