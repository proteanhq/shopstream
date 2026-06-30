# Earn and Redeem Points

> A customer enrols into the rewards program, earns points on activity, and later redeems
> some — updating both the database view and the cache-backed leaderboard.

## The Story

Maya signs up for ShopStream's rewards program. A reward account is created for her in the
bronze tier with a zero balance and a freshly generated member code. Over the following
weeks she earns points (from orders and a delivery bonus), and one day she redeems some
points for a voucher. Her spendable balance goes down, but her *lifetime* points — the
number that drives her tier — stay put.

Behind the scenes, every earn and redeem both mutates the `RewardAccount` aggregate and
appends an append-only ledger entry, then fans out to two read models: a database-backed
account view and a cache-backed points leaderboard.

## The Flow

### 1. Enrolment

A command enrols Maya:

- **`EnrollRewardAccount`** — the intent to create a reward account. Key data:
  `customer_id`, optional `member_code`.

&rarr; [source](../../src/loyalty/reward/enrollment.py)

`EnrollRewardAccountHandler` calls the aggregate factory `RewardAccount.enroll(...)`. If no
`member_code` is supplied, `generate_member_code()` produces a valid one (6–12 uppercase
alphanumerics, no three-in-a-row repeats — satisfying the field's `RegexValidator` and the
custom `NoTripleRepeatValidator`). The account is created Active, bronze, with
`points_balance = 0` and `lifetime_points = 0`, and raises `RewardAccountEnrolled`.

&rarr; [source](../../src/loyalty/reward/reward_account.py) (`RewardAccount.enroll`)

### 2. Earning Points

Later, a command credits points:

- **`EarnPoints`** — key data: `account_id`, `amount`, `reason`.

&rarr; [source](../../src/loyalty/reward/points.py)

`PointsHandler.earn()` loads the account and calls `earn_points(amount, reason)`, which:

1. Increases `points_balance` by `amount`.
2. Increases `lifetime_points` by `amount` (lifetime only ever grows).
3. Appends a `PointsLedgerEntry` (`entry_type="earn"`, `balance_after`, `reason`,
   `occurred_at`) via the `HasMany` helper `add_entries(...)`.
4. `touch()`es the audit timestamp.
5. Raises `PointsEarned`.

The handler persists with `current_domain.repository_for(RewardAccount).add(account)`.

### 3. Redeeming Points

When Maya redeems:

- **`RedeemPoints`** — key data: `account_id`, `amount`, `reason`.

`PointsHandler.redeem()` loads the account and calls `redeem_points(amount, reason)`, which
subtracts from `points_balance` (but **not** `lifetime_points`), appends a `redeem` ledger
entry, and raises `PointsRedeemed`.

**What invariants are checked?**
- `balance_never_negative` (`@invariant.post`) rejects any redemption larger than the balance.
- `closed_accounts_are_immutable` (`@invariant.pre`) rejects any mutation of a closed account.

**What could fail?**
- Redeeming more than the balance &rarr; `ValidationError`: "Points balance cannot be negative".
- A non-positive amount &rarr; `ValidationError`: "Amount must be positive".
- Operating on a closed account &rarr; `ValidationError`: "A closed reward account cannot be modified".

### 4. Persistence

Each command's Unit of Work commits the updated `RewardAccount` and writes an outbox record
for the raised event — atomically in the same database transaction.

### 5. Async Reactions

With `event_processing` async, the Loyalty Engine's OutboxProcessor publishes the event to
Redis Streams, and projectors update the read models:

| Event | Handled By | Effect |
|-------|-----------|--------|
| `RewardAccountEnrolled` | `RewardAccountViewProjector` | Creates the DB `RewardAccountView` (balance 0, Active) |
| `RewardAccountEnrolled` | `PointsLeaderboardProjector` | Creates the cache `PointsLeaderboard` entry (balance 0) |
| `PointsEarned` | `RewardAccountViewProjector` | Sets `points_balance`, increments `lifetime_points` |
| `PointsEarned` | `PointsLeaderboardProjector` | Updates the cached balance |
| `PointsRedeemed` | `RewardAccountViewProjector` | Lowers `points_balance` (lifetime unchanged) |
| `PointsRedeemed` | `PointsLeaderboardProjector` | Updates the cached balance |

The leaderboard projector reads the existing entry via `view_for(PointsLeaderboard).get(id)`,
updates the balance, and writes it back via `cache_for(PointsLeaderboard).add(entry)` — the
cache-backed projection's read/write API.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Handler as PointsHandler
    participant Repo as RewardAccount Repository
    participant Agg as RewardAccount
    participant DB as Database + Outbox
    participant Engine as Loyalty Engine
    participant View as RewardAccountView (DB)
    participant LB as PointsLeaderboard (cache)

    Client->>Handler: EarnPoints {account_id, amount}
    Handler->>Repo: get(account_id)
    Repo-->>Handler: RewardAccount
    Handler->>Agg: earn_points(amount, reason)
    Agg->>Agg: balance += amount; lifetime += amount
    Agg->>Agg: add_entries(PointsLedgerEntry "earn")
    Agg->>Agg: raise_(PointsEarned)
    Handler->>DB: repository.add(account)
    DB->>DB: UPDATE account + outbox record (atomic)

    Note over Engine: Async processing
    Engine->>DB: Poll outbox
    Engine->>View: PointsEarned → update balance + lifetime
    Engine->>LB: PointsEarned → view_for().get() → cache_for().add()
```

## Edge Cases

| Scenario | What Happens | Why |
|----------|-------------|-----|
| Enrol without a member code | A valid code is generated automatically | Every account needs its own code; generation guarantees the validators pass |
| Redeem more than the balance | `ValidationError`: balance cannot be negative | `balance_never_negative` post-invariant |
| Earn/redeem a non-positive amount | `ValidationError`: amount must be positive | Method-level guard before mutation |
| Earn or redeem on a closed account | `ValidationError`: closed account is immutable | `closed_accounts_are_immutable` pre-invariant (sees pre-mutation state) |
| Redeem points | `lifetime_points` is unchanged; only `points_balance` drops | Lifetime drives tiering and reflects total contribution |
| Leaderboard read with a bare key | Use `view_for(PointsLeaderboard).get(id)` | Cache keys are `name:::id`; `view_for`/`cache_for` build them — `repository_for` does not serve cache projections |
| Projector fails after commit | Event stays in the outbox, retried next poll | At-least-once delivery keeps projections eventually consistent |
