"""Per-user state tracking for Locust load test scenarios.

Each Locust user instance maintains its own state — no cross-user sharing.
State tracks entity IDs returned by creation endpoints so follow-up
operations can reference them.
"""

from dataclasses import dataclass, field


@dataclass
class CustomerState:
    """Tracks state for a single simulated customer lifecycle."""

    customer_id: str | None = None
    address_count: int = 0
    current_tier: str = "STANDARD"
    current_status: str = "Active"


@dataclass
class ProductState:
    """Tracks state for a single simulated product lifecycle."""

    product_id: str | None = None
    variant_count: int = 0
    image_count: int = 0
    current_status: str = "Draft"


@dataclass
class CategoryState:
    """Tracks state for category hierarchy building."""

    category_ids: list[str] = field(default_factory=list)


@dataclass
class CartState:
    """Tracks state for a shopping cart lifecycle."""

    cart_id: str | None = None
    item_ids: list[str] = field(default_factory=list)
    item_count: int = 0


@dataclass
class OrderState:
    """Tracks state for a single order lifecycle."""

    order_id: str | None = None
    customer_id: str | None = None
    current_status: str = "Created"
    payment_id: str | None = None
    item_ids: list[str] = field(default_factory=list)


@dataclass
class InventoryState:
    """Tracks state for an inventory item lifecycle."""

    inventory_item_id: str | None = None
    warehouse_id: str | None = None
    reservation_ids: list[str] = field(default_factory=list)
    current_on_hand: int = 0
    current_available: int = 0


@dataclass
class PaymentState:
    """Tracks state for a payment lifecycle."""

    payment_id: str | None = None
    order_id: str | None = None
    amount: float = 0.0
    current_status: str = "pending"
    refund_id: str | None = None


@dataclass
class FulfillmentState:
    """Tracks state for a single fulfillment lifecycle."""

    fulfillment_id: str | None = None
    order_id: str | None = None
    tracking_number: str | None = None
    item_count: int = 0
    current_status: str = "Pending"


@dataclass
class CrossDomainState:
    """Tracks state across domains for end-to-end scenarios.

    Used by cross-domain journeys that create entities in multiple
    domains and thread them together via IDs.
    """

    customer_id: str | None = None
    product_id: str | None = None
    variant_id: str | None = None
    inventory_item_id: str | None = None
    warehouse_id: str | None = None
    cart_id: str | None = None
    order_id: str | None = None
    payment_id: str | None = None
    reservation_id: str | None = None
