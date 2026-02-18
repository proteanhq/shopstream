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

import time

import requests
from locust import events

# Import all user classes so Locust discovers them
from loadtests.scenarios.catalogue import CatalogueUser  # noqa: F401
from loadtests.scenarios.identity import IdentityUser  # noqa: F401
from loadtests.scenarios.mixed import MixedWorkloadUser  # noqa: F401
from loadtests.scenarios.stress import EventFloodUser, SpikeUser  # noqa: F401

OBSERVATORY_URL = "http://localhost:9000/metrics"


@events.test_start.add_listener
def on_test_start(environment, **_kwargs):
    """Log a marker when load test begins."""
    print(f"\n[LOADTEST] Started at {time.strftime('%H:%M:%S')}")
    print(f"[LOADTEST] Target host: {environment.host}")
    print(f"[LOADTEST] Observatory metrics: {OBSERVATORY_URL}")
    print()


@events.test_stop.add_listener
def on_test_stop(_environment, **_kwargs):
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
