"""Queries for the ProductDetail projection."""

from protean import read
from protean.fields import Identifier
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.projections.product_detail import ProductDetail


@catalogue.query(part_of=ProductDetail)
class GetProductDetail:
    product_id = Identifier(required=True)


@catalogue.query_handler(part_of=ProductDetail)
class ProductDetailQueryHandler:
    @read(GetProductDetail)
    def get_product_detail(self, query):
        return current_domain.view_for(ProductDetail).get(query.product_id)
