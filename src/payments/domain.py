"""Payments & Billing bounded context — Payment Processing and Invoicing.

Handles payment lifecycle (event-sourced), refunds, invoice generation (CQRS),
and gateway abstraction for payment processing.
"""

import structlog
from protean.domain import Domain

payments = Domain(name="payments")

logger = structlog.get_logger(__name__)
