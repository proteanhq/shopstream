"""Application tests for account lifecycle via domain.process()."""

import pytest
from identity.customer.account import CloseAccount, ReactivateAccount, SuspendAccount
from identity.customer.customer import Customer, CustomerStatus
from identity.customer.registration import RegisterCustomer
from protean import current_domain
from protean.exceptions import ValidationError


class TestAccountLifecycleFlow:
    def _register_customer(self):
        command = RegisterCustomer(
            external_id="EXT-001",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
        )
        return current_domain.process(command, asynchronous=False)

    def test_suspend_active_account(self):
        customer_id = self._register_customer()

        current_domain.process(
            SuspendAccount(customer_id=customer_id, reason="Fraud"),
            asynchronous=False,
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.status == CustomerStatus.SUSPENDED.value

    def test_reactivate_suspended_account(self):
        customer_id = self._register_customer()

        current_domain.process(
            SuspendAccount(customer_id=customer_id, reason="Review"),
            asynchronous=False,
        )
        current_domain.process(
            ReactivateAccount(customer_id=customer_id),
            asynchronous=False,
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.status == CustomerStatus.ACTIVE.value

    def test_close_account(self):
        customer_id = self._register_customer()

        current_domain.process(
            CloseAccount(customer_id=customer_id),
            asynchronous=False,
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.status == CustomerStatus.CLOSED.value

    def test_cannot_suspend_closed_account(self):
        customer_id = self._register_customer()

        current_domain.process(
            CloseAccount(customer_id=customer_id),
            asynchronous=False,
        )

        with pytest.raises(ValidationError):
            current_domain.process(
                SuspendAccount(customer_id=customer_id, reason="Test"),
                asynchronous=False,
            )

    def test_cannot_reactivate_active_account(self):
        customer_id = self._register_customer()

        with pytest.raises(ValidationError):
            current_domain.process(
                ReactivateAccount(customer_id=customer_id),
                asynchronous=False,
            )

    def test_full_lifecycle(self):
        customer_id = self._register_customer()

        # Active -> Suspended
        current_domain.process(
            SuspendAccount(customer_id=customer_id, reason="Review"),
            asynchronous=False,
        )

        # Suspended -> Active
        current_domain.process(
            ReactivateAccount(customer_id=customer_id),
            asynchronous=False,
        )

        # Active -> Closed
        current_domain.process(
            CloseAccount(customer_id=customer_id),
            asynchronous=False,
        )

        customer = current_domain.repository_for(Customer).get(customer_id)
        assert customer.status == CustomerStatus.CLOSED.value
