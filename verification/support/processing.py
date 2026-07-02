"""Drive a command through the *whole* runtime path, then wait for it to settle.

WHY THIS EXISTS
    Protean already ships a unit-test DSL (`protean.testing.given().process()`)
    for pure, in-memory tests of aggregates, process managers and projections.
    It stops at the aggregate boundary. It does NOT exercise the path a command
    actually takes at runtime:

        command -> handler -> aggregate -> UoW commit -> outbox
                -> engine -> broker -> subscription -> projector -> read model

    How much of that runs synchronously depends on the domain's
    `event_processing` config:

      * `sync`  (PROTEAN_ENV=test / memory) - the whole chain runs inline during
        the UoW commit, so a test can read the projection immediately.
      * `async` (production, and the engine-driven tests) - the command returns
        as soon as its outbox rows are written; a background engine drains them
        afterwards. A test that asserts on the read model must wait for it.

    `process_and_wait` hides that difference so the SAME test body works in
    either mode. `drain` is the primitive underneath it - run the engine until a
    condition holds - factored out so tests (and the load suite) stop
    hand-rolling their own bounded `for _ in range(n): Engine(...).run()` loops.

SCOPE / HONESTY
    This is a ShopStream-local seed. The richer version - one that also returns
    the events that fired and any handler error, without reaching into framework
    internals - belongs in `protean.testing`. Filed upstream as
    proteanhq/protean#1065. Until that lands, this helper deliberately returns
    only the command result and leaves event/read-model assertions to the caller.

    The `async` branch (`drain`) can only be exercised with a live engine +
    broker, so it is covered by the engine-marked DLQ test, not by the in-memory
    CI run. The `sync` branch is covered in CI (see test_processing.py).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from protean.server.engine import Engine
from protean.utils import Processing

# A bounded default: the runtime pipeline (outbox -> publish -> deliver ->
# project) can need more than one test-mode engine pass to fully settle, but it
# must never loop forever. Callers with a precise stop condition pass `until`.
DEFAULT_MAX_CYCLES = 10


def _is_sync(domain: Any) -> bool:
    """True when the domain processes events inline (no engine needed)."""
    return domain.config["event_processing"] == Processing.SYNC.value


def drain(
    domain: Any,
    *,
    until: Callable[[], bool] | None = None,
    max_cycles: int = DEFAULT_MAX_CYCLES,
) -> int:
    """Run `domain`'s engine in test mode until it settles; return cycles run.

    Each `Engine(...).run()` is a single bounded test-mode pass. We repeat it
    because one command can fan out across several pipeline steps (outbox ->
    publish -> deliver -> project / retry -> DLQ), and a single pass may not
    carry a message all the way through.

    Args:
        domain: the Protean `Domain` whose engine to run.
        until: optional predicate; stop as soon as it returns truthy. When
            omitted, run the full `max_cycles` (best-effort drain).
        max_cycles: hard upper bound on engine passes, so a stuck pipeline
            fails the test with a timeout rather than hanging.

    Returns:
        The number of engine passes actually run.
    """
    for cycle in range(1, max_cycles + 1):
        Engine(domain, test_mode=True).run()
        if until is not None and until():
            return cycle
    return max_cycles


def process_and_wait(
    command: Any,
    domain: Any,
    *,
    until: Callable[[], bool] | None = None,
    max_cycles: int = DEFAULT_MAX_CYCLES,
) -> Any | None:
    """Process `command` and block until its events have been handled.

    In a `sync` domain the events fire inline during the command's UoW commit,
    so this returns as soon as the handler does. In an `async` domain the events
    land in the outbox; this drains the engine before returning, so the caller
    can assert on the read model either way.

    Args:
        command: an instance of a `@domain.command`-decorated class.
        domain: the Protean `Domain` to process against.
        until: forwarded to `drain` (async domains only). A precise stop
            condition - e.g. `lambda: repo.get(id).total == 1` - both speeds the
            wait up and turns a never-satisfied pipeline into a clean timeout.
        max_cycles: forwarded to `drain`.

    Returns:
        The command handler's return value (e.g. the new aggregate id).
    """
    # asynchronous=False runs the handler now and returns its value; event
    # dispatch still follows the domain's event_processing config.
    result = domain.process(command, asynchronous=False)
    if _is_sync(domain):
        return result
    drain(domain, until=until, max_cycles=max_cycles)
    return result
