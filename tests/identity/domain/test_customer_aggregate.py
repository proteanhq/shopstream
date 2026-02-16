import pytest
from identity.customer.customer import (
    Address,
    Customer,
    CustomerStatus,
    CustomerTier,
    Profile,
)
from identity.shared.email import EmailAddress
from identity.shared.phone import PhoneNumber
from protean.exceptions import ValidationError
from protean.utils import DomainObjects
from protean.utils.reflection import declared_fields


def test_customer_aggregate_element_type():
    assert Customer.element_type == DomainObjects.AGGREGATE


def test_customer_aggregate_has_defined_fields():
    assert all(
        field_name in declared_fields(Customer)
        for field_name in [
            "external_id",
            "email",
            "profile",
            "addresses",
            "status",
            "tier",
            "registered_at",
            "last_login_at",
        ]
    )


class TestCustomerConstruction:
    """Tests for Customer construction with new fields."""

    def test_minimal_customer(self):
        customer = Customer(
            external_id="CUST-001",
            email=EmailAddress(address="test@example.com"),
        )
        assert customer.external_id == "CUST-001"
        assert customer.email.address == "test@example.com"
        assert customer.status == CustomerStatus.ACTIVE.value
        assert customer.tier == CustomerTier.STANDARD.value
        assert customer.profile is None
        assert customer.registered_at is not None
        assert customer.last_login_at is None

    def test_customer_with_profile(self):
        customer = Customer(
            external_id="CUST-002",
            email=EmailAddress(address="jane@example.com"),
            profile=Profile(first_name="Jane", last_name="Doe"),
        )
        assert customer.profile.first_name == "Jane"
        assert customer.profile.last_name == "Doe"

    def test_customer_with_profile_and_phone(self):
        customer = Customer(
            external_id="CUST-003",
            email=EmailAddress(address="john@example.com"),
            profile=Profile(
                first_name="John",
                last_name="Smith",
                phone=PhoneNumber(number="+1-555-123-4567"),
            ),
        )
        assert customer.profile.phone.number == "+1-555-123-4567"

    def test_customer_with_addresses(self):
        customer = Customer(
            external_id="CUST-004",
            email=EmailAddress(address="alice@example.com"),
        )
        customer.add_addresses(
            Address(
                street="123 Main St",
                city="Springfield",
                postal_code="62701",
                country="US",
                is_default=True,
            )
        )
        assert len(customer.addresses) == 1
        assert customer.addresses[0].street == "123 Main St"


class TestCustomerStatus:
    """Tests for Customer status field."""

    def test_status_defaults_to_active(self):
        customer = Customer(
            external_id="CUST-001",
            email=EmailAddress(address="test@example.com"),
        )
        assert customer.status == CustomerStatus.ACTIVE.value

    def test_status_can_be_set_to_active(self):
        customer = Customer(
            external_id="CUST-001",
            email=EmailAddress(address="test@example.com"),
            status=CustomerStatus.ACTIVE.value,
        )
        assert customer.status == CustomerStatus.ACTIVE.value

    def test_status_can_be_set_to_suspended(self):
        customer = Customer(
            external_id="CUST-001",
            email=EmailAddress(address="test@example.com"),
            status=CustomerStatus.SUSPENDED.value,
        )
        assert customer.status == CustomerStatus.SUSPENDED.value

    def test_status_can_be_set_to_closed(self):
        customer = Customer(
            external_id="CUST-001",
            email=EmailAddress(address="test@example.com"),
            status=CustomerStatus.CLOSED.value,
        )
        assert customer.status == CustomerStatus.CLOSED.value

    def test_status_rejects_invalid_value(self):
        with pytest.raises(ValidationError):
            Customer(
                external_id="CUST-001",
                email=EmailAddress(address="test@example.com"),
                status="Invalid",
            )


class TestCustomerTier:
    """Tests for Customer tier field."""

    def test_tier_defaults_to_standard(self):
        customer = Customer(
            external_id="CUST-001",
            email=EmailAddress(address="test@example.com"),
        )
        assert customer.tier == CustomerTier.STANDARD.value

    def test_tier_can_be_set_to_standard(self):
        customer = Customer(
            external_id="CUST-001",
            email=EmailAddress(address="test@example.com"),
            tier=CustomerTier.STANDARD.value,
        )
        assert customer.tier == CustomerTier.STANDARD.value

    def test_tier_can_be_set_to_silver(self):
        customer = Customer(
            external_id="CUST-001",
            email=EmailAddress(address="test@example.com"),
            tier=CustomerTier.SILVER.value,
        )
        assert customer.tier == CustomerTier.SILVER.value

    def test_tier_can_be_set_to_gold(self):
        customer = Customer(
            external_id="CUST-001",
            email=EmailAddress(address="test@example.com"),
            tier=CustomerTier.GOLD.value,
        )
        assert customer.tier == CustomerTier.GOLD.value

    def test_tier_can_be_set_to_platinum(self):
        customer = Customer(
            external_id="CUST-001",
            email=EmailAddress(address="test@example.com"),
            tier=CustomerTier.PLATINUM.value,
        )
        assert customer.tier == CustomerTier.PLATINUM.value

    def test_tier_rejects_invalid_value(self):
        with pytest.raises(ValidationError):
            Customer(
                external_id="CUST-001",
                email=EmailAddress(address="test@example.com"),
                tier="Diamond",
            )
