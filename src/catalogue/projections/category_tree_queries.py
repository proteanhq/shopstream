"""Queries for the CategoryTree projection."""

from protean import read
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.projections.category_tree import CategoryTree


@catalogue.query(part_of=CategoryTree)
class ListCategoryTree:
    pass


@catalogue.query_handler(part_of=CategoryTree)
class CategoryTreeQueryHandler:
    @read(ListCategoryTree)
    def list_category_tree(self, _query):
        return current_domain.view_for(CategoryTree).query.all()
