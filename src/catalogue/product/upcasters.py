"""Upcasters that move Product price events from float money to ``Decimal`` money.

v1 of these events stored prices as floats. v2 declares them as
``Decimal(precision=19, scale=4)``, so each upcaster rewrites the stored
floats as 4-place strings, rounded half-even.
"""

from typing import Any

from protean.core.upcaster import BaseUpcaster

from catalogue.domain import catalogue
from catalogue.product.events import TierPriceSet, VariantAdded, VariantPriceChanged
from shared.money import money_fields_as_text


@catalogue.upcaster(event_type=VariantAdded, from_version=1, to_version=2)
class UpcastVariantAddedV1ToV2(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        return money_fields_as_text(data, "price_amount")


@catalogue.upcaster(event_type=VariantPriceChanged, from_version=1, to_version=2)
class UpcastVariantPriceChangedV1ToV2(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        return money_fields_as_text(data, "previous_price", "new_price")


@catalogue.upcaster(event_type=TierPriceSet, from_version=1, to_version=2)
class UpcastTierPriceSetV1ToV2(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        return money_fields_as_text(data, "price")
