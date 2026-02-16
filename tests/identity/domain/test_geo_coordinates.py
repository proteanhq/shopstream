import pytest
from identity.customer.customer import GeoCoordinates
from protean.exceptions import ValidationError
from protean.utils import DomainObjects


def test_geo_coordinates_element_type():
    assert GeoCoordinates.element_type == DomainObjects.VALUE_OBJECT


def test_geo_coordinates_requires_latitude_and_longitude():
    with pytest.raises(ValidationError):
        GeoCoordinates()


def test_geo_coordinates_requires_latitude():
    with pytest.raises(ValidationError):
        GeoCoordinates(longitude=0.0)


def test_geo_coordinates_requires_longitude():
    with pytest.raises(ValidationError):
        GeoCoordinates(latitude=0.0)


class TestValidCoordinates:
    def test_origin(self):
        geo = GeoCoordinates(latitude=0.0, longitude=0.0)
        assert geo.latitude == 0.0
        assert geo.longitude == 0.0

    def test_positive_values(self):
        geo = GeoCoordinates(latitude=40.7128, longitude=-74.0060)
        assert geo.latitude == 40.7128
        assert geo.longitude == -74.0060

    def test_max_latitude(self):
        geo = GeoCoordinates(latitude=90.0, longitude=0.0)
        assert geo.latitude == 90.0

    def test_min_latitude(self):
        geo = GeoCoordinates(latitude=-90.0, longitude=0.0)
        assert geo.latitude == -90.0

    def test_max_longitude(self):
        geo = GeoCoordinates(latitude=0.0, longitude=180.0)
        assert geo.longitude == 180.0

    def test_min_longitude(self):
        geo = GeoCoordinates(latitude=0.0, longitude=-180.0)
        assert geo.longitude == -180.0

    def test_extreme_corners(self):
        geo = GeoCoordinates(latitude=90.0, longitude=180.0)
        assert geo.latitude == 90.0
        assert geo.longitude == 180.0

        geo2 = GeoCoordinates(latitude=-90.0, longitude=-180.0)
        assert geo2.latitude == -90.0
        assert geo2.longitude == -180.0


class TestInvalidCoordinates:
    def test_latitude_too_high(self):
        with pytest.raises(ValidationError):
            GeoCoordinates(latitude=90.1, longitude=0.0)

    def test_latitude_too_low(self):
        with pytest.raises(ValidationError):
            GeoCoordinates(latitude=-90.1, longitude=0.0)

    def test_longitude_too_high(self):
        with pytest.raises(ValidationError):
            GeoCoordinates(latitude=0.0, longitude=180.1)

    def test_longitude_too_low(self):
        with pytest.raises(ValidationError):
            GeoCoordinates(latitude=0.0, longitude=-180.1)
