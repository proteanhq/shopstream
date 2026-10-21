"""Price history — append-only analytics projection."""

from datetime import datetime
from decimal import Decimal as D

from protean.core.projector import on
from protean.fields import DateTime, Decimal, Identifier, String
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.product.events import VariantPriceChanged
from catalogue.product.product import Product


@catalogue.projection
class PriceHistory:
    entry_id: str = Identifier(identifier=True, required=True)
    product_id: str = Identifier(required=True)
    variant_id: str = Identifier(required=True)
    previous_price: D = Decimal(precision=19, scale=4, required=True)
    new_price: D = Decimal(precision=19, scale=4, required=True)
    currency: str = String(required=True)
    changed_at: datetime = DateTime(required=True)


@catalogue.projector(projector_for=PriceHistory, aggregates=[Product], idempotent=True)
class PriceHistoryProjector:
    @on(VariantPriceChanged)
    def on_variant_price_changed(self, event: VariantPriceChanged) -> None:
        import uuid

        current_domain.repository_for(PriceHistory).add(
            PriceHistory(
                entry_id=str(uuid.uuid4()),
                product_id=event.product_id,
                variant_id=event.variant_id,
                previous_price=event.previous_price,
                new_price=event.new_price,
                currency=event.currency,
                changed_at=datetime.now(),
            )
        )
