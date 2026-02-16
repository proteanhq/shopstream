"""Tests for Customer command DTOs."""

import pytest
from identity.customer.account import CloseAccount, ReactivateAccount, SuspendAccount
from identity.customer.addresses import (
    AddAddress,
    RemoveAddress,
    SetDefaultAddress,
    UpdateAddress,
)
from identity.customer.profile import UpdateProfile
from identity.customer.registration import RegisterCustomer
from identity.customer.tier import UpgradeTier
from protean.exceptions import ValidationError
from protean.utils import DomainObjects


class TestRegisterCustomer:
    def test_element_type(self):
        assert RegisterCustomer.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = RegisterCustomer(
            external_id="EXT-001",
            email="john@example.com",
            first_name="John",
            last_name="Doe",
        )
        assert cmd.external_id == "EXT-001"
        assert cmd.email == "john@example.com"
        assert cmd.first_name == "John"
        assert cmd.last_name == "Doe"

    def test_optional_fields(self):
        cmd = RegisterCustomer(
            external_id="EXT-001",
            email="john@example.com",
            first_name="John",
            last_name="Doe",
            phone="+1-555-123-4567",
            date_of_birth="1990-05-15",
        )
        assert cmd.phone == "+1-555-123-4567"
        assert cmd.date_of_birth == "1990-05-15"

    def test_requires_external_id(self):
        with pytest.raises(ValidationError):
            RegisterCustomer(
                email="john@example.com",
                first_name="John",
                last_name="Doe",
            )

    def test_requires_email(self):
        with pytest.raises(ValidationError):
            RegisterCustomer(
                external_id="EXT-001",
                first_name="John",
                last_name="Doe",
            )

    def test_requires_first_name(self):
        with pytest.raises(ValidationError):
            RegisterCustomer(
                external_id="EXT-001",
                email="john@example.com",
                last_name="Doe",
            )

    def test_requires_last_name(self):
        with pytest.raises(ValidationError):
            RegisterCustomer(
                external_id="EXT-001",
                email="john@example.com",
                first_name="John",
            )


class TestUpdateProfile:
    def test_element_type(self):
        assert UpdateProfile.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = UpdateProfile(
            customer_id="cust-123",
            first_name="Jane",
            last_name="Smith",
        )
        assert cmd.customer_id == "cust-123"
        assert cmd.first_name == "Jane"
        assert cmd.last_name == "Smith"

    def test_requires_customer_id(self):
        with pytest.raises(ValidationError):
            UpdateProfile(first_name="Jane", last_name="Smith")


class TestAddAddress:
    def test_element_type(self):
        assert AddAddress.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = AddAddress(
            customer_id="cust-123",
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        assert cmd.customer_id == "cust-123"
        assert cmd.street == "123 Main St"

    def test_requires_customer_id(self):
        with pytest.raises(ValidationError):
            AddAddress(
                street="123 Main St",
                city="Springfield",
                postal_code="62701",
                country="US",
            )


class TestUpdateAddress:
    def test_element_type(self):
        assert UpdateAddress.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = UpdateAddress(
            customer_id="cust-123",
            address_id="addr-456",
            street="456 Elm St",
        )
        assert cmd.customer_id == "cust-123"
        assert cmd.address_id == "addr-456"
        assert cmd.street == "456 Elm St"


class TestRemoveAddress:
    def test_element_type(self):
        assert RemoveAddress.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = RemoveAddress(
            customer_id="cust-123",
            address_id="addr-456",
        )
        assert cmd.customer_id == "cust-123"
        assert cmd.address_id == "addr-456"


class TestSetDefaultAddress:
    def test_element_type(self):
        assert SetDefaultAddress.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = SetDefaultAddress(
            customer_id="cust-123",
            address_id="addr-456",
        )
        assert cmd.customer_id == "cust-123"
        assert cmd.address_id == "addr-456"


class TestSuspendAccount:
    def test_element_type(self):
        assert SuspendAccount.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = SuspendAccount(
            customer_id="cust-123",
            reason="Fraudulent activity",
        )
        assert cmd.customer_id == "cust-123"
        assert cmd.reason == "Fraudulent activity"

    def test_requires_reason(self):
        with pytest.raises(ValidationError):
            SuspendAccount(customer_id="cust-123")


class TestReactivateAccount:
    def test_element_type(self):
        assert ReactivateAccount.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = ReactivateAccount(customer_id="cust-123")
        assert cmd.customer_id == "cust-123"


class TestCloseAccount:
    def test_element_type(self):
        assert CloseAccount.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = CloseAccount(customer_id="cust-123")
        assert cmd.customer_id == "cust-123"


class TestUpgradeTier:
    def test_element_type(self):
        assert UpgradeTier.element_type == DomainObjects.COMMAND

    def test_construction(self):
        cmd = UpgradeTier(
            customer_id="cust-123",
            new_tier="Silver",
        )
        assert cmd.customer_id == "cust-123"
        assert cmd.new_tier == "Silver"

    def test_requires_new_tier(self):
        with pytest.raises(ValidationError):
            UpgradeTier(customer_id="cust-123")
