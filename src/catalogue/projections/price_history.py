"""Price history — append-only analytics projection."""

from datetime import datetime

from protean.core.projector import on
from protean.fields import DateTime, Float, Identifier, String
from protean.utils.globals import current_domain

from catalogue.domain import catalogue
from catalogue.product.events import VariantPriceChanged
from catalogue.product.product import Product


@catalogue.projection
class PriceHistory:
    entry_id: Identifier(identifier=True, required=True)
    product_id: Identifier(required=True)
    variant_id: Identifier(required=True)
    previous_price: Float(required=True)
    new_price: Float(required=True)
    currency: String(required=True)
    changed_at: DateTime(required=True)


@catalogue.projector(projector_for=PriceHistory, aggregates=[Product])
class PriceHistoryProjector:
    @on(VariantPriceChanged)
    def on_variant_price_changed(self, event):
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
