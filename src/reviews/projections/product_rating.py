"""ProductRating — aggregated rating statistics per product.

Idempotent projector: it records which reviews it has already counted
(``counted_reviews``), so a redelivered ``ReviewApproved`` / ``ReviewRemoved``
is a no-op. Protean delivers events at least once and does not dedupe on the
consume side (proteanhq/protean#1042), so an accumulating projector must guard
itself or it double-counts. All aggregate stats are derived from
``counted_reviews`` rather than incremented in place.
"""

from protean.core.projector import on
from protean.fields import DateTime, Dict, Float, Identifier, Integer
from protean.utils.globals import current_domain

from reviews.domain import reviews
from reviews.review.events import ReviewApproved, ReviewRemoved
from reviews.review.review import Review


@reviews.projection
class ProductRating:
    product_id = Identifier(identifier=True, required=True)
    average_rating = Float(default=0.0)
    total_reviews = Integer(default=0)
    rating_distribution = Dict()
    verified_review_count = Integer(default=0)
    # review_id -> {"rating": int, "verified": bool}. The set of reviews counted
    # so far; makes the projector idempotent under at-least-once redelivery.
    counted_reviews = Dict()
    updated_at = DateTime()


def _default_distribution():
    return {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}


def _recalculate_average(distribution):
    total = sum(distribution.values())
    if total == 0:
        return 0.0
    weighted_sum = sum(int(rating) * count for rating, count in distribution.items())
    return round(weighted_sum / total, 2)


def _recompute(pr):
    """Derive all stats from the counted_reviews set (idempotent)."""
    distribution = _default_distribution()
    verified = 0
    for info in pr.counted_reviews.values():
        rating_key = str(info["rating"])
        distribution[rating_key] = distribution.get(rating_key, 0) + 1
        if info.get("verified"):
            verified += 1
    pr.rating_distribution = distribution
    pr.total_reviews = len(pr.counted_reviews)
    pr.verified_review_count = verified
    pr.average_rating = _recalculate_average(distribution)


def _is_verified(review_id) -> bool:
    try:
        review = current_domain.repository_for(Review).get(review_id)
        return bool(review.verified_purchase)
    except Exception:
        return False


@reviews.projector(projector_for=ProductRating, aggregates=[Review])
class ProductRatingProjector:
    @on(ReviewApproved)
    def on_review_approved(self, event):
        repo = current_domain.repository_for(ProductRating)
        try:
            pr = repo.get(event.product_id)
        except Exception:
            pr = ProductRating(
                product_id=event.product_id,
                rating_distribution=_default_distribution(),
                counted_reviews={},
            )

        counted = dict(pr.counted_reviews or {})
        review_key = str(event.review_id)
        if review_key in counted:
            return  # idempotent: this review is already counted

        counted[review_key] = {"rating": event.rating, "verified": _is_verified(event.review_id)}
        pr.counted_reviews = counted
        _recompute(pr)
        pr.updated_at = event.approved_at
        repo.add(pr)

    @on(ReviewRemoved)
    def on_review_removed(self, event):
        repo = current_domain.repository_for(ProductRating)
        try:
            pr = repo.get(event.product_id)
        except Exception:
            return  # no rating record to update

        counted = dict(pr.counted_reviews or {})
        review_key = str(event.review_id)
        if review_key not in counted:
            return  # idempotent: already removed (or never counted)

        del counted[review_key]
        pr.counted_reviews = counted
        _recompute(pr)
        pr.updated_at = event.removed_at
        repo.add(pr)
