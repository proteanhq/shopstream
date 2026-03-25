"""Upcasters for Order events — schema evolution support."""

from protean.core.upcaster import BaseUpcaster

from ordering.domain import ordering
from ordering.order.events import OrderCreated


@ordering.upcaster(event_type=OrderCreated, from_version=1, to_version=2)
class UpcastOrderCreatedV1ToV2(BaseUpcaster):
    """v1 had no order_source field — default to 'web'."""

    def upcast(self, data: dict) -> dict:
        data["order_source"] = "web"
        return data
