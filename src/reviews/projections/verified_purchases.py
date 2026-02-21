"""VerifiedPurchases — maps customer+product to order delivery for verified reviews.

Populated by the OrderDelivered cross-domain event handler.
"""

from protean.fields import DateTime, Identifier, String

from reviews.domain import reviews


@reviews.projection
class VerifiedPurchases:
    vp_id = Identifier(identifier=True, required=True)
    customer_id = String(required=True)
    product_id = String(required=True)
    variant_id = String()
    order_id = String(required=True)
    delivered_at = DateTime(required=True)
