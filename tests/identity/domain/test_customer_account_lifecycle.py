"""Tests for Customer account lifecycle: suspend, reactivate, close."""

import pytest
from identity.customer.customer import Customer, CustomerStatus
from identity.customer.events import AccountClosed, AccountReactivated, AccountSuspended
from protean.exceptions import ValidationError


def _make_active_customer():
    return Customer.register(
        external_id="EXT-001",
        email="test@example.com",
        first_name="John",
        last_name="Doe",
    )


class TestSuspend:
    def test_suspend_active_account(self):
        customer = _make_active_customer()
        customer._events.clear()

        customer.suspend(reason="Fraudulent activity")
        assert customer.status == CustomerStatus.SUSPENDED.value

    def test_suspend_raises_event(self):
        customer = _make_active_customer()
        customer._events.clear()

        customer.suspend(reason="Fraudulent activity")
        assert len(customer._events) == 1
        event = customer._events[0]
        assert isinstance(event, AccountSuspended)
        assert event.customer_id == str(customer.id)
        assert event.reason == "Fraudulent activity"
        assert event.suspended_at is not None

    def test_cannot_suspend_suspended_account(self):
        customer = _make_active_customer()
        customer.suspend(reason="First suspension")
        with pytest.raises(ValidationError) as exc:
            customer.suspend(reason="Second suspension")
        assert "Only active accounts can be suspended" in str(exc.value)

    def test_cannot_suspend_closed_account(self):
        customer = _make_active_customer()
        customer.close()
        with pytest.raises(ValidationError) as exc:
            customer.suspend(reason="Suspend closed")
        assert "Only active accounts can be suspended" in str(exc.value)


class TestReactivate:
    def test_reactivate_suspended_account(self):
        customer = _make_active_customer()
        customer.suspend(reason="Test")
        customer._events.clear()

        customer.reactivate()
        assert customer.status == CustomerStatus.ACTIVE.value

    def test_reactivate_raises_event(self):
        customer = _make_active_customer()
        customer.suspend(reason="Test")
        customer._events.clear()

        customer.reactivate()
        assert len(customer._events) == 1
        event = customer._events[0]
        assert isinstance(event, AccountReactivated)
        assert event.customer_id == str(customer.id)
        assert event.reactivated_at is not None

    def test_cannot_reactivate_active_account(self):
        customer = _make_active_customer()
        with pytest.raises(ValidationError) as exc:
            customer.reactivate()
        assert "Only suspended accounts can be reactivated" in str(exc.value)

    def test_cannot_reactivate_closed_account(self):
        customer = _make_active_customer()
        customer.close()
        with pytest.raises(ValidationError) as exc:
            customer.reactivate()
        assert "Only suspended accounts can be reactivated" in str(exc.value)


class TestClose:
    def test_close_active_account(self):
        customer = _make_active_customer()
        customer._events.clear()

        customer.close()
        assert customer.status == CustomerStatus.CLOSED.value

    def test_close_suspended_account(self):
        customer = _make_active_customer()
        customer.suspend(reason="Test")
        customer._events.clear()

        customer.close()
        assert customer.status == CustomerStatus.CLOSED.value

    def test_close_raises_event(self):
        customer = _make_active_customer()
        customer._events.clear()

        customer.close()
        assert len(customer._events) == 1
        event = customer._events[0]
        assert isinstance(event, AccountClosed)
        assert event.customer_id == str(customer.id)
        assert event.closed_at is not None

    def test_cannot_close_already_closed_account(self):
        customer = _make_active_customer()
        customer.close()
        with pytest.raises(ValidationError) as exc:
            customer.close()
        assert "Account is already closed" in str(exc.value)


class TestFullLifecycle:
    def test_active_to_suspended_to_reactivated(self):
        customer = _make_active_customer()
        assert customer.status == CustomerStatus.ACTIVE.value

        customer.suspend(reason="Review")
        assert customer.status == CustomerStatus.SUSPENDED.value

        customer.reactivate()
        assert customer.status == CustomerStatus.ACTIVE.value

    def test_active_to_suspended_to_closed(self):
        customer = _make_active_customer()
        customer.suspend(reason="Review")
        customer.close()
        assert customer.status == CustomerStatus.CLOSED.value

    def test_active_to_closed(self):
        customer = _make_active_customer()
        customer.close()
        assert customer.status == CustomerStatus.CLOSED.value
