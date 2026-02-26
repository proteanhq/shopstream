"""Queries for the ProductReviews projection."""

from protean import read
from protean.fields import Identifier, Integer
from protean.utils.globals import current_domain

from reviews.domain import reviews
from reviews.projections.product_reviews import ProductReviews


@reviews.query(part_of=ProductReviews)
class ListProductReviews:
    product_id = Identifier(required=True)
    page = Integer(default=1)
    page_size = Integer(default=20)


@reviews.query_handler(part_of=ProductReviews)
class ProductReviewsQueryHandler:
    @read(ListProductReviews)
    def list_product_reviews(self, query):
        qs = current_domain.view_for(ProductReviews).query.filter(product_id=query.product_id)
        offset = (query.page - 1) * query.page_size
        return qs.offset(offset).limit(query.page_size).all()
