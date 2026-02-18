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
