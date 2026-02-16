"""Address book — where do our customers live?"""

import json

from protean.core.projector import on
from protean.fields import Identifier, Text
from protean.utils.globals import current_domain

from identity.customer.customer import Customer
from identity.customer.events import (
    AddressAdded,
    AddressRemoved,
    AddressUpdated,
    DefaultAddressChanged,
)
from identity.domain import identity


@identity.projection
class AddressBook:
    customer_id: Identifier(identifier=True, required=True)
    addresses: Text()


@identity.projector(projector_for=AddressBook, aggregates=[Customer])
class AddressBookProjector:
    @on(AddressAdded)
    def on_address_added(self, event):
        repo = current_domain.repository_for(AddressBook)
        try:
            book = repo.get(event.customer_id)
            entries = json.loads(book.addresses) if book.addresses else []
        except Exception:
            book = AddressBook(
                customer_id=event.customer_id,
                addresses="[]",
            )
            entries = []

        entries.append(
            {
                "address_id": event.address_id,
                "label": event.label,
                "street": event.street,
                "city": event.city,
                "state": event.state,
                "postal_code": event.postal_code,
                "country": event.country,
                "is_default": event.is_default,
            }
        )
        book.addresses = json.dumps(entries)
        repo.add(book)

    @on(AddressUpdated)
    def on_address_updated(self, event):
        repo = current_domain.repository_for(AddressBook)
        book = repo.get(event.customer_id)
        entries = json.loads(book.addresses) if book.addresses else []

        for entry in entries:
            if entry["address_id"] == event.address_id:
                for field in ("label", "street", "city", "state", "postal_code", "country"):
                    value = getattr(event, field, None)
                    if value is not None:
                        entry[field] = value
                break

        book.addresses = json.dumps(entries)
        repo.add(book)

    @on(AddressRemoved)
    def on_address_removed(self, event):
        repo = current_domain.repository_for(AddressBook)
        book = repo.get(event.customer_id)
        entries = json.loads(book.addresses) if book.addresses else []

        entries = [e for e in entries if e["address_id"] != event.address_id]
        book.addresses = json.dumps(entries)
        repo.add(book)

    @on(DefaultAddressChanged)
    def on_default_address_changed(self, event):
        repo = current_domain.repository_for(AddressBook)
        book = repo.get(event.customer_id)
        entries = json.loads(book.addresses) if book.addresses else []

        for entry in entries:
            entry["is_default"] = str(entry["address_id"] == event.address_id)

        book.addresses = json.dumps(entries)
        repo.add(book)
