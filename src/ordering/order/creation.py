"""Order creation — command, handler, and v1→v2 upcaster."""

from decimal import Decimal as D
from typing import Any

from protean import handle
from protean.core.upcaster import BaseUpcaster
from protean.fields import Decimal, Dict, Identifier, List, String
from protean.utils.globals import current_domain
from protean.utils.processing import Priority, processing_priority

from ordering.domain import ordering
from ordering.order.events import OrderCreated
from ordering.order.order import Order


@ordering.command(part_of="Order")
class CreateOrder:
    """Create a new order from a shopping cart's items, addresses, and pricing."""

    customer_id: str = Identifier(required=True)
    items: list[dict[str, Any]] = List(Dict(), required=True)
    shipping_address: dict[str, Any] = Dict(required=True)
    billing_address: dict[str, Any] = Dict(required=True)
    subtotal: D = Decimal(precision=19, scale=4, required=True)
    shipping_cost: D = Decimal(precision=19, scale=4, default=D("0"))
    tax_total: D = Decimal(precision=19, scale=4, default=D("0"))
    discount_total: D = Decimal(precision=19, scale=4, default=D("0"))
    grand_total: D = Decimal(precision=19, scale=4, required=True)
    currency: str = String(max_length=3, default="USD")
    order_source: str = String(max_length=20, default="web")


@ordering.command_handler(part_of=Order)
class CreateOrderHandler:
    @handle(CreateOrder)
    def create_order(self, command: CreateOrder) -> str:
        with processing_priority(Priority.HIGH):
            items_data = command.items
            shipping_address = command.shipping_address
            billing_address = command.billing_address

            pricing = {
                "subtotal": command.subtotal,
                "shipping_cost": command.shipping_cost,
                "tax_total": command.tax_total,
                "discount_total": command.discount_total,
                "grand_total": command.grand_total,
                "currency": command.currency or "USD",
            }

            order = Order.create(
                customer_id=command.customer_id,
                items_data=items_data,
                shipping_address=shipping_address,
                billing_address=billing_address,
                pricing=pricing,
                order_source=command.order_source or "web",
            )
            current_domain.repository_for(Order).add(order)
            return str(order.id)


# ---------------------------------------------------------------------------
# Upcaster: OrderCreated v1 → v2
# ---------------------------------------------------------------------------
@ordering.upcaster(event_type=OrderCreated, from_version=1, to_version=2)
class UpcastOrderCreatedV1ToV2(BaseUpcaster):
    """v1 had no order_source field — default to 'web'."""

    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        data["order_source"] = "web"
        return data
