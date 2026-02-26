"""Fulfillment creation — command and handler."""

from protean import handle
from protean.fields import Dict, Identifier, List
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment


@fulfillment.command(part_of="Fulfillment")
class CreateFulfillment:
    """Create a new fulfillment for a paid order."""

    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    warehouse_id = Identifier()
    items = List(Dict(), required=True)


@fulfillment.command_handler(part_of=Fulfillment)
class CreateFulfillmentHandler:
    @handle(CreateFulfillment)
    def create_fulfillment(self, command):
        ff = Fulfillment.create(
            order_id=command.order_id,
            customer_id=command.customer_id,
            items_data=command.items,
            warehouse_id=command.warehouse_id,
        )
        current_domain.repository_for(Fulfillment).add(ff)
        return str(ff.id)
