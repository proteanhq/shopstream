"""ShopStream Load Testing — Locust entry point.

Discovers all user classes from the scenarios package.
Run specific scenarios with Locust's class selection or use --tags.

Usage:
    # All scenarios (web UI):
    locust -f loadtests/locustfile.py

    # Mixed workload only:
    locust -f loadtests/locustfile.py MixedWorkloadUser

    # Stress test:
    locust -f loadtests/locustfile.py EventFloodUser

    # Headless (CI mode):
    locust -f loadtests/locustfile.py MixedWorkloadUser --headless \
           -u 50 -r 5 -t 300s --csv=results/loadtest
"""

import logging
import time

import requests
from locust import events

# Import all user classes so Locust discovers them
from loadtests.helpers.response import extract_error_detail
from loadtests.scenarios.catalogue import CatalogueUser  # noqa: F401
from loadtests.scenarios.identity import IdentityUser  # noqa: F401
from loadtests.scenarios.mixed import MixedWorkloadUser  # noqa: F401
from loadtests.scenarios.stress import EventFloodUser, SpikeUser  # noqa: F401

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
