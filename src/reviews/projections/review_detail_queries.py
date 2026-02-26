"""Queries for the ReviewDetail projection."""

from protean import read
from protean.fields import Identifier
from protean.utils.globals import current_domain

from reviews.domain import reviews
from reviews.projections.review_detail import ReviewDetail


@reviews.query(part_of=ReviewDetail)
class GetReviewDetail:
    review_id = Identifier(required=True)


@reviews.query_handler(part_of=ReviewDetail)
class ReviewDetailQueryHandler:
    @read(GetReviewDetail)
    def get_review_detail(self, query):
        return current_domain.view_for(ReviewDetail).get(query.review_id)
