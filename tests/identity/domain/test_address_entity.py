import pytest
from identity.customer.customer import Address, AddressLabel, GeoCoordinates
from protean.exceptions import ValidationError
from protean.utils import DomainObjects
from protean.utils.reflection import declared_fields


def test_address_element_type():
    assert Address.element_type == DomainObjects.ENTITY


def test_address_has_defined_fields():
    assert all(
        field_name in declared_fields(Address)
        for field_name in [
            "label",
            "street",
            "city",
            "state",
            "postal_code",
            "country",
            "is_default",
        ]
    )


class TestAddressConstruction:
    def test_minimal_address(self):
        addr = Address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        assert addr.street == "123 Main St"
        assert addr.city == "Springfield"
        assert addr.postal_code == "62701"
        assert addr.country == "US"

    def test_defaults(self):
        addr = Address(
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        assert addr.label == AddressLabel.HOME.value
        assert addr.is_default is False
        assert addr.state is None
        assert addr.geo_coordinates is None

    def test_full_address(self):
        addr = Address(
            label=AddressLabel.WORK.value,
            street="456 Oak Ave",
            city="Chicago",
            state="Illinois",
            postal_code="60601",
            country="US",
            is_default=True,
            geo_coordinates=GeoCoordinates(latitude=41.8781, longitude=-87.6298),
        )
        assert addr.label == AddressLabel.WORK.value
        assert addr.street == "456 Oak Ave"
        assert addr.city == "Chicago"
        assert addr.state == "Illinois"
        assert addr.postal_code == "60601"
        assert addr.country == "US"
        assert addr.is_default is True
        assert addr.geo_coordinates.latitude == 41.8781
        assert addr.geo_coordinates.longitude == -87.6298


class TestAddressRequired:
    def test_requires_street(self):
        with pytest.raises(ValidationError):
            Address(city="Springfield", postal_code="62701", country="US")

    def test_requires_city(self):
        with pytest.raises(ValidationError):
            Address(street="123 Main St", postal_code="62701", country="US")

    def test_requires_postal_code(self):
        with pytest.raises(ValidationError):
            Address(street="123 Main St", city="Springfield", country="US")

    def test_requires_country(self):
        with pytest.raises(ValidationError):
            Address(street="123 Main St", city="Springfield", postal_code="62701")


class TestAddressLabel:
    def test_label_home(self):
        addr = Address(
            label=AddressLabel.HOME.value,
            street="123 Main St",
            city="Springfield",
            postal_code="62701",
            country="US",
        )
        assert addr.label == AddressLabel.HOME.value

    def test_label_work(self):
        addr = Address(
            label=AddressLabel.WORK.value,
            street="456 Office Blvd",
            city="Chicago",
            postal_code="60601",
            country="US",
        )
        assert addr.label == AddressLabel.WORK.value

    def test_label_other(self):
        addr = Address(
            label=AddressLabel.OTHER.value,
            street="789 Elm St",
            city="Denver",
            postal_code="80201",
            country="US",
        )
        assert addr.label == AddressLabel.OTHER.value

    def test_label_rejects_invalid(self):
        with pytest.raises(ValidationError):
            Address(
                label="Invalid",
                street="123 Main St",
                city="Springfield",
                postal_code="62701",
                country="US",
            )


class TestAddressMaxLength:
    def test_street_max_length(self):
        with pytest.raises(ValidationError):
            Address(
                street="S" * 256,
                city="Springfield",
                postal_code="62701",
                country="US",
            )

    def test_city_max_length(self):
        with pytest.raises(ValidationError):
            Address(
                street="123 Main St",
                city="C" * 101,
                postal_code="62701",
                country="US",
            )

    def test_postal_code_max_length(self):
        with pytest.raises(ValidationError):
            Address(
                street="123 Main St",
                city="Springfield",
                postal_code="P" * 21,
                country="US",
            )

    def test_country_max_length(self):
        with pytest.raises(ValidationError):
            Address(
                street="123 Main St",
                city="Springfield",
                postal_code="62701",
                country="C" * 101,
            )
