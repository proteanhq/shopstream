"""Tests for Customer domain events."""

from datetime import datetime

from identity.customer.events import (
    AccountClosed,
    AccountReactivated,
    AccountSuspended,
    AddressAdded,
    AddressRemoved,
    AddressUpdated,
    CustomerRegistered,
    DefaultAddressChanged,
    ProfileUpdated,
    TierUpgraded,
)
from protean.utils import DomainObjects


class TestCustomerRegistered:
    def test_element_type(self):
        assert CustomerRegistered.element_type == DomainObjects.EVENT

    def test_construction(self):
        now = datetime.now()
        event = CustomerRegistered(
            customer_id="cust-123",
            external_id="EXT-001",
            email="john@example.com",
            first_name="John",
            last_name="Doe",
            registered_at=now,
        )
        assert event.customer_id == "cust-123"
        assert event.external_id == "EXT-001"
        assert event.email == "john@example.com"
        assert event.first_name == "John"
        assert event.last_name == "Doe"
        assert event.registered_at == now

    def test_version(self):
        assert CustomerRegistered.__version__ == "v1"


class TestProfileUpdated:
    def test_element_type(self):
        assert ProfileUpdated.element_type == DomainObjects.EVENT

    def test_construction(self):
        event = ProfileUpdated(
            customer_id="cust-123",
            first_name="Jane",
            last_name="Smith",
            phone="+1-555-123-4567",
            date_of_birth="1990-05-15",
        )
        assert event.customer_id == "cust-123"
        assert event.first_name == "Jane"
        assert event.last_name == "Smith"
        assert event.phone == "+1-555-123-4567"
        assert event.date_of_birth == "1990-05-15"

    def test_optional_fields(self):
        event = ProfileUpdated(
            customer_id="cust-123",
            first_name="Jane",
            last_name="Smith",
        )
        assert event.phone is None
        assert event.date_of_birth is None


class TestAddressAdded:
    def test_element_type(self):
        assert AddressAdded.element_type == DomainObjects.EVENT

    def test_construction(self):
        event = AddressAdded(
            customer_id="cust-123",
            address_id="addr-456",
            label="Home",
            street="123 Main St",
            city="Springfield",
            state="IL",
            postal_code="62701",
            country="US",
            is_default="True",
        )
        assert event.customer_id == "cust-123"
        assert event.address_id == "addr-456"
        assert event.label == "Home"
        assert event.street == "123 Main St"
        assert event.city == "Springfield"
        assert event.state == "IL"
        assert event.postal_code == "62701"
        assert event.country == "US"
        assert event.is_default == "True"


class TestAddressUpdated:
    def test_element_type(self):
        assert AddressUpdated.element_type == DomainObjects.EVENT

    def test_construction(self):
        event = AddressUpdated(
            customer_id="cust-123",
            address_id="addr-456",
            street="456 Oak Ave",
            city="Chicago",
        )
        assert event.customer_id == "cust-123"
        assert event.address_id == "addr-456"
        assert event.street == "456 Oak Ave"
        assert event.city == "Chicago"


class TestAddressRemoved:
    def test_element_type(self):
        assert AddressRemoved.element_type == DomainObjects.EVENT

    def test_construction(self):
        event = AddressRemoved(
            customer_id="cust-123",
            address_id="addr-456",
        )
        assert event.customer_id == "cust-123"
        assert event.address_id == "addr-456"


class TestDefaultAddressChanged:
    def test_element_type(self):
        assert DefaultAddressChanged.element_type == DomainObjects.EVENT

    def test_construction(self):
        event = DefaultAddressChanged(
            customer_id="cust-123",
            address_id="addr-789",
            previous_default_address_id="addr-456",
        )
        assert event.customer_id == "cust-123"
        assert event.address_id == "addr-789"
        assert event.previous_default_address_id == "addr-456"

    def test_optional_previous(self):
        event = DefaultAddressChanged(
            customer_id="cust-123",
            address_id="addr-789",
        )
        assert event.previous_default_address_id is None


class TestAccountSuspended:
    def test_element_type(self):
        assert AccountSuspended.element_type == DomainObjects.EVENT

    def test_construction(self):
        now = datetime.now()
        event = AccountSuspended(
            customer_id="cust-123",
            reason="Fraudulent activity",
            suspended_at=now,
        )
        assert event.customer_id == "cust-123"
        assert event.reason == "Fraudulent activity"
        assert event.suspended_at == now


class TestAccountReactivated:
    def test_element_type(self):
        assert AccountReactivated.element_type == DomainObjects.EVENT

    def test_construction(self):
        now = datetime.now()
        event = AccountReactivated(
            customer_id="cust-123",
            reactivated_at=now,
        )
        assert event.customer_id == "cust-123"
        assert event.reactivated_at == now


class TestAccountClosed:
    def test_element_type(self):
        assert AccountClosed.element_type == DomainObjects.EVENT

    def test_construction(self):
        now = datetime.now()
        event = AccountClosed(
            customer_id="cust-123",
            closed_at=now,
        )
        assert event.customer_id == "cust-123"
        assert event.closed_at == now


class TestTierUpgraded:
    def test_element_type(self):
        assert TierUpgraded.element_type == DomainObjects.EVENT

    def test_construction(self):
        now = datetime.now()
        event = TierUpgraded(
            customer_id="cust-123",
            previous_tier="Standard",
            new_tier="Silver",
            upgraded_at=now,
        )
        assert event.customer_id == "cust-123"
        assert event.previous_tier == "Standard"
        assert event.new_tier == "Silver"
        assert event.upgraded_at == now
