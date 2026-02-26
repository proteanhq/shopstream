"""Order creation — command and handler."""

from protean import handle
from protean.fields import Dict, Float, Identifier, List, String
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.order import Order


@ordering.command(part_of="Order")
class CreateOrder:
    """Create a new order from a shopping cart's items, addresses, and pricing."""

    customer_id = Identifier(required=True)
    items = List(Dict(), required=True)
    shipping_address = Dict(required=True)
    billing_address = Dict(required=True)
    subtotal = Float(required=True)
    shipping_cost = Float(default=0.0)
    tax_total = Float(default=0.0)
    discount_total = Float(default=0.0)
    grand_total = Float(required=True)
    currency = String(max_length=3, default="USD")


@ordering.command_handler(part_of=Order)
class CreateOrderHandler:
    @handle(CreateOrder)
    def create_order(self, command):
        items_data = command.items
        shipping_address = command.shipping_address
        billing_address = command.billing_address

        pricing = {
            "subtotal": command.subtotal,
            "shipping_cost": command.shipping_cost or 0.0,
            "tax_total": command.tax_total or 0.0,
            "discount_total": command.discount_total or 0.0,
            "grand_total": command.grand_total,
            "currency": command.currency or "USD",
        }

        order = Order.create(
            customer_id=command.customer_id,
            items_data=items_data,
            shipping_address=shipping_address,
            billing_address=billing_address,
            pricing=pricing,
        )
        current_domain.repository_for(Order).add(order)
        return str(order.id)
