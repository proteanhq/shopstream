from identity.model.customer.aggregate import Customer
from protean.utils import DomainObjects
from protean.utils.reflection import declared_fields


def test_customer_aggregate_element_type():
    assert Customer.element_type == DomainObjects.AGGREGATE


def test_customer_aggregate_has_defined_fields():
    assert all(field_name in declared_fields(Customer) for field_name in ["external_id", "email"])
