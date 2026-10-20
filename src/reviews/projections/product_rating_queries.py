"""Queries for the ProductRating projection."""

from protean import read
from protean.core.projection import BaseProjection
from protean.fields import Identifier
from protean.utils.globals import current_domain

from reviews.domain import reviews
from reviews.projections.product_rating import ProductRating


@reviews.query(part_of=ProductRating)
class GetProductRating:
    product_id: str = Identifier(required=True)


@reviews.query_handler(part_of=ProductRating)
class ProductRatingQueryHandler:
    @read(GetProductRating)
    def get_product_rating(self, query: GetProductRating) -> BaseProjection:
        return current_domain.view_for(ProductRating).get(query.product_id)
