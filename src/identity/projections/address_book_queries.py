"""Queries for the AddressBook projection."""

from protean import read
from protean.fields import Identifier
from protean.utils.globals import current_domain

from identity.domain import identity
from identity.projections.address_book import AddressBook


@identity.query(part_of=AddressBook)
class GetAddressBook:
    customer_id = Identifier(required=True)


@identity.query_handler(part_of=AddressBook)
class AddressBookQueryHandler:
    @read(GetAddressBook)
    def get_address_book(self, query):
        return current_domain.view_for(AddressBook).get(query.customer_id)
