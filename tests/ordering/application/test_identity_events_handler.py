"""Application tests for IdentityOrderEventHandler — Ordering reacts to Identity events.

Covers:
- on_account_suspended: creates SuspendedAccount projection record
- on_account_suspended duplicate: idempotent — only one record created
- on_account_reactivated: removes SuspendedAccount record
- on_account_reactivated when no record exists: no error
"""

from datetime import UTC, datetime

import pytest
from ordering.order.identity_events import IdentityOrderEventHandler
from ordering.projections.suspended_accounts import SuspendedAccount
from protean import current_domain
from shared.events.identity import AccountReactivated, AccountSuspended


class TestAccountSuspendedHandler:
    def test_creates_suspended_account_record(self):
        """AccountSuspended should create a SuspendedAccount projection record."""
        handler = IdentityOrderEventHandler()
        handler.on_account_suspended(
            AccountSuspended(
                customer_id="cust-susp-001",
                reason="Fraud detected",
                suspended_at=datetime.now(UTC),
            )
        )

        record = current_domain.repository_for(SuspendedAccount).get("cust-susp-001")
        assert record.customer_id == "cust-susp-001"
        assert record.reason == "Fraud detected"

    def test_duplicate_suspension_is_idempotent(self):
        """Calling on_account_suspended twice should not create duplicate records."""
        handler = IdentityOrderEventHandler()
        suspended_at = datetime.now(UTC)

        handler.on_account_suspended(
            AccountSuspended(
                customer_id="cust-susp-002",
                reason="Policy violation",
                suspended_at=suspended_at,
            )
        )
        handler.on_account_suspended(
            AccountSuspended(
                customer_id="cust-susp-002",
                reason="Policy violation again",
                suspended_at=suspended_at,
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
        handler = IdentityOrderEventHandler()

        # First suspend the account
        handler.on_account_suspended(
            AccountSuspended(
                customer_id="cust-react-001",
                reason="Under review",
                suspended_at=datetime.now(UTC),
            )
        )

        # Verify record exists
        record = current_domain.repository_for(SuspendedAccount).get("cust-react-001")
        assert record is not None

        # Now reactivate
        handler.on_account_reactivated(
            AccountReactivated(
                customer_id="cust-react-001",
                reactivated_at=datetime.now(UTC),
            )
        )

        # Record should be gone
        from protean.exceptions import ObjectNotFoundError

        with pytest.raises(ObjectNotFoundError):
            current_domain.repository_for(SuspendedAccount).get("cust-react-001")

    def test_reactivation_with_no_record_is_noop(self):
        """Reactivating an account that was never suspended should not error."""
        handler = IdentityOrderEventHandler()
        # Should not raise
        handler.on_account_reactivated(
            AccountReactivated(
                customer_id="cust-never-suspended",
                reactivated_at=datetime.now(UTC),
            )
        )


class TestAccountSuspendedMockNotFound:
    """Mock-based test: ObjectNotFoundError in on_account_suspended triggers create path."""

    def test_creates_suspended_account_when_repo_get_raises(self):
        from unittest.mock import MagicMock, patch

        from protean.exceptions import ObjectNotFoundError

        handler = IdentityOrderEventHandler()
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "SuspendedAccount not found"})

        with patch("ordering.order.identity_events.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            handler.on_account_suspended(
                AccountSuspended(
                    customer_id="cust-mock-001",
                    reason="Fraud detected",
                    suspended_at=datetime.now(UTC),
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

        handler = IdentityOrderEventHandler()
        mock_repo = MagicMock()
        mock_repo.get.side_effect = ObjectNotFoundError({"_entity": "SuspendedAccount not found"})

        with patch("ordering.order.identity_events.current_domain") as mock_domain:
            mock_domain.repository_for = MagicMock(return_value=mock_repo)
            # Should not raise
            handler.on_account_reactivated(
                AccountReactivated(
                    customer_id="cust-mock-never",
                    reactivated_at=datetime.now(UTC),
                )
            )
            # _dao.delete should NOT have been called since get raised
            mock_repo._dao.delete.assert_not_called()
