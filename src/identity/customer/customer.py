"""Customer aggregate root with Address entity, Profile and GeoCoordinates value objects."""

from datetime import date, datetime
from enum import Enum
from typing import Final

from protean import atomic_change, invariant
from protean.exceptions import ValidationError
from protean.fields import Boolean, Date, DateTime, Float, HasMany, Status, String, ValueObject

from identity.domain import identity
from identity.shared.email import EmailAddress
from identity.shared.phone import PhoneNumber

# Tier ordering for upgrade validation
_TIER_ORDER = ["Standard", "Silver", "Gold", "Platinum"]


class _Unset(Enum):
    """Sentinel type for distinguishing "not provided" from None in partial updates.

    A single-member enum (rather than a bare ``object()``) lets type checkers
    narrow ``x is not _UNSET`` to the real argument type.
    """

    UNSET = "UNSET"


_UNSET: Final = _Unset.UNSET


class CustomerStatus(Enum):
    """Enumeration of customer account statuses."""

    ACTIVE = "Active"
    SUSPENDED = "Suspended"
    CLOSED = "Closed"


class CustomerTier(Enum):
    """Enumeration of customer loyalty tiers."""

    STANDARD = "Standard"
    SILVER = "Silver"
    GOLD = "Gold"
    PLATINUM = "Platinum"


class AddressLabel(Enum):
    """Enumeration of address types."""

    HOME = "Home"
    WORK = "Work"
    OTHER = "Other"


@identity.value_object(part_of="Customer")
class GeoCoordinates:
    """Latitude/longitude pair for address geolocation.

    Both coordinates are required when provided; partial coordinates are rejected.
    Latitude ranges from -90 to 90, longitude from -180 to 180.
    """

    latitude: float | None = Float(min_value=-90.0, max_value=90.0)
    longitude: float | None = Float(min_value=-180.0, max_value=180.0)

    @invariant.post
    def both_coordinates_required(self) -> None:
        if self.latitude is None or self.longitude is None:
            raise ValidationError({"coordinates": ["Both latitude and longitude are required"]})


@identity.value_object(part_of="Customer")
class Profile:
    """Personal information associated with a Customer — name, phone, and date of birth.

    A Profile has no identity of its own; it exists only as part of a Customer.
    It is replaced wholesale on update (value object semantics).
    """

    first_name: str = String(required=True, max_length=100)
    last_name: str = String(required=True, max_length=100)
    phone: PhoneNumber | None = ValueObject(PhoneNumber)
    date_of_birth: date | None = Date()


@identity.entity(part_of="Customer")
class Address:
    """A physical location associated with a Customer, such as a home or work address.

    Each address carries a label, geo-coordinates, and a default flag. A customer may
    have up to 10 addresses, with exactly one marked as the default at all times.
    """

    label: str = String(choices=AddressLabel, default=AddressLabel.HOME.value)
    street: str = String(required=True, max_length=255)
    city: str = String(required=True, max_length=100)
    state: str | None = String(max_length=100)
    postal_code: str = String(required=True, max_length=20)
    country: str = String(required=True, max_length=100)
    is_default: bool = Boolean(default=False)
    geo_coordinates: GeoCoordinates | None = ValueObject(GeoCoordinates)


@identity.aggregate
class Customer:
    """A registered person on the platform, identified by a system ID and an external ID.

    The Customer aggregate groups profile, addresses, account status, and loyalty tier
    into a single transactional boundary. The "exactly one default address" invariant
    requires these elements to change together consistently.
    """

    external_id: str = String(required=True, max_length=255, unique=True)
    email: EmailAddress = ValueObject(EmailAddress, required=True)
    profile: Profile | None = ValueObject(Profile)
    addresses: list[Address] = HasMany(Address)
    status: str = Status(
        CustomerStatus,
        default=CustomerStatus.ACTIVE.value,
        transitions={
            CustomerStatus.ACTIVE: [CustomerStatus.SUSPENDED, CustomerStatus.CLOSED],
            CustomerStatus.SUSPENDED: [CustomerStatus.ACTIVE, CustomerStatus.CLOSED],
        },
    )
    tier: str = Status(
        CustomerTier,
        default=CustomerTier.STANDARD.value,
        transitions={
            CustomerTier.STANDARD: [CustomerTier.SILVER, CustomerTier.GOLD, CustomerTier.PLATINUM],
            CustomerTier.SILVER: [CustomerTier.GOLD, CustomerTier.PLATINUM],
            CustomerTier.GOLD: [CustomerTier.PLATINUM],
        },
    )
    registered_at: datetime = DateTime(default=datetime.now)
    last_login_at: datetime | None = DateTime()

    @invariant.post
    def addresses_cannot_exceed_maximum(self) -> None:
        if len(self.addresses) > 10:
            raise ValidationError({"addresses": ["Cannot have more than 10 addresses"]})

    @invariant.post
    def exactly_one_default_address_when_addresses_exist(self) -> None:
        if not self.addresses:
            return
        defaults = [a for a in self.addresses if a.is_default]
        if len(defaults) != 1:
            raise ValidationError({"addresses": ["Exactly one address must be marked as default"]})

    @classmethod
    def register(
        cls,
        external_id: str,
        email: str,
        first_name: str,
        last_name: str,
        phone: str | None = None,
        date_of_birth: date | None = None,
    ) -> "Customer":
        from identity.customer.events import CustomerRegistered

        phone_vo = PhoneNumber(number=phone) if phone else None
        profile = Profile(
            first_name=first_name,
            last_name=last_name,
            phone=phone_vo,
            date_of_birth=date_of_birth,
        )
        email_vo = EmailAddress(address=email)
        now = datetime.now()

        customer = cls(
            external_id=external_id,
            email=email_vo,
            profile=profile,
            registered_at=now,
        )
        customer.raise_(
            CustomerRegistered(
                customer_id=customer.id,
                external_id=external_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                registered_at=now,
            )
        )
        return customer

    def update_profile(
        self,
        first_name: str | _Unset = _UNSET,
        last_name: str | _Unset = _UNSET,
        phone: str | None | _Unset = _UNSET,
        date_of_birth: date | None | _Unset = _UNSET,
    ) -> None:
        from identity.customer.events import ProfileUpdated

        current = self.profile
        if current is None:
            raise ValidationError({"profile": ["Customer has no profile to update"]})

        new_first = first_name if first_name is not _UNSET else current.first_name
        new_last = last_name if last_name is not _UNSET else current.last_name

        phone_vo = (PhoneNumber(number=phone) if phone else None) if phone is not _UNSET else current.phone

        new_dob = date_of_birth if date_of_birth is not _UNSET else current.date_of_birth

        self.profile = Profile(
            first_name=new_first,
            last_name=new_last,
            phone=phone_vo,
            date_of_birth=new_dob,
        )
        self.raise_(
            ProfileUpdated(
                customer_id=self.id,
                first_name=new_first,
                last_name=new_last,
                phone=phone_vo.number if phone_vo else None,
                date_of_birth=str(new_dob) if new_dob else None,
            )
        )

    def add_address(
        self,
        street: str,
        city: str,
        postal_code: str,
        country: str,
        label: str = AddressLabel.HOME.value,
        state: str | None = None,
        is_default: bool = False,
        geo_coordinates: GeoCoordinates | None = None,
    ) -> Address:
        from identity.customer.events import AddressAdded

        # First address is always default
        if not self.addresses:
            is_default = True

        with atomic_change(self):
            # If this is set as default, unset all others
            if is_default:
                for addr in self.addresses:
                    if addr.is_default:
                        addr.is_default = False

            address = Address(
                label=label,
                street=street,
                city=city,
                state=state,
                postal_code=postal_code,
                country=country,
                is_default=is_default,
                geo_coordinates=geo_coordinates,
            )
            self.add_addresses(address)

        self.raise_(
            AddressAdded(
                customer_id=self.id,
                address_id=address.id,
                label=label,
                street=street,
                city=city,
                state=state,
                postal_code=postal_code,
                country=country,
                is_default=is_default,
            )
        )
        return address

    def update_address(self, address_id: str, **kwargs: str) -> None:
        from identity.customer.events import AddressUpdated

        address = next((a for a in self.addresses if a.id == address_id), None)
        if address is None:
            raise ValidationError({"addresses": [f"Address {address_id} not found"]})

        for field, value in kwargs.items():
            setattr(address, field, value)

        self.raise_(
            AddressUpdated(
                customer_id=self.id,
                address_id=address_id,
                **{k: v for k, v in kwargs.items() if isinstance(v, str | type(None))},
            )
        )

    def remove_address(self, address_id: str) -> None:
        from identity.customer.events import AddressRemoved

        address = next((a for a in self.addresses if a.id == address_id), None)
        if address is None:
            raise ValidationError({"addresses": [f"Address {address_id} not found"]})

        if len(self.addresses) <= 1:
            raise ValidationError({"addresses": ["Cannot remove the last address"]})

        was_default = address.is_default

        with atomic_change(self):
            self.remove_addresses(address)

            # If removed address was default, assign default to first remaining
            if was_default and self.addresses:
                self.addresses[0].is_default = True

        self.raise_(
            AddressRemoved(
                customer_id=self.id,
                address_id=address_id,
            )
        )

    def set_default_address(self, address_id: str) -> None:
        from identity.customer.events import DefaultAddressChanged

        address = next((a for a in self.addresses if a.id == address_id), None)
        if address is None:
            raise ValidationError({"addresses": [f"Address {address_id} not found"]})

        previous_default = next((a for a in self.addresses if a.is_default), None)
        previous_default_id = previous_default.id if previous_default else None

        with atomic_change(self):
            # Unset all defaults, then set the new one
            for addr in self.addresses:
                if addr.is_default:
                    addr.is_default = False
            address.is_default = True

        self.raise_(
            DefaultAddressChanged(
                customer_id=self.id,
                address_id=address_id,
                previous_default_address_id=previous_default_id,
            )
        )

    def suspend(self, reason: str) -> None:
        from identity.customer.events import AccountSuspended

        if self.status != CustomerStatus.ACTIVE.value:
            raise ValidationError({"status": ["Only active accounts can be suspended"]})

        self.status = CustomerStatus.SUSPENDED.value
        now = datetime.now()
        self.raise_(
            AccountSuspended(
                customer_id=self.id,
                reason=reason,
                suspended_at=now,
            )
        )

    def reactivate(self) -> None:
        from identity.customer.events import AccountReactivated

        if self.status != CustomerStatus.SUSPENDED.value:
            raise ValidationError({"status": ["Only suspended accounts can be reactivated"]})

        self.status = CustomerStatus.ACTIVE.value
        now = datetime.now()
        self.raise_(
            AccountReactivated(
                customer_id=self.id,
                reactivated_at=now,
            )
        )

    def close(self) -> None:
        from identity.customer.events import AccountClosed

        self.status = CustomerStatus.CLOSED.value
        now = datetime.now()
        self.raise_(
            AccountClosed(
                customer_id=self.id,
                closed_at=now,
            )
        )

    def upgrade_tier(self, new_tier: str) -> None:
        from identity.customer.events import TierUpgraded

        current_index = _TIER_ORDER.index(self.tier)
        new_index = _TIER_ORDER.index(new_tier)

        if new_index <= current_index:
            raise ValidationError({"tier": [f"Cannot downgrade from {self.tier} to {new_tier}"]})

        previous_tier = self.tier
        self.tier = new_tier
        now = datetime.now()
        self.raise_(
            TierUpgraded(
                customer_id=self.id,
                previous_tier=previous_tier,
                new_tier=new_tier,
                upgraded_at=now,
            )
        )
