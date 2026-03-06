"""ShopStream Load Testing — Locust entry point.

Discovers user classes from the scenarios package. Specialty scenarios
that create deliberate failures or timing-sensitive race conditions are
excluded from default discovery and must be run explicitly.

Usage:
    # All default scenarios (web UI):
    locust -f loadtests/locustfile.py

    # Mixed workload only:
    locust -f loadtests/locustfile.py MixedWorkloadUser

    # Cross-domain workload (generates expected saga/race failures):
    locust -f loadtests/scenarios/cross_domain.py CrossDomainUser

    # Headless (CI mode):
    locust -f loadtests/locustfile.py MixedWorkloadUser --headless \
           -u 50 -r 5 -t 300s --csv=results/loadtest

Specialty scenarios (run explicitly — these generate EXPECTED failures):

    Contention & race conditions:
        locust -f loadtests/scenarios/cross_domain.py FlashSaleUser      # Insufficient stock contention
        locust -f loadtests/scenarios/cross_domain.py RaceConditionUser  # Version conflicts

    Timing-sensitive saga/state races:
        locust -f loadtests/scenarios/ordering.py OrderingSagaUser            # Saga vs direct API race
        locust -f loadtests/scenarios/fulfillment.py FulfillmentTrackingUser  # Tracking before shipment
        locust -f loadtests/scenarios/notifications.py NotificationsCancelUser  # Cancel after send
        locust -f loadtests/scenarios/inventory.py InventoryMaintenanceUser -u 1  # Expire reservations

    Priority lanes:
        locust -f loadtests/scenarios/priority_lanes.py MigrationWithProductionTrafficUser
        locust -f loadtests/scenarios/priority_lanes.py BackfillDrainRateUser
        locust -f loadtests/scenarios/priority_lanes.py PriorityStarvationTestUser
        locust -f loadtests/scenarios/priority_lanes.py PriorityLanesDisabledBaseline

    Stress & burst traffic:
        locust -f loadtests/scenarios/stress.py SpikeUser       # Burst traffic (20 req/sec/user)
        locust -f loadtests/locustfile.py EventFloodUser        # Pipeline saturation
"""

import logging
import time

import requests
from locust import events

# Import all user classes so Locust discovers them
from loadtests.helpers.response import extract_error_detail
from loadtests.scenarios.catalogue import CatalogueUser  # noqa: F401

# CrossDomainUser is excluded from default discovery — ALL its journeys
# involve saga timing races or deliberate race conditions (E2E order lifecycle
# races the OrderCheckoutSaga, CancelDuringPayment is a deliberate race,
# ConcurrentOrderModification tests optimistic locking). These generate
# expected handler failures (RecordPaymentHandler, ReservationHandler).
# Run explicitly:
#   locust -f loadtests/scenarios/cross_domain.py CrossDomainUser
#   locust -f loadtests/scenarios/cross_domain.py FlashSaleUser
#   locust -f loadtests/scenarios/cross_domain.py RaceConditionUser
# SubscriberUser is included — happy-path subscriber ACL flows (no expected failures):
from loadtests.scenarios.cross_domain import SubscriberUser  # noqa: F401

# FulfillmentTrackingUser excluded — sends tracking webhooks before shipment,
# generating expected TrackingHandler failures. Run explicitly:
#   locust -f loadtests/locustfile.py FulfillmentTrackingUser
from loadtests.scenarios.fulfillment import FulfillmentUser  # noqa: F401
from loadtests.scenarios.identity import IdentityUser  # noqa: F401
from loadtests.scenarios.inventory import InventoryUser  # noqa: F401
from loadtests.scenarios.mixed import MixedWorkloadUser  # noqa: F401
from loadtests.scenarios.notifications import NotificationsUser  # noqa: F401

# OrderingSagaUser excluded — races the saga's RecordPaymentSuccess against
# a direct API call, generating expected handler failures. Run explicitly:
#   locust -f loadtests/locustfile.py OrderingSagaUser
from loadtests.scenarios.ordering import OrderingUser  # noqa: F401
from loadtests.scenarios.payments import PaymentsUser  # noqa: F401

# Priority lane scenarios excluded — MigrationWithProductionTrafficUser creates
# orders + confirms + fires payment webhooks, which triggers the OrderCheckoutSaga
# and generates RecordPaymentHandler failures. All priority lane scenarios are
# specialty tests for the priority lanes feature. Run explicitly:
#   locust -f loadtests/scenarios/priority_lanes.py MigrationWithProductionTrafficUser
#   locust -f loadtests/scenarios/priority_lanes.py BackfillDrainRateUser
#   locust -f loadtests/scenarios/priority_lanes.py PriorityStarvationTestUser
#   locust -f loadtests/scenarios/priority_lanes.py PriorityLanesDisabledBaseline
from loadtests.scenarios.reviews import ReviewsUser  # noqa: F401
from loadtests.scenarios.stress import EventFloodUser  # noqa: F401

# SpikeUser excluded — specialty burst scenario. Run explicitly:
#   locust -f loadtests/locustfile.py SpikeUser

logger = logging.getLogger("loadtest")

OBSERVATORY_URL = "http://localhost:9000/metrics"


@events.request.add_listener
def on_request(request_type, name, response, exception, **_kw):
    """Log error details for every failed request.

    Fires globally for all scenarios — no per-task wiring needed.
    Extracts the API error body so you see "Cannot reactivate from Active state"
    instead of just "422".
    """
    if exception:
        logger.error("[EXCEPTION] %s %s: %s", request_type, name, exception)
    elif response is not None and response.status_code >= 400:
        detail = extract_error_detail(response)
        logger.error("[%s] %s %s: %s", response.status_code, request_type, name, detail)


@events.test_start.add_listener
def on_test_start(environment, **_kwargs):
    """Log a marker when load test begins."""
    print(f"\n[LOADTEST] Started at {time.strftime('%H:%M:%S')}")
    print(f"[LOADTEST] Target host: {environment.host}")
    print(f"[LOADTEST] Observatory metrics: {OBSERVATORY_URL}")
    print()


@events.test_stop.add_listener
def on_test_stop(**_kwargs):
    """Fetch and print Observatory metrics when test ends."""
    print(f"\n[LOADTEST] Stopped at {time.strftime('%H:%M:%S')}")
    try:
        resp = requests.get(OBSERVATORY_URL, timeout=5)
        lines = [
            line
            for line in resp.text.split("\n")
            if any(keyword in line for keyword in ["protean_outbox", "protean_stream", "protean_broker"])
            and not line.startswith("#")
        ]
        if lines:
            print("\n[LOADTEST] Final infrastructure metrics:")
            for line in lines:
                print(f"  {line}")
        print()
    except Exception as e:
        print(f"[LOADTEST] Could not fetch Observatory metrics: {e}\n")
