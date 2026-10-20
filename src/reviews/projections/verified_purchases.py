"""VerifiedPurchases — maps customer+product to order delivery for verified reviews.

Populated by the OrderDelivered cross-domain event handler.
"""

from datetime import datetime

from protean.fields import DateTime, Identifier, String

from reviews.domain import reviews


@reviews.projection(externally_populated=True)
class VerifiedPurchases:
    vp_id: str = Identifier(identifier=True, required=True)
    customer_id: str = String(required=True)
    product_id: str = String(required=True)
    variant_id: str | None = String()
    order_id: str = String(required=True)
    delivered_at: datetime = DateTime(required=True)
