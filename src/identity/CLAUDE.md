# Identity Domain

Customer accounts, profiles, addresses, and loyalty tiers.

## Domain Composition Root

`domain.py` — `identity = Domain(name="identity")`

All elements register via `@identity.<element_type>` decorators.

## Configuration

`domain.toml` — PostgreSQL database, Redis broker, Message DB event store. Environment overlays for test (`identity_test` DB) and production (`identity` DB, async events).

## Aggregate: Customer

**File:** `customer/customer.py`

Root fields: `external_id`, `email` (EmailAddress VO), `profile` (Profile VO), `addresses` (HasMany Address), `status` (CustomerStatus enum), `tier` (CustomerTier enum), `registered_at`, `last_login_at`.

### Enums
- `CustomerStatus`: Active, Suspended, Closed
- `CustomerTier`: Standard, Silver, Gold, Platinum (ordered for upgrade validation)
- `AddressLabel`: Home, Work, Other

### Value Objects (part_of="Customer")
- `Profile` — first_name, last_name, phone (PhoneNumber VO), date_of_birth
- `GeoCoordinates` — latitude, longitude (both required invariant)

### Entity (part_of="Customer")
- `Address` — label, street, city, state, postal_code, country, is_default, geo_coordinates

### Shared Value Objects (`shared/`)
- `EmailAddress` (`shared/email.py`) — address field, format validation invariant
- `PhoneNumber` (`shared/phone.py`) — number field, flexible format validation

### Invariants
- `addresses_cannot_exceed_maximum` — max 10 addresses
- `exactly_one_default_address_when_addresses_exist` — exactly one default when any exist

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `Customer.register(...)` | Class method, creates customer, raises `CustomerRegistered` |
| `update_profile(...)` | Replaces Profile VO, raises `ProfileUpdated` |
| `add_address(...)` | First address auto-default, uses `atomic_change`, raises `AddressAdded` |
| `update_address(address_id, **kwargs)` | Partial update, raises `AddressUpdated` |
| `remove_address(address_id)` | Cannot remove last, reassigns default, raises `AddressRemoved` |
| `set_default_address(address_id)` | Unsets all others, raises `DefaultAddressChanged` |
| `suspend(reason)` | Only from Active, raises `AccountSuspended` |
| `reactivate()` | Only from Suspended, raises `AccountReactivated` |
| `close()` | Not from Closed, raises `AccountClosed` |
| `upgrade_tier(new_tier)` | Only upgrades (no downgrades), raises `TierUpgraded` |

## Events

**File:** `customer/events.py` — All versioned (`__version__ = "v1"`), past tense names.

`CustomerRegistered`, `ProfileUpdated`, `AddressAdded`, `AddressUpdated`, `AddressRemoved`, `DefaultAddressChanged`, `AccountSuspended`, `AccountReactivated`, `AccountClosed`, `TierUpgraded`

## Commands & Handlers

One file per use case, command + handler in same file:

| File | Command | Handler |
|------|---------|---------|
| `customer/registration.py` | `RegisterCustomer` | `RegisterCustomerHandler` — creates via `Customer.register()` |
| `customer/profile.py` | `UpdateProfile` | `UpdateProfileHandler` — loads, calls `update_profile()` |
| `customer/addresses.py` | `AddAddress`, `UpdateAddress`, `RemoveAddress`, `SetDefaultAddress` | `AddressHandler` — all address mutations |
| `customer/account.py` | `SuspendAccount`, `ReactivateAccount`, `CloseAccount` | `AccountHandler` — lifecycle transitions |
| `customer/tier.py` | `UpgradeTier` | `UpgradeTierHandler` — tier upgrades |

Handler pattern: load aggregate from repo → call aggregate method → `repo.add(customer)` → return ID if creation.

## Projections

**Directory:** `projections/`

| File | Projection | Projector | Events Handled |
|------|-----------|-----------|----------------|
| `customer_card.py` | `CustomerCard` | `CustomerCardProjector` | CustomerRegistered, ProfileUpdated, AccountSuspended/Reactivated/Closed, TierUpgraded |
| `customer_lookup.py` | `CustomerLookup` | `CustomerLookupProjector` | Lookup by external_id/email |
| `address_book.py` | `AddressBook` | `AddressBookProjector` | Address events |
| `customer_segments.py` | `CustomerSegments` | `CustomerSegmentsProjector` | Tier/status segmentation |

Projector pattern:
```python
@identity.projector(projector_for=CustomerCard, aggregates=[Customer])
class CustomerCardProjector:
    @on(CustomerRegistered)
    def on_customer_registered(self, event):
        current_domain.repository_for(CustomerCard).add(
            CustomerCard(customer_id=event.customer_id, ...)
        )
```

## API

**Package:** `api/`

| File | Contents |
|------|----------|
| `api/__init__.py` | Re-exports `router` for backward-compatible imports |
| `api/schemas.py` | Pydantic request/response models (external contract) |
| `api/routes.py` | 10 endpoints on `APIRouter(prefix="/customers", tags=["customers"])` |

### Endpoints
| Method | Path | Request Body | Response |
|--------|------|-------------|----------|
| POST | `/customers` | `RegisterCustomerRequest` | `CustomerIdResponse` (201) |
| PUT | `/customers/{id}/profile` | `UpdateProfileRequest` | `StatusResponse` |
| POST | `/customers/{id}/addresses` | `AddAddressRequest` | `StatusResponse` (201) |
| PUT | `/customers/{id}/addresses/{aid}` | `UpdateAddressRequest` | `StatusResponse` |
| DELETE | `/customers/{id}/addresses/{aid}` | — | `StatusResponse` |
| PUT | `/customers/{id}/addresses/{aid}/default` | — | `StatusResponse` |
| PUT | `/customers/{id}/suspend` | `SuspendAccountRequest` | `StatusResponse` |
| PUT | `/customers/{id}/reactivate` | — | `StatusResponse` |
| PUT | `/customers/{id}/close` | — | `StatusResponse` |
| PUT | `/customers/{id}/tier` | `UpgradeTierRequest` | `StatusResponse` |
