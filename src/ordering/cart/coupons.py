"""Cart coupon management — command and handler."""

from protean import handle
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from ordering.cart.cart import ShoppingCart
from ordering.domain import ordering


@ordering.command(part_of="ShoppingCart")
class ApplyCouponToCart:
    """Apply a coupon code to a shopping cart."""

    cart_id: str = Identifier(required=True)
    coupon_code: str = String(required=True, max_length=100)


@ordering.command_handler(part_of=ShoppingCart)
class ApplyCouponHandler:
    @handle(ApplyCouponToCart)
    def apply_coupon(self, command: ApplyCouponToCart) -> None:
        repo = current_domain.repository_for(ShoppingCart)
        cart = repo.get(command.cart_id)
        cart.apply_coupon(coupon_code=command.coupon_code)
        repo.add(cart)
