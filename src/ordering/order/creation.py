"""Order creation — command and handler."""

import json

from protean import handle
from protean.fields import Float, Identifier, String, Text
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.order.order import Order


@ordering.command(part_of="Order")
class CreateOrder:
    customer_id = Identifier(required=True)
    items = Text(required=True)  # JSON: list of item dicts
    shipping_address = Text(required=True)  # JSON: address dict
    billing_address = Text(required=True)  # JSON: address dict
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
        items_data = json.loads(command.items) if isinstance(command.items, str) else command.items
        shipping_address = (
            json.loads(command.shipping_address)
            if isinstance(command.shipping_address, str)
            else command.shipping_address
        )
        billing_address = (
            json.loads(command.billing_address) if isinstance(command.billing_address, str) else command.billing_address
        )

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
