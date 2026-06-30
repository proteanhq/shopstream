# Transfer Points Between Accounts

> One member gifts points to another. The operation spans two reward accounts, conserves the
> total, and is orchestrated by a domain service and an application service — not a CQRS command.

## The Story

Maya wants to send 40 of her points to her friend Leo. Both have reward accounts. The
transfer must be all-or-nothing: Maya's balance goes down by 40, Leo's goes up by 40, and the
total points across both accounts is unchanged. Neither account may be closed.

This operation touches *two* `RewardAccount` aggregates, so it cannot live inside a single
aggregate. ShopStream models it with a **domain service** (the business rule) wrapped by an
**application service** (the entry point and transaction boundary).

## The Flow

### 1. Entry Point — Application Service

Unlike the earn/redeem flow, this is not dispatched via `domain.process()`. The caller invokes
the application service **directly**:

```python
LoyaltyService().transfer_points(source_id, target_id, amount=40)
```

&rarr; [source](../../src/loyalty/reward/services.py)

`LoyaltyService.transfer_points` is decorated with `@use_case`, which wraps it in a Unit of
Work and logs execution. It:

1. Loads both accounts from the repository.
2. Runs the `TransferPoints` domain service.
3. Persists **both** accounts.
4. Returns a value synchronously: `{"source_balance": ..., "target_balance": ...}`.

This is the DDD (non-CQRS) counterpart to a command handler: invoked directly, always returns
a value, one implicit Unit of Work.

### 2. Business Rule — Domain Service

- **`TransferPoints`** — a callable domain service, `part_of=[RewardAccount, RewardAccount]`.

&rarr; [source](../../src/loyalty/reward/transfer.py)

On construction it records the combined balance (`_total_before`). Its `__call__(amount)`:

1. Rejects a non-positive `amount`.
2. Calls `source.redeem_points(amount, reason="transfer_out")`.
3. Calls `target.earn_points(amount, reason="transfer_in")`.

Cross-aggregate invariants guard the operation:

- `@invariant.pre both_accounts_must_be_active` — both accounts must be Active.
- `@invariant.post points_are_conserved` — the combined balance after must equal `_total_before`.

Over-transfer is caught for free: `redeem_points` drives the source balance negative, tripping
the source account's own `balance_never_negative` post-invariant.

### 3. Aggregate Behaviour

Each side reuses the normal points methods, so each raises its own event and appends a ledger
entry:

- Source: `redeem_points` &rarr; `PointsRedeemed` + a `transfer_out` ledger entry.
- Target: `earn_points` &rarr; `PointsEarned` + a `transfer_in` ledger entry.

### 4. Persistence

The `@use_case` Unit of Work commits **both** aggregates and both outbox records in one
transaction. Either both succeed or neither does — the conservation guarantee depends on this
atomicity.

### 5. Async Reactions

The two events flow through the outbox to the projectors, exactly as in the earn/redeem flow —
the source's `RewardAccountView` and `PointsLeaderboard` balances drop, the target's rise.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant App as LoyaltyService (@use_case)
    participant Repo as RewardAccount Repository
    participant Svc as TransferPoints (domain service)
    participant Src as Source account
    participant Tgt as Target account
    participant DB as Database + Outbox

    Client->>App: transfer_points(source_id, target_id, 40)
    App->>Repo: get(source_id), get(target_id)
    Repo-->>App: source, target
    App->>Svc: TransferPoints(source, target)(40)
    Note over Svc: @invariant.pre both accounts active
    Svc->>Src: redeem_points(40, "transfer_out")
    Src->>Src: balance -= 40; raise_(PointsRedeemed)
    Svc->>Tgt: earn_points(40, "transfer_in")
    Tgt->>Tgt: balance += 40; raise_(PointsEarned)
    Note over Svc: @invariant.post points conserved
    App->>DB: repository.add(source); repository.add(target)
    DB->>DB: UPDATE both + 2 outbox records (atomic)
    App-->>Client: {source_balance, target_balance}
```

## Edge Cases

| Scenario | What Happens | Why |
|----------|-------------|-----|
| Transfer more than the source balance | `ValidationError`: balance cannot be negative | Source account's `balance_never_negative` post-invariant |
| Either account is Closed (or Frozen) | `ValidationError`: both accounts must be active | `both_accounts_must_be_active` pre-invariant on the domain service |
| Non-positive transfer amount | `ValidationError`: transfer amount must be positive | Guard in `TransferPoints.__call__` |
| Persist fails mid-transfer | The whole Unit of Work rolls back; no points move | Both aggregates persist in one transaction — conservation is atomic |
| Lifetime points on the source | Unchanged (only balance moves) | `redeem_points` never lowers lifetime points |
| Same account as source and target | Conservation still holds (net zero) | The post-invariant compares total-before to total-after |
