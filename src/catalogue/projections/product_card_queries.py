"""Queries for the ProductCard projection."""

from protean import read
from protean.fields import Identifier, Integer, String
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.projections.product_card import ProductCard


@catalogue.query(part_of=ProductCard)
class ListProductCards:
    category_id = Identifier()
    status = String()
    page = Integer(default=1)
    page_size = Integer(default=20)


@catalogue.query_handler(part_of=ProductCard)
class ProductCardQueryHandler:
    @read(ListProductCards)
    def list_product_cards(self, query):
        qs = current_domain.view_for(ProductCard).query
        if query.category_id:
            qs = qs.filter(category_id=query.category_id)
        if query.status:
            qs = qs.filter(status=query.status)
        offset = (query.page - 1) * query.page_size
        return qs.offset(offset).limit(query.page_size).all()
