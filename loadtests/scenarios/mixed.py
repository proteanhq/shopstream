"""Mixed cross-domain workload scenario.

Combines journeys from all eight bounded contexts with weights that
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
    FulfillmentCreationJourney,
    FulfillmentPickerCancelJourney,
    FulfillmentTrackingWebhookJourney,
)
from loadtests.scenarios.identity import (
    AccountLifecycleJourney,
    NewCustomerJourney,
    TierProgressionJourney,
)
from loadtests.scenarios.inventory import (
    DamageWriteOffJourney,
    ExpireReservationsJourney,
    ReservationLifecycleJourney,
    ReturnToStockJourney,
    StockInitAndReceiveJourney,
    WarehouseManagementJourney,
)
from loadtests.scenarios.notifications import (
    NotificationCancelJourney,
    PreferenceManagementJourney,
    QuietHoursLifecycleJourney,
    UnsubscribeResubscribeJourney,
)
from loadtests.scenarios.ordering import (
    CartLifecycleJourney,
    CartToCheckoutJourney,
    OrderCancellationJourney,
    OrderCheckoutSagaJourney,
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
    ReviewReportAndRemoveJourney,
    ReviewSellerReplyJourney,
    ReviewSubmitAndModerateJourney,
    ReviewVotingJourney,
)


class MixedWorkloadUser(HttpUser):
    """Realistic mixed workload simulating concurrent e-commerce activity.

    Weight distribution models real-world patterns across all 8 domains:

    Identity (12%):
    - Customer registration: most common write + read verification
    - Account lifecycle: state machine exercise
    - Tier progression: occasional

    Catalogue (10%):
    - Product catalog building: seller activity + read verification
    - Product lifecycle: state machine
    - Category management: admin activity + read verification

    Ordering (20%):
    - Cart lifecycle: browsing + cart view + abandonment
    - Order full lifecycle: happy path + order detail + timeline reads
    - Checkout saga: cart → order → payment flow
    - Cart to checkout: conversion
    - Order cancellation: unhappy path
    - Order returns: post-delivery

    Inventory (12%):
    - Stock init & receive: warehouse operations
    - Reservation creation: order-driven
    - Damage write-off: quality control
    - Return to stock: order returns
    - Warehouse management: admin operations
    - Reservation expiry: maintenance

    Payments (12%):
    - Payment success: most common
    - Payment failure + retry: occasional
    - Refund: occasional
    - Invoice lifecycle: triggered by orders

    Fulfillment (10%):
    - Creation + picker assignment: warehouse ops
    - Cancellation: before shipment
    - Tracking webhooks: carrier updates
    - Picker cancel: cancel during picking

    Reviews (10%):
    - Submit and moderate: most common + read verification
    - Voting: community interaction
    - Edit and resubmit: rejection flow
    - Seller reply: seller engagement
    - Report and remove: content moderation

    Notifications (8%):
    - Preference management: channel configuration
    - Quiet hours: do-not-disturb
    - Unsubscribe/resubscribe: opt-out flow
    - Notification cancel: lifecycle management

    Creates cross-domain pressure on all eight PostgreSQL databases
    simultaneously, testing the DomainContextMiddleware's ability
    to route to the correct domain under load.
    """

    wait_time = between(0.5, 3.0)
    tasks = {
        # Identity (12%)
        NewCustomerJourney: 5,
        AccountLifecycleJourney: 2,
        TierProgressionJourney: 1,
        # Catalogue (10%)
        ProductCatalogBuilder: 3,
        ProductLifecycleJourney: 2,
        CategoryHierarchyBuilder: 2,
        # Ordering (20%)
        CartLifecycleJourney: 4,
        OrderFullLifecycleJourney: 3,
        OrderCheckoutSagaJourney: 3,
        CartToCheckoutJourney: 2,
        OrderCancellationJourney: 1,
        OrderReturnJourney: 1,
        # Inventory (12%)
        StockInitAndReceiveJourney: 3,
        ReservationLifecycleJourney: 2,
        DamageWriteOffJourney: 1,
        ReturnToStockJourney: 1,
        WarehouseManagementJourney: 1,
        ExpireReservationsJourney: 1,
        # Payments (12%)
        PaymentSuccessJourney: 4,
        PaymentFailureRetryJourney: 2,
        PaymentRefundJourney: 1,
        InvoiceJourney: 1,
        # Fulfillment (10%)
        FulfillmentCreationJourney: 3,
        FulfillmentCancellationJourney: 2,
        FulfillmentTrackingWebhookJourney: 2,
        FulfillmentPickerCancelJourney: 1,
        # Reviews (10%)
        ReviewSubmitAndModerateJourney: 3,
        ReviewVotingJourney: 2,
        ReviewEditAndResubmitJourney: 1,
        ReviewSellerReplyJourney: 1,
        ReviewReportAndRemoveJourney: 1,
        # Notifications (8%)
        PreferenceManagementJourney: 3,
        UnsubscribeResubscribeJourney: 2,
        QuietHoursLifecycleJourney: 1,
        NotificationCancelJourney: 1,
    }
