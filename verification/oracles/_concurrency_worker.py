"""Subprocess worker for the P2 no-lost-updates oracle (test_no_lost_updates.py).

This lives in its own importable module (not the test file) because the oracle
uses `multiprocessing` with the **spawn** start method: each worker is a fresh
interpreter that re-imports the target by qualified name. A pytest test module,
imported under `--import-mode=importlib`, has no stable importable name, so the
worker function must sit in a plain module like this one.

Each worker is a genuinely separate OS process with its own domain, its own DB
connections, and its own Unit of Work. The shared real Postgres + Message-DB are
the only synchronization point — exactly the setup needed to exercise Protean's
optimistic-concurrency control under true contention (not cooperative threads).
"""

from __future__ import annotations

import contextlib
import os
import sys

# Spawned children start from a bare interpreter; make sure `inventory` (under
# src/) and the repo root are importable regardless of how pytest was launched.
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (_REPO, os.path.join(_REPO, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_INITED = False


def _domain(env: str, retry_config: dict | None):
    """Init the inventory domain once per worker process.

    `retry_config` overrides `server.version_retry` for this process — the oracle
    uses it to run with generous retries (liveness) or with retry disabled
    (falsification). `None` leaves the shipped defaults untouched.
    """
    global _INITED
    os.environ["PROTEAN_ENV"] = env
    from inventory.domain import inventory

    if not _INITED:
        inventory.init()
        _INITED = True
    if retry_config is not None:
        server = inventory.config.setdefault("server", {})
        server.setdefault("version_retry", {}).update(retry_config)
    return inventory


def reserve_once(args):
    """Fire one ReserveStock(quantity=1) at the shared aggregate.

    Returns a short outcome tag the parent tallies:
      "ok"                   - the reservation committed
      "conflict"             - lost the optimistic-concurrency race (ExpectedVersionError)
      "insufficient"         - stock genuinely exhausted (ValidationError)
      "<ExceptionName>"      - anything unexpected (surfaces as a test failure)
    """
    env, item_id, order_id, barrier, retry_config = args
    inventory = _domain(env, retry_config)

    from protean.exceptions import ExpectedVersionError, ValidationError

    from inventory.stock.reservation import ReserveStock

    with inventory.domain_context():
        # Align every worker on the same starting version → maximal contention.
        # BrokenBarrierError (a sibling died/timed out) shouldn't abort the write.
        with contextlib.suppress(Exception):
            barrier.wait()
        try:
            inventory.process(
                ReserveStock(inventory_item_id=item_id, order_id=order_id, quantity=1),
                asynchronous=False,
            )
            return "ok"
        except ExpectedVersionError:
            return "conflict"
        except ValidationError as exc:
            if "Insufficient stock" in str(exc):
                return "insufficient"
            return f"ValidationError:{exc}"
        except Exception as exc:  # noqa: BLE001
            return f"{type(exc).__name__}:{str(exc)[:80]}"
