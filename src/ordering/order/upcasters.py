"""Upcasters that move Order events from float money to ``Decimal`` money.

Earlier versions of these events stored money as floats. The current versions
declare it as ``Decimal(precision=19, scale=4)``, so each upcaster rewrites the
stored floats as 4-place strings, rounded half-even. OrderCreated v1 to v2
lives in ``ordering.order.creation``; the chain continues here from v2 to v3.
"""

from typing import Any

from protean.core.upcaster import BaseUpcaster

from ordering.domain import ordering
from ordering.order.events import (
    ItemAdded,
    ItemQuantityUpdated,
    ItemRemoved,
    OrderCreated,
    OrderRefunded,
    PaymentSucceeded,
)
from shared.money import money_fields_as_text

ORDER_ITEM_MONEY_FIELDS = ("unit_price", "discount", "tax_amount")


@ordering.upcaster(event_type=OrderCreated, from_version=2, to_version=3)
class UpcastOrderCreatedV2ToV3(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        data["items"] = [money_fields_as_text(dict(item), *ORDER_ITEM_MONEY_FIELDS) for item in data.get("items") or []]
        return money_fields_as_text(data, "subtotal", "shipping_cost", "tax_total", "discount_total", "grand_total")


@ordering.upcaster(event_type=ItemAdded, from_version=1, to_version=2)
class UpcastItemAddedV1ToV2(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        return money_fields_as_text(data, "unit_price", "new_subtotal", "new_grand_total")


@ordering.upcaster(event_type=ItemRemoved, from_version=1, to_version=2)
class UpcastItemRemovedV1ToV2(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        return money_fields_as_text(data, "new_subtotal", "new_grand_total")


@ordering.upcaster(event_type=ItemQuantityUpdated, from_version=1, to_version=2)
class UpcastItemQuantityUpdatedV1ToV2(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        return money_fields_as_text(data, "new_subtotal", "new_grand_total")


@ordering.upcaster(event_type=PaymentSucceeded, from_version=1, to_version=2)
class UpcastPaymentSucceededV1ToV2(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        return money_fields_as_text(data, "amount")


@ordering.upcaster(event_type=OrderRefunded, from_version=1, to_version=2)
class UpcastOrderRefundedV1ToV2(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        return money_fields_as_text(data, "refund_amount")
