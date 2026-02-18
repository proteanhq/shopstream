"""Ordering bounded context — Order Management and Shopping Cart.

Handles order lifecycle (event-sourced), shopping cart management (CQRS),
and the checkout flow that converts carts to orders.
"""

import structlog
from protean.domain import Domain

ordering = Domain(name="ordering")

logger = structlog.get_logger(__name__)
