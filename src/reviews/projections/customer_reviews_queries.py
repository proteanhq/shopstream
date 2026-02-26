"""Queries for the CustomerReviews projection."""

from protean import read
from protean.fields import Identifier, Integer
from protean.utils.globals import current_domain

from reviews.domain import reviews
from reviews.projections.customer_reviews import CustomerReviews


@reviews.query(part_of=CustomerReviews)
class ListCustomerReviews:
    customer_id = Identifier(required=True)
    page = Integer(default=1)
    page_size = Integer(default=20)


@reviews.query_handler(part_of=CustomerReviews)
class CustomerReviewsQueryHandler:
    @read(ListCustomerReviews)
    def list_customer_reviews(self, query):
        qs = current_domain.view_for(CustomerReviews).query.filter(customer_id=query.customer_id)
        offset = (query.page - 1) * query.page_size
        return qs.offset(offset).limit(query.page_size).all()
