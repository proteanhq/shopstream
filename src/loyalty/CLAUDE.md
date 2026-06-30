# Loyalty Domain

Reward accounts and points (CQRS) plus event-sourced promotional campaigns. Loyalty is also
ShopStream's **capability-showcase** context — it deliberately exercises Protean building
blocks the other domains don't (domain services, application services, custom repositories,
cache-backed projections, abstract aggregate inheritance, fact events, snapshots, multi-step
upcasters). See root `PROTEAN_COVERAGE.md` for the full matrix, and `docs/loyalty/` for the
domain narrative + scenarios.

## Domain Composition Root

`domain.py` — `loyalty = Domain(name="loyalty")`. Registers `enrich_command` / `enrich_event`
via `register_command_enricher` / `register_event_enricher`. All elements register via
`@loyalty.<element_type>` decorators.

## Configuration

`domain.toml` — PostgreSQL database, Redis broker (DB 8), Message DB event store, a Redis
**cache** (`[caches.loyalty]`, DB 9) for the leaderboard projection, `snapshot_threshold = 5`,
health port 8089. Environment overlays for test (`loyalty_test` DB; `[test.caches.loyalty]`
uses the in-memory cache so tests need no Redis cache), production (async + telemetry), and
memory (in-memory/inline adapters).

## Aggregate: RewardAccount (CQRS)

**File:** `reward/reward_account.py`

Inherits the abstract base aggregate `Auditable` (`@loyalty.aggregate(abstract=True)`:
`created_at`, `updated_at`, `touch()`).

Root fields: `customer_id`, `status` (`AccountStatus`), `tier` (non-Enum `choices`:
bronze/silver/gold/platinum), `points_balance` (default 0), `lifetime_points` (default 0),
`membership_since` (`Date`), `member_code` (required; `RegexValidator` + custom
`NoTripleRepeatValidator`), `referral_code` (optional; `RegexValidator`), `card`
(`HasOne` MembershipCard), `entries` (`HasMany` PointsLedgerEntry).

### Enums
- `AccountStatus`: Active, Frozen, Closed

### Entities (part_of="RewardAccount")
- `MembershipCard` — `card_number`, `issued_on` (Date), `status` (`HasOne` child)
- `PointsLedgerEntry` — `reward_account` (explicit `Reference`), `entry_type` (choices:
  earn/redeem/transfer_in/transfer_out/adjust), `amount`, `balance_after`, `reason`,
  `occurred_at` (`HasMany` child)

### Invariants
- `balance_never_negative` (`@invariant.post`) — rejects over-redemption / over-transfer
- `closed_accounts_are_immutable` (`@invariant.pre`) — a Closed account cannot be mutated
  (the pre-check sees pre-mutation state, so `close()` itself is allowed)

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `RewardAccount.enroll(customer_id, member_code?, referral_code?)` | Factory; generates a valid `member_code` if absent; raises `RewardAccountEnrolled` |
| `issue_card(card_number)` | Attaches the 1:1 `MembershipCard` (at most one); raises `MembershipCardIssued` |
| `earn_points(amount, reason?)` | Increments balance + lifetime; appends ledger entry; raises `PointsEarned` |
| `redeem_points(amount, reason?)` | Decrements balance (not lifetime); appends ledger entry; raises `PointsRedeemed` |
| `close()` | Sets status Closed (terminal); raises `RewardAccountClosed` |

### Helpers
- `generate_member_code(length=8)` — module-level; produces a validator-passing code.
- `NoTripleRepeatValidator` — custom callable field validator (composed with `RegexValidator`).

## Aggregate: PromoCampaign (Event-Sourced)

**File:** `campaign/campaign.py` — `@loyalty.aggregate(is_event_sourced=True, fact_events=True)`

Root fields: `campaign_code`, `name`, `discount_type` (choices:
percentage/fixed/points_multiplier), `discount_value`, `status` (draft/active/paused/expired),
`starts_on` (Date), `ends_on` (Date), `launched_at`.

### Aggregate Methods
| Method | Behavior |
|--------|----------|
| `PromoCampaign.launch(...)` | Factory via `_create_new()`; raises `CampaignLaunched` (v3) |
| `activate()` | draft/paused &rarr; active; raises `CampaignActivated` |
| `pause(reason?)` | active &rarr; paused; raises `CampaignPaused` |
| `expire()` | any &rarr; expired (terminal); raises `CampaignExpired` |

All state changes are applied via `@apply` handlers for event-sourcing replay. With
`fact_events=True`, a complete-state `PromoCampaignFactEvent` is auto-emitted on the
`loyalty::promo_campaign-fact-<id>` stream after each persist. `snapshot_threshold=5` allows
snapshot-based reconstruction; `domain.create_snapshot(PromoCampaign, id)` /
`create_snapshots(PromoCampaign)` create them.

## Events

**RewardAccount events** (`reward/events.py`): `RewardAccountEnrolled`, `PointsEarned`,
`PointsRedeemed`, `MembershipCardIssued`, `RewardAccountClosed`.

**PromoCampaign events** (`campaign/events.py`): `CampaignLaunched` (`__version__ = 3`),
`CampaignActivated`, `CampaignPaused`, `CampaignExpired` (+ auto `PromoCampaignFactEvent`).

### Upcasters
**File:** `campaign/upcasters.py` — the only **multi-step** upcaster chain in ShopStream:
- `UpcastCampaignLaunchedV1ToV2` — renames `discount_pct` &rarr; `discount_value`, adds `discount_type`
- `UpcastCampaignLaunchedV2ToV3` — adds optional `starts_on` / `ends_on`

## Commands & Handlers

| File | Commands | Handler |
|------|---------|---------|
| `reward/enrollment.py` | `EnrollRewardAccount` | `EnrollRewardAccountHandler` |
| `reward/points.py` | `EarnPoints`, `RedeemPoints` | `PointsHandler` |

Points transfer is **not** a CQRS command — see the domain/application services below.
PromoCampaign lifecycle is driven directly on the event-sourced aggregate.

## Domain Service & Application Service

- **`reward/transfer.py`** — `TransferPoints`, a callable domain service
  (`part_of=[RewardAccount, RewardAccount]`) with `@invariant.pre` (both active) and
  `@invariant.post` (points conserved). Moves points between two accounts.
- **`reward/services.py`** — `LoyaltyService`, an `@loyalty.application_service`. Its
  `transfer_points` use case (`@use_case`) loads both accounts, runs `TransferPoints`, persists
  both in one UoW, and returns synchronously. Invoked directly (not via `domain.process()`).

## Custom Repository

**File:** `reward/repository.py` — `RewardAccountRepository` (`@loyalty.repository`). Adds
domain queries via `self._dao`: `top_savers` (order_by + limit), `never_redeemed`
(`F("lifetime_points")` comparison), `eligible_for_promo` (`Q` OR + `in`/`gte` lookups).
`repository_for(RewardAccount)` returns this repo, with the default `add`/`get` inherited.

## Cross-Domain Integration

### Inbound: Ordering → Loyalty
**File:** `reward/ordering_subscriber.py` — `@loyalty.subscriber(broker="global",
stream="ordering::order")`. On `OrderDelivered`, awards a delivery bonus by loading the
customer's `RewardAccount` and calling `earn_points` **directly** (subscriber **pattern B** —
direct aggregate mutation, vs the pattern-A command-dispatching subscribers elsewhere). ACL:
raw dict payload, type filtering, no shared event classes.

## Projections

**Directory:** `projections/`

| File | Projection | Storage | Projector |
|------|-----------|---------|-----------|
| `reward_account_view.py` | `RewardAccountView` | Database | `RewardAccountViewProjector` ([RewardAccount]) |
| `points_leaderboard.py` | `PointsLeaderboard` | **Cache** (`cache="loyalty"`) | `PointsLeaderboardProjector` ([RewardAccount]) |

`PointsLeaderboard` is the only cache-backed projection in ShopStream. Write via
`current_domain.cache_for(PointsLeaderboard).add(...)`; read via
`current_domain.view_for(PointsLeaderboard).get(...)`. `repository_for` does **not** serve
cache projections.

## API

Loyalty does not expose an HTTP API of its own yet — it is exercised as a capability showcase
and via cross-domain events. The domain is initialised in `src/app.py`.

## Tests

`tests/loyalty/{domain,application}/` — domain-layer behaviour (RewardAccount, PromoCampaign,
TransferPoints, upcasters) and application-layer flows (commands + projections, the application
service, the custom repository, the pattern-B subscriber, ES persistence + fact events +
snapshots). Run with `make test-loyalty` (or `make test-loyalty-domain` / `-application`), in
memory mode via `make test-memory*`, or against Postgres via `make test`.
