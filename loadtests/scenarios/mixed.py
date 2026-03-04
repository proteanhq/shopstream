"""Mixed cross-domain workload scenario.

Combines journeys from all seven bounded contexts with weights that
model realistic e-commerce traffic patterns. This is the recommended
scenario for load baseline testing.
"""

from locust import HttpUser, between

from loadtests.scenarios.catalogue import (
    CategoryHierarchyBuilder,
    ProductCatalogBuilder,
    ProductLifecycleJourney,
)
from loadtests.scenarios.fulfillment import (
    FulfillmentCancellationJourney,
    FulfillmentFullLifecycleJourney,
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
from loadtests.scenarios.reviews import (
    ReviewEditAndResubmitJourney,
    ReviewSellerReplyJourney,
    ReviewSubmitAndModerateJourney,
    ReviewVotingJourney,
)


class MixedWorkloadUser(HttpUser):
    """Realistic mixed workload simulating concurrent e-commerce activity.

    Weight distribution models real-world patterns across all 7 domains:

    Identity (15%):
    - Customer registration: most common write operation
    - Account lifecycle: less frequent
    - Tier progression: occasional

    Catalogue (12%):
    - Product catalog building: frequent seller activity
    - Product lifecycle: occasional
    - Category management: least frequent (admin activity)

    Ordering (23%):
    - Cart lifecycle: browsing & abandonment (most common)
    - Order full lifecycle: happy path
    - Cart to checkout: conversion
    - Order cancellation: unhappy path
    - Order returns: post-delivery

    Inventory (12%):
    - Stock init & receive: warehouse operations
    - Reservation lifecycle: order-driven
    - Damage write-off: infrequent

    Payments (15%):
    - Payment success: most common
    - Payment failure + retry: occasional
    - Refund: occasional
    - Invoice lifecycle: triggered by orders

    Fulfillment (10%):
    - Full lifecycle: warehouse to doorstep
    - Cancellation: before shipment

    Reviews (10%):
    - Submit and moderate: most common
    - Voting: community interaction
    - Edit and resubmit: rejection flow
    - Seller reply: seller engagement

    Creates cross-domain pressure on all seven PostgreSQL databases
    simultaneously, testing the DomainContextMiddleware's ability
    to route to the correct domain under load.
    """

    wait_time = between(0.5, 3.0)
    tasks = {
        # Identity (15%)
        NewCustomerJourney: 6,
        AccountLifecycleJourney: 3,
        TierProgressionJourney: 1,
        # Catalogue (12%)
        ProductCatalogBuilder: 4,
        ProductLifecycleJourney: 2,
        CategoryHierarchyBuilder: 2,
        # Ordering (23%)
        CartLifecycleJourney: 5,
        OrderFullLifecycleJourney: 4,
        CartToCheckoutJourney: 3,
        OrderCancellationJourney: 2,
        OrderReturnJourney: 1,
        # Inventory (12%)
        StockInitAndReceiveJourney: 4,
        ReservationLifecycleJourney: 3,
        DamageWriteOffJourney: 1,
        # Payments (15%)
        PaymentSuccessJourney: 5,
        PaymentFailureRetryJourney: 3,
        PaymentRefundJourney: 1,
        InvoiceJourney: 1,
        # Fulfillment (10%)
        FulfillmentFullLifecycleJourney: 4,
        FulfillmentCancellationJourney: 2,
        # Reviews (10%)
        ReviewSubmitAndModerateJourney: 3,
        ReviewVotingJourney: 2,
        ReviewEditAndResubmitJourney: 1,
        ReviewSellerReplyJourney: 1,
    }
