"""Queries for the CategoryProducts projection."""

from protean import read
from protean.core.projection import BaseProjection
from protean.fields import Identifier
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.projections.category_products import CategoryProducts


@catalogue.query(part_of=CategoryProducts)
class GetCategoryProducts:
    category_id: str = Identifier(required=True)


@catalogue.query_handler(part_of=CategoryProducts)
class CategoryProductsQueryHandler:
    @read(GetCategoryProducts)
    def get_category_products(self, query: GetCategoryProducts) -> BaseProjection:
        return current_domain.view_for(CategoryProducts).get(query.category_id)
