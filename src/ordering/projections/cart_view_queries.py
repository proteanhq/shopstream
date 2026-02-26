"""Queries for the CartView projection."""

from protean import read
from protean.fields import Identifier
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.projections.cart_view import CartView


@ordering.query(part_of=CartView)
class GetCartView:
    cart_id = Identifier(required=True)


@ordering.query_handler(part_of=CartView)
class CartViewQueryHandler:
    @read(GetCartView)
    def get_cart_view(self, query):
        return current_domain.view_for(CartView).get(query.cart_id)
