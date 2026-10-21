"""No two ShopStream processes on one host try to bind the same port.

WHAT THIS CHECKS
    On a developer machine every process runs side by side: the API, the
    Observatory, Locust and nine engines. Each engine's health server binds the
    `[server.health] port` in its `domain.toml`, and with `port_auto_increment`
    on, each further `--workers N` worker takes the next free port above it.
    ShopStream keeps ten ports from each context's base (8100-8109 for
    identity, and so on). This check reads the nine `domain.toml` files,
    `loadtests/locust.conf`, the Makefile and `docker-compose.yml`, and asserts:

    - every context turns on `port_auto_increment` and binds loopback unless
      `PROTEAN_HEALTH_HOST` says otherwise;
    - no fixed port (API, Observatory, Locust) falls inside a context's range;
    - no two context ranges overlap;
    - no `make engine-*-scaled` target starts more workers than its range holds;
    - each compose engine sets `PROTEAN_HEALTH_HOST` to 0.0.0.0, and its
      healthcheck probes its context's base port.

    Protean walks up to 100 ports when the base is taken, so the ten-port range
    is a ShopStream convention, not a limit Protean enforces.
"""

from __future__ import annotations

import re
import tomllib
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTEXTS = (
    "identity",
    "catalogue",
    "ordering",
    "inventory",
    "payments",
    "fulfillment",
    "reviews",
    "notifications",
    "loyalty",
)
WORKERS_PER_CONTEXT = 10
# Protean's default for `protean observatory`, used when the target passes no --port.
OBSERVATORY_DEFAULT_PORT = 9000
HOST_TEMPLATE = "${PROTEAN_HEALTH_HOST|127.0.0.1}"


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def _recipe(target: str) -> str:
    """The first recipe line of a Makefile target."""
    match = re.search(rf"^{re.escape(target)}:.*\n\t(.*)", MAKEFILE, re.MULTILINE)
    assert match, f"the Makefile has no `{target}` target"
    return match.group(1)


def _compose_services() -> dict[str, str]:
    """Each top-level compose service's name and its block of text."""
    services = _read("docker-compose.yml").split("\nservices:\n", 1)[1]
    blocks = re.split(r"^  (?=[\w-]+:\n)", services, flags=re.MULTILINE)
    return {block.split(":", 1)[0]: block for block in blocks if block.strip() and not block.startswith(" ")}


MAKEFILE = _read("Makefile")
HEALTH = {context: tomllib.loads(_read("src", context, "domain.toml"))["server"]["health"] for context in CONTEXTS}
RANGES = {context: range(h["port"], h["port"] + WORKERS_PER_CONTEXT) for context, h in HEALTH.items()}


def _fixed_ports() -> dict[str, int]:
    api = re.search(r"--port (\d+)", _recipe("api"))
    assert api, "the `make api` target no longer passes --port"
    observatory = re.search(r"--port (\d+)", _recipe("observatory"))
    web = re.search(r"^web-port\s*=\s*(\d+)", _read("loadtests", "locust.conf"), re.MULTILINE)
    assert web, "loadtests/locust.conf no longer sets web-port"

    return {
        "api": int(api.group(1)),
        "observatory": int(observatory.group(1)) if observatory else OBSERVATORY_DEFAULT_PORT,
        "locust": int(web.group(1)),
    }


def test_every_context_auto_increments_on_a_configurable_host():
    for context, health in HEALTH.items():
        assert health.get("port_auto_increment") is True, context
        assert health.get("host") == HOST_TEMPLATE, context


def test_fixed_ports_are_distinct():
    ports = _fixed_ports()
    assert len(set(ports.values())) == len(ports), ports


def test_no_fixed_port_falls_in_an_engine_range():
    clashes = [
        (process, port, context)
        for process, port in _fixed_ports().items()
        for context, ports in RANGES.items()
        if port in ports
    ]
    assert not clashes, clashes


def test_engine_ranges_do_not_overlap():
    overlaps = [
        (a, b) for (a, ra), (b, rb) in combinations(RANGES.items(), 2) if ra.start < rb.stop and rb.start < ra.stop
    ]
    assert not overlaps, overlaps


def test_scaled_targets_fit_their_port_range():
    scaled = re.findall(r"--domain (\w+)\.domain --workers (\d+)", MAKEFILE)

    assert scaled, "no `--workers` engine targets found in the Makefile"
    too_many = [(context, int(n)) for context, n in scaled if int(n) > WORKERS_PER_CONTEXT]
    assert not too_many, too_many


def test_compose_engines_expose_and_probe_their_health_port():
    services = _compose_services()
    probed = {}
    for context in CONTEXTS:
        block = services[f"engine-{context}"]
        assert "<<: *engine-env" in block, f"engine-{context} does not merge *engine-env"
        probe = re.search(r"^      test: \[.*127\.0\.0\.1:(\d+)/readyz", block, re.MULTILINE)
        assert probe, f"engine-{context} has no /readyz healthcheck"
        probed[context] = int(probe.group(1))

    assert re.search(
        r"^x-engine-env:.*\n(?:  .*\n)*  PROTEAN_HEALTH_HOST: 0\.0\.0\.0$", _read("docker-compose.yml"), re.MULTILINE
    )
    assert probed == {context: h["port"] for context, h in HEALTH.items()}
