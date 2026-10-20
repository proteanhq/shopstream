"""Oracle: `protean idempotency cleanup` prunes old processed-message markers.

An idempotent projector writes one marker per (message id, handler) it has
applied. A marker only matters while its event can still be redelivered, so
`make idempotency-cleanup` runs `cleanup_processed_messages` for each domain to
delete markers older than `[consume_idempotency.cleanup] retention_hours`.

Each case writes markers with a known `processed_at`, runs the cleanup, and
checks which markers are left. The timestamps sit a full day or more away from
the cutoff, so the result does not depend on how long the test takes.
"""

import os
import re
import subprocess
import sys
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from protean.utils.consume_idempotency import ProcessedMessage, cleanup_processed_messages
from protean.utils.globals import current_domain

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
CONTEXTS = [
    "identity",
    "catalogue",
    "ordering",
    "inventory",
    "payments",
    "fulfillment",
    "reviews",
    "notifications",
    "loyalty",
]


def _marker_repo():
    return current_domain._get_processed_message_repo("default")


def _write_marker(message_id: str, age_hours: int) -> None:
    _marker_repo()._dao.save(
        ProcessedMessage(
            message_id=message_id,
            handler="payments.projections.daily_revenue.DailyRevenueProjector.on_payment_succeeded",
            processed_at=datetime.now(UTC) - timedelta(hours=age_hours),
        )
    )


def _remaining_message_ids() -> list[str]:
    return sorted(m.message_id for m in _marker_repo()._dao.query.all().items)


@pytest.mark.usefixtures("payments_ctx")
def test_cleanup_deletes_only_markers_older_than_the_window():
    _write_marker("payments::payment-old-1", age_hours=48)
    _write_marker("payments::payment-new-1", age_hours=0)
    assert _remaining_message_ids() == ["payments::payment-new-1", "payments::payment-old-1"]

    deleted = cleanup_processed_messages(current_domain, retention_hours=24)

    assert deleted == 1
    assert _remaining_message_ids() == ["payments::payment-new-1"]


@pytest.mark.usefixtures("payments_ctx")
def test_cleanup_keeps_markers_inside_the_window():
    _write_marker("payments::payment-old-1", age_hours=48)
    _write_marker("payments::payment-new-1", age_hours=0)

    deleted = cleanup_processed_messages(current_domain, retention_hours=24 * 30)

    assert deleted == 0
    assert _remaining_message_ids() == ["payments::payment-new-1", "payments::payment-old-1"]


@pytest.mark.usefixtures("payments_ctx")
def test_cleanup_without_arguments_uses_the_retention_in_domain_toml():
    assert current_domain.config["consume_idempotency"]["cleanup"] == {"retention_hours": 168, "batch_size": 5000}
    _write_marker("payments::payment-old-1", age_hours=168 + 24)
    _write_marker("payments::payment-new-1", age_hours=168 - 24)

    deleted = cleanup_processed_messages(current_domain)

    assert deleted == 1
    assert _remaining_message_ids() == ["payments::payment-new-1"]


@pytest.mark.usefixtures("payments_ctx")
def test_cleanup_rejects_a_negative_window():
    _write_marker("payments::payment-new-1", age_hours=0)

    with pytest.raises(ValueError, match="cannot be negative"):
        cleanup_processed_messages(current_domain, retention_hours=-1)

    assert _remaining_message_ids() == ["payments::payment-new-1"]


@pytest.mark.usefixtures("payments_ctx")
def test_payments_has_idempotent_consumers():
    # cleanup_processed_messages returns 0 without touching any table when a
    # domain has no idempotent projector, so the cases above only mean
    # something while this holds.
    assert current_domain.has_idempotent_consumers


def _cleanup_target_domains() -> list[str]:
    """The contexts `make idempotency-cleanup` loops over."""
    makefile = (ROOT / "Makefile").read_text()
    recipe = re.search(r"^idempotency-cleanup:.*\n((?:\t.*\n)+)", makefile, re.MULTILINE)
    if recipe is None:
        pytest.fail("precondition: the Makefile has an idempotency-cleanup target")
    loop = re.search(r"for d in ([\w ]+); do", recipe.group(1))
    if loop is None:
        pytest.fail("precondition: the idempotency-cleanup recipe loops over the domains")
    return loop.group(1).split()


def test_cleanup_target_covers_every_domain_with_an_idempotent_projector(request):
    has_markers = {
        context: request.getfixturevalue(f"{context}_bed").domain.has_idempotent_consumers for context in CONTEXTS
    }
    if not any(has_markers.values()) or all(has_markers.values()):
        pytest.fail(f"precondition: some contexts have idempotent projectors and some do not: {has_markers}")

    assert sorted(_cleanup_target_domains()) == sorted(c for c, flagged in has_markers.items() if flagged)


def test_each_cleaned_domain_sets_its_retention_in_domain_toml():
    # The values equal Protean's defaults, so loading the domain config cannot
    # show whether the table is there. Read the file itself.
    domains = _cleanup_target_domains()
    if not domains:
        pytest.fail("precondition: the cleanup target lists at least one domain")

    tables = {d: tomllib.loads((SRC_DIR / d / "domain.toml").read_text()).get("consume_idempotency") for d in domains}

    assert tables == {d: {"cleanup": {"retention_hours": 168, "batch_size": 5000}} for d in domains}


def test_cleanup_command_exits_0_for_each_domain_in_the_target(request):
    """Run the command `make idempotency-cleanup` runs, for each of its domains.

    Under `--protean-env test` the child processes clean the real Postgres
    databases. Requesting each domain's bed first makes sure its marker table
    exists there.
    """
    domains = _cleanup_target_domains()
    for domain in domains:
        request.getfixturevalue(f"{domain}_bed")
    env = {**os.environ, "PROTEAN_LOG_LEVEL": "WARNING", "PYTHONPATH": str(SRC_DIR)}
    children = {
        domain: subprocess.Popen(
            [sys.executable, "-m", "protean", "idempotency", "cleanup", f"--domain={domain}.domain"],
            cwd=SRC_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for domain in domains
    }

    outputs = {domain: child.communicate(timeout=180)[0] for domain, child in children.items()}
    results = {domain: (children[domain].returncode, output) for domain, output in outputs.items()}

    failed = {domain: output for domain, (code, output) in results.items() if code != 0}
    assert failed == {}
    assert all("idempotency marker" in output for _, output in results.values()), results
