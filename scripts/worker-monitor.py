#!/usr/bin/env python3
"""Monitor per-worker message consumption across Redis consumer groups.

Sends a burst of API requests, then polls XPENDING to show which
consumer instance is processing each message in real-time.

Usage:
    python scripts/worker-monitor.py
"""

import contextlib
import subprocess
import sys
import threading
import time
from collections import defaultdict

import requests

sys.path.insert(0, ".")
from loadtests.data_generators import (
    customer_name,
    unique_external_id,
    valid_email,
    valid_phone,
)

REDIS_CMD = ["docker", "exec", "shopstream-redis-1", "redis-cli"]
API_URL = "http://localhost:8000"
STREAM = "identity::customer"
GROUPS = [
    "identity.projections.address_book.AddressBookProjector",
    "identity.projections.customer_card.CustomerCardProjector",
    "ordering.order.identity_events.IdentityOrderEventHandler",
]


def redis_cli(*args):
    result = subprocess.run(REDIS_CMD + list(args), capture_output=True, text=True)
    return result.stdout.strip()


def get_xpending_detail(stream, group, count=100):
    """Get XPENDING with consumer detail for each message."""
    output = redis_cli("XPENDING", stream, group, "-", "+", str(count))
    if not output:
        return []
    lines = output.split("\n")
    entries = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("1)"):
            msg_id = lines[i].strip().split(") ", 1)[1].strip('"')
            consumer = lines[i + 1].strip().split(") ", 1)[1].strip('"') if i + 1 < len(lines) else "?"
            entries.append({"message_id": msg_id, "consumer": consumer})
            i += 4  # skip idle time and delivery count
        else:
            i += 1
    return entries


def get_consumer_stats(stream, group):
    """Get per-consumer stats from XINFO CONSUMERS."""
    output = redis_cli("XINFO", "CONSUMERS", stream, group)
    if not output:
        return []
    lines = output.split("\n")
    consumers = []
    current = {}
    for i in range(0, len(lines), 2):
        if i + 1 >= len(lines):
            break
        key = lines[i].strip()
        val = lines[i + 1].strip()
        current[key] = val
        if key == "inactive":
            consumers.append(dict(current))
            current = {}
    return consumers


def register_customer():
    first, last = customer_name()
    with contextlib.suppress(Exception):
        requests.post(
            f"{API_URL}/customers",
            json={
                "external_id": unique_external_id(),
                "email": valid_email(),
                "phone": valid_phone(),
                "first_name": first,
                "last_name": last,
            },
            timeout=5,
        )


def main():
    burst_size = 50
    poll_interval = 0.1
    poll_duration = 5

    # Track which consumers we see actively processing
    active_consumers = defaultdict(lambda: defaultdict(int))

    # Record stream length before burst
    before = int(redis_cli("XLEN", STREAM) or "0")
    print(f"Stream '{STREAM}' has {before} messages before burst\n")

    # Fire burst
    print(f"Sending {burst_size} customer registrations...")
    threads = [threading.Thread(target=register_customer) for _ in range(burst_size)]
    for t in threads:
        t.start()

    # Poll XPENDING while burst is in-flight
    print(f"Polling consumer activity for {poll_duration}s...\n")
    start = time.time()
    polls = 0
    while time.time() - start < poll_duration:
        for group in GROUPS:
            entries = get_xpending_detail(STREAM, group)
            for entry in entries:
                active_consumers[group][entry["consumer"]] += 1
        polls += 1
        time.sleep(poll_interval)

    for t in threads:
        t.join()

    after = int(redis_cli("XLEN", STREAM) or "0")
    new_messages = after - before

    # Print results
    print("=" * 70)
    print("WORKER MESSAGE DISTRIBUTION REPORT")
    print("=" * 70)
    print(f"New messages produced: {new_messages}")
    print(f"Polls performed: {polls}")
    print()

    for group in GROUPS:
        short_name = group.split(".")[-1]
        consumers = get_consumer_stats(STREAM, group)
        print(f"--- {short_name} ({len(consumers)} consumers) ---")

        if active_consumers[group]:
            print(f"  {'Consumer':<55} {'Seen Active':>12}")
            for consumer, count in sorted(active_consumers[group].items(), key=lambda x: -x[1]):
                bar = "#" * min(count, 40)
                print(f"  {consumer:<55} {count:>8}    {bar}")
        else:
            print("  (messages processed too fast to observe in-flight)")

        print()

    # Also show final idle times to confirm all workers participated
    print("--- Final Consumer Idle Times ---")
    print(f"  {'Consumer':<55} {'Idle (ms)':>10}")
    for group in GROUPS:
        consumers = get_consumer_stats(STREAM, group)
        for c in consumers:
            print(f"  {c['name']:<55} {c['idle']:>10}")


if __name__ == "__main__":
    main()
