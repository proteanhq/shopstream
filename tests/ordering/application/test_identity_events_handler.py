"""Application tests for IdentityEventsSubscriber — Ordering reacts to Identity events.

Covers:
- on_account_suspended: creates SuspendedAccount projection record
- on_account_suspended duplicate: idempotent — only one record created
- on_account_reactivated: removes SuspendedAccount record
- on_account_reactivated when no record exists: no error
"""

from datetime import UTC, datetime

import pytest
from protean import current_domain

from ordering.order.identity_subscriber import IdentityEventsSubscriber
from ordering.projections.suspended_accounts import SuspendedAccount


def _build_message(event_type: str, data: dict) -> dict:
    return {"data": data, "metadata": {"headers": {"type": event_type}}}


class TestAccountSuspendedHandler:
    def test_creates_suspended_account_record(self):
        """AccountSuspended should create a SuspendedAccount projection record."""
        subscriber = IdentityEventsSubscriber()
        subscriber(
            _build_message(
                "Identity.AccountSuspended.v1",
                {
                    "customer_id": "cust-susp-001",
                    "reason": "Fraud detected",
                    "suspended_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        record = current_domain.repository_for(SuspendedAccount).get("cust-susp-001")
        assert record.customer_id == "cust-susp-001"
        assert record.reason == "Fraud detected"

    def test_duplicate_suspension_is_idempotent(self):
        """Calling on_account_suspended twice should not create duplicate records."""
        subscriber = IdentityEventsSubscriber()
        suspended_at = datetime.now(UTC).isoformat()

        subscriber(
            _build_message(
                "Identity.AccountSuspended.v1",
                {
                    "customer_id": "cust-susp-002",
                    "reason": "Policy violation",
                    "suspended_at": suspended_at,
                },
            )
        )
        subscriber(
            _build_message(
                "Identity.AccountSuspended.v1",
                {
                    "customer_id": "cust-susp-002",
                    "reason": "Policy violation again",
                    "suspended_at": suspended_at,
                },
            )
        )

        # Should still have exactly one record
        record = current_domain.repository_for(SuspendedAccount).get("cust-susp-002")
        assert record is not None
        # The original reason is preserved (not overwritten)
        assert record.reason == "Policy violation"


class TestAccountReactivatedHandler:
    def test_removes_suspended_account_record(self):
        """AccountReactivated should remove the SuspendedAccount projection record."""
        subscriber = IdentityEventsSubscriber()

        # First suspend the account
        subscriber(
            _build_message(
                "Identity.AccountSuspended.v1",
                {
                    "customer_id": "cust-react-001",
                    "reason": "Under review",
                    "suspended_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        # Verify record exists
        record = current_domain.repository_for(SuspendedAccount).get("cust-react-001")
        assert record is not None

        # Now reactivate
        subscriber(
            _build_message(
                "Identity.AccountReactivated.v1",
                {
                    "customer_id": "cust-react-001",
                    "reactivated_at": datetime.now(UTC).isoformat(),
                },
            )
        )

        # Record should be gone
        from protean.exceptions import ObjectNotFoundError

        with pytest.raises(ObjectNotFoundError):
            current_domain.repository_for(SuspendedAccount).get("cust-react-001")

    def test_reactivation_with_no_record_is_noop(self):
        """Reactivating an account that was never suspended should not error."""
        subscriber = IdentityEventsSubscriber()
        # Should not raise
        subscriber(
            _build_message(
                "Identity.AccountReactivated.v1",
                {
                    "customer_id": "cust-never-suspended",
                    "reactivated_at": datetime.now(UTC).isoformat(),
                },
            )
        )


class TestAccountSuspendedMockNotFound:
    """Mock-based test: ObjectNotFoundError in on_account_suspended triggers create path."""

    def test_creates_suspended_account_when_repo_get_raises(self):
        from unittest.mock import MagicMock, patch

        from protean.exceptions import ObjectNotFoundError

        subscriber = IdentityEventsSubscriber()
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "SuspendedAccount not found"})

        with patch("ordering.order.identity_subscriber.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            subscriber(
                _build_message(
                    "Identity.AccountSuspended.v1",
                    {
                        "customer_id": "cust-mock-001",
                        "reason": "Fraud detected",
                        "suspended_at": datetime.now(UTC).isoformat(),
                    },
                )
            )
            # repo.add should have been called to create the new record
            mock_repo.add.assert_called_once()
            created = mock_repo.add.call_args[0][0]
            assert created.customer_id == "cust-mock-001"
            assert created.reason == "Fraud detected"


class TestAccountReactivatedMockNotFound:
    """Mock-based test: ObjectNotFoundError in on_account_reactivated is silently caught."""

    def test_passes_when_repo_get_raises_not_found(self):
        from unittest.mock import MagicMock, patch

        from protean.exceptions import ObjectNotFoundError

        subscriber = IdentityEventsSubscriber()
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "SuspendedAccount not found"})

        with patch("ordering.order.identity_subscriber.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            # Should not raise
            subscriber(
                _build_message(
                    "Identity.AccountReactivated.v1",
                    {
                        "customer_id": "cust-mock-never",
                        "reactivated_at": datetime.now(UTC).isoformat(),
                    },
                )
            )
            # delete won't be reached since get() raised ObjectNotFoundError
            mock_repo.query.filter.assert_not_called()


class TestIgnoresUnrelatedEvents:
    def test_ignores_non_matching_identity_events(self):
        """Events on the identity stream that aren't handled should be ignored."""
        subscriber = IdentityEventsSubscriber()
        subscriber(
            _build_message(
                "Identity.ProfileUpdated.v1",
                {"customer_id": "cust-ignore"},
            )
        )
