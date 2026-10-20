"""Oracle: `protean idempotency cleanup` prunes old processed-message markers.

An idempotent projector writes one marker per (message id, handler) it has
applied. A marker only matters while its event can still be redelivered, so
`make idempotency-cleanup` runs `cleanup_processed_messages` for each domain to
delete markers older than `[consume_idempotency.cleanup] retention_hours`.

Each case writes markers with a known `processed_at`, runs the cleanup, and
checks which markers are left. The timestamps sit a full day or more away from
the cutoff, so the result does not depend on how long the test takes.
"""

from datetime import UTC, datetime, timedelta

import pytest
from protean.utils.consume_idempotency import ProcessedMessage, cleanup_processed_messages
from protean.utils.globals import current_domain


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
