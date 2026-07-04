# Mutation audit — Protean core (T3.1)

`[manual]` / quarterly. **No public badge, no gate** — this is an audit report, not
a committed check. It measures how thoroughly Protean's OWN unit tests pin down its
core logic: a *surviving mutant* is a change to Protean source that **no test
notices**, i.e. a test gap. ShopStream exists to keep Protean honest, so once a
quarter we mutate the core modules ShopStream leans on hardest and read the report.

The proposed tests below are written for the **Protean** repo (that's where the
gap is); per the T3.1 decision they are documented here, not committed upstream in
this change.

## Scope (this run)

- **Target module**: `src/protean/utils/outbox.py` — the transactional outbox
  aggregate. It is the backbone of every async flow in ShopStream (command → outbox
  → engine → broker → projector), and it is dense with state-machine / retry /
  locking logic, which is exactly what mutation testing probes.
- **Protean commit**: `c79c497` — the exact commit ShopStream pins (`uv.lock`), run
  in an isolated `git worktree` so the developer's working branch is untouched.
- **Killer suite** (the tests a mutant must survive): the fast, infra-free outbox
  unit tests — `test_outbox_aggregate`, `test_outbox_field_bounds`,
  `test_outbox_cleanup_batched`, `test_reconciliation`, `test_outbox_repository`,
  `test_external_dispatch` (~165 tests, ~2s). Integration/perf tests are excluded
  (too slow per mutant); a surviving mutant here means the UNIT tests miss it.
- **Tool**: `mutmut 2.5.1`.

## Reproduce

```bash
# isolated protean source at the pinned commit
git -C /path/to/protean worktree add --detach /tmp/protean-t31 c79c497
cd /tmp/protean-t31

VENV=/path/to/shopstream/.venv           # reuse ShopStream's venv (has protean's deps)
$VENV/bin/pip install 'mutmut<3'
RUNNER="$VENV/bin/python -m pytest \
  tests/outbox/test_outbox_aggregate.py tests/outbox/test_outbox_field_bounds.py \
  tests/outbox/test_outbox_cleanup_batched.py tests/outbox/test_reconciliation.py \
  tests/outbox/test_outbox_repository.py tests/outbox/test_external_dispatch.py -x -q"
PYTHONPATH=src $VENV/bin/mutmut run \
  --paths-to-mutate src/protean/utils/outbox.py --tests-dir tests/outbox/ --runner "$RUNNER"
PYTHONPATH=src $VENV/bin/mutmut results     # survivors
PYTHONPATH=src $VENV/bin/mutmut show <id>   # the diff of one survivor
```

## Results

293 mutants, **228 killed / 65 survived → 78% mutation score**. A solid score for a
938-line module. The 65 survivors triage into:

- **~50 low-value** (equivalent or not-worth-testing): the `OutboxStatus` /
  `ProcessingResult` string constants (`"pending"`, `"already_locked"`, …), default
  tuning arguments (`PAGE_SIZE=50`, `lock_duration_minutes=5`, `published_retention_
  hours=168`, `batch_size` defaults, backoff caps), and the `Index(...)` definitions.
  Mutating a default constant that no behavioural test pins is expected; not a real
  gap.
- **~12 real logic gaps** — untested *boundaries* the unit tests skip over. These are
  the audit's actual output, below.

## Triaged survivors + proposed tests (for the Protean repo)

Line numbers are `src/protean/utils/outbox.py` @ `c79c497` (mutmut's cache is
off-by-one vs the file; the verified file lines are given for #1/#2).

### 1. Retry-timing boundary is untested (L196 in `start_processing`, L309 in `can_process_now`)

*Verified by hand*: applying the `<` → `<=` mutation on L309 leaves the whole outbox
unit suite green (236 passed) — the survivor is real, not a cache artifact.

```python
if current_time < ensure_utc_aware(self.next_retry_at):
    return False   # RETRY_NOT_DUE
```
Mutating `<` → `<=` (and `<` → `>`) **survives** on BOTH call sites — no test checks a
message whose `next_retry_at` is exactly now / one tick past. The retry-COUNT boundary
(`_can_retry`, `retry_count < max_retries`) IS killed by a test; the retry-TIME
boundary is not.

*Proposed test*: build a FAILED message with `next_retry_at = now + 1s`; assert
`start_processing` → `RETRY_NOT_DUE`. Advance to `next_retry_at = now - 1s`; assert it
now succeeds. Same two cases for `can_process_now`.

### 2. Lock-expiry boundary is untested (L319 in `_is_locked`)

```python
return bool(
    self.locked_until
    and datetime.now(timezone.utc) < ensure_utc_aware(self.locked_until)
    and self.status == OutboxStatus.PROCESSING.value
)
```
Mutating the `<` (and the `and`s) **survives** — no test exercises a lock that has just
expired vs one still held. A message whose `locked_until` is in the past must be
processable again; nothing pins that.

*Proposed test*: PROCESSING message with `locked_until = now - 1s` → `_is_locked()`
False (reclaimable); `locked_until = now + 1s` → True. Also flip `status` away from
PROCESSING with a live `locked_until` → False.

### 3. Query `limit` boundaries are untested (L379, L459, L503)

```python
if limit is not None and limit == 0:   # -> []      (L459 find_unprocessed, L383 helper)
    return []
if limit is not None and limit > 0:    # L379
    query = query.limit(limit)
...
if limit <= 0:                          # L503 claim_batch
    return []
```
Mutating `== 0` → `!= 0`, `> 0` → `>= 0`, and `<= 0` → `< 0` **survives** across the
fetch/claim paths — no test passes `limit=0` (must return empty, no query) or checks
the `> 0` guard. A `limit=0` that silently fetched everything would ship unnoticed.

*Proposed test*: `find_unprocessed(limit=0)` and `claim_batch(limit=0)` each return
`[]` and issue no query; `limit=1` returns at most one.

### 4. Reconcile-sweep window off-by-one is untested (L913 in `reconcile_outbox`)

```python
tail = last.metadata.event_store.global_position
start = max(0, tail - limit + 1)
```
Mutating `+ 1` → `- 1` and `max` → `min` **survives** — the reconcile sweep's start
position (which events it re-reads after a crash) has no test pinning the exact
window. An off-by-one here silently drops or re-scans an event during recovery — and
recovery is precisely what T1.3 found already-fragile (proteanhq/protean#1073).

*Proposed test*: with a known `global_position` tail and a `limit`, assert
`store.read("$all", position=..., no_of_messages=...)` is called with `start == tail -
limit + 1` (clamped at 0 for `tail < limit`).

### 5. `target_broker` filter not verified (L422)

```python
criteria &= Q(target_broker=target_broker)
```
Mutating `&=` → `=` (drop the AND) **survives** — the query method that filters by
`target_broker` has no test asserting the filter is actually applied, so a dropped
broker filter (returning other brokers' rows) would pass.

*Proposed test*: seed rows for two `target_broker`s; assert the method returns only the
requested broker's rows.

### 6. Minor: `max_retries` default not pinned (L86)

`max_retries: int = 3` — mutating `3` → `4` survives. Low priority, but the default
retry budget is a real contract; one assertion (`Outbox(...).max_retries == 3`) pins it.

## Notes

- **No public badge, no gate** (per the ticket) — this is a quarterly report.
- Survivors 1–4 are genuine boundary gaps in Protean's outbox unit tests; #1 and #4
  are the most valuable (retry timing + crash-recovery window). They would be filed /
  fixed in the Protean repo, not here.
- `mutmut results` itself crashes on this pony-orm version (`QueryResultIterator not
  iterable`); the survivors above were read straight from `.mutmut-cache` (see the
  `sqlite3` query in git history of this run). Worth noting if the audit is automated.
