"""Fulfillment creation — command and handler."""

import json

from protean import handle
from protean.fields import Identifier, Text
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment


@fulfillment.command(part_of="Fulfillment")
class CreateFulfillment:
    """Create a new fulfillment for a paid order."""

    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    warehouse_id = Identifier()
    items = Text(required=True)  # JSON list of item dicts


@fulfillment.command_handler(part_of=Fulfillment)
class CreateFulfillmentHandler:
    @handle(CreateFulfillment)
    def create_fulfillment(self, command):
        items_data = json.loads(command.items) if isinstance(command.items, str) else command.items
        ff = Fulfillment.create(
            order_id=command.order_id,
            customer_id=command.customer_id,
            items_data=items_data,
            warehouse_id=command.warehouse_id,
        )
        current_domain.repository_for(Fulfillment).add(ff)
        return str(ff.id)
