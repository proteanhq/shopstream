# verification/

The heavier correctness checks for Protean, kept separate from the per-domain
`tests/` tree so that:

- the code people read to learn Protean (`src/`, `tests/<domain>/`) stays simple, and
- the normal test run does not need heavy tools (Hypothesis, Toxiproxy, etc.).

Read `VERIFICATION_STRATEGY.md` in the repo root for the full plan.

## Layout

```
verification/
  oracles/         hand-checked correctness checks (strongest: independent answer)
  metamorphic/     "two paths must agree" checks (projection==fold, replay, sync==async)
  contracts/       IR backward-compat gate, cross-domain event payload snapshots, engine ports + /readyz shape
  resilience/      fault injection (Toxiproxy, process kill) on small fixed workloads
  conformance/     same behavior across adapters (memory/postgres/sqlite) - keep small
  capabilities.yaml  capability -> taught_by / guarded_by / property map
  conftest.py      per-domain test setup (memory adapters, no Docker)
```

## Running

These are NOT part of the default `make test`. Run them on purpose:

```bash
# the one check that exists today (no Docker needed):
.venv/bin/python -m pytest verification/ --protean-env memory -q
```

`test_p20_projector_idempotency.py` is the worked example of the approach: its
expected value is computed by hand (one approved review -> count 1), independent
of the event stream, so it catches a real bug (a redelivered event double-counts)
that a "projection == fold(events)" check cannot. Each case reads the stored
event back from the event store and hands it to the projector several times.
The stored event carries its message id, which Protean's dedup needs.

The projectors pass in one of two ways. `ProductRatingProjector` dedupes on its
own `counted_reviews` (ticket T0.3). The other accumulating projectors are
marked `idempotent=True`: Protean records a processed-message marker per
message id and handler, in the same unit of work as the read-model write, and
skips a message it has already marked. `test_idempotency_cleanup.py` checks that
`cleanup_processed_messages`, which `make idempotency-cleanup` runs, deletes old
markers and keeps recent ones. It also runs the target's command for each domain
the target lists.

## Adding a check

1. Pick the property from `VERIFICATION_STRATEGY.md` section 4.
2. Prefer a type-A check (compute the expected answer independently; do not let
   the system under test produce its own answer).
3. Add a row to `capabilities.yaml`.
4. Keep it out of `src/` and out of `tests/<domain>/`.
