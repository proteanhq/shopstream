"""Mixed cross-domain workload scenario.

Combines journeys from all five bounded contexts with weights that
model realistic e-commerce traffic patterns. This is the recommended
scenario for load baseline testing.
"""

from locust import HttpUser, between

from loadtests.scenarios.catalogue import (
    CategoryHierarchyBuilder,
    ProductCatalogBuilder,
    ProductLifecycleJourney,
)
from loadtests.scenarios.identity import (
    AccountLifecycleJourney,
    NewCustomerJourney,
    TierProgressionJourney,
)
from loadtests.scenarios.inventory import (
    DamageWriteOffJourney,
    ReservationLifecycleJourney,
    StockInitAndReceiveJourney,
)
from loadtests.scenarios.ordering import (
    CartLifecycleJourney,
    CartToCheckoutJourney,
    OrderCancellationJourney,
    OrderFullLifecycleJourney,
    OrderReturnJourney,
)
from loadtests.scenarios.payments import (
    InvoiceJourney,
    PaymentFailureRetryJourney,
    PaymentRefundJourney,
    PaymentSuccessJourney,
)


class MixedWorkloadUser(HttpUser):
    """Realistic mixed workload simulating concurrent e-commerce activity.

    Weight distribution models real-world patterns across all 5 domains:

    Identity (20%):
    - Customer registration: most common write operation
    - Account lifecycle: less frequent
    - Tier progression: occasional

    Catalogue (15%):
    - Product catalog building: frequent seller activity
    - Product lifecycle: occasional
    - Category management: least frequent (admin activity)

    Ordering (30%):
    - Cart lifecycle: browsing & abandonment (most common)
    - Order full lifecycle: happy path
    - Cart to checkout: conversion
    - Order cancellation: unhappy path
    - Order returns: post-delivery

    Inventory (15%):
    - Stock init & receive: warehouse operations
    - Reservation lifecycle: order-driven
    - Damage write-off: infrequent

    Payments (20%):
    - Payment success: most common
    - Payment failure + retry: occasional
    - Refund: occasional
    - Invoice lifecycle: triggered by orders

    Creates cross-domain pressure on all five PostgreSQL databases
    simultaneously, testing the DomainContextMiddleware's ability
    to route to the correct domain under load.
    """

    wait_time = between(0.5, 3.0)
    tasks = {
        # Identity (20%)
        NewCustomerJourney: 8,
        AccountLifecycleJourney: 3,
        TierProgressionJourney: 2,
        # Catalogue (15%)
        ProductCatalogBuilder: 5,
        ProductLifecycleJourney: 2,
        CategoryHierarchyBuilder: 2,
        # Ordering (30%)
        CartLifecycleJourney: 6,
        OrderFullLifecycleJourney: 5,
        CartToCheckoutJourney: 3,
        OrderCancellationJourney: 3,
        OrderReturnJourney: 2,
        # Inventory (15%)
        StockInitAndReceiveJourney: 4,
        ReservationLifecycleJourney: 3,
        DamageWriteOffJourney: 2,
        # Payments (20%)
        PaymentSuccessJourney: 5,
        PaymentFailureRetryJourney: 3,
        PaymentRefundJourney: 2,
        InvoiceJourney: 2,
    }
