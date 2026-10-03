# Protean regression set

ShopStream is Protean's proving ground. **Every Protean bug it finds becomes one
permanent, named test** — so a fixed bug can never quietly come back.

This is the habit. When you surface a Protean bug:

1. **File it upstream** on [proteanhq/protean](https://github.com/proteanhq/protean/issues).
2. **Add a named test** that asserts the *correct* (post-fix) behavior — here as
   `test_<issue>_<slug>`, or as an oracle under `verification/oracles/` when the
   bug is really a property (cross-reference it in the manifest below).
3. **`xfail(strict=True)` while the installed Protean still has the bug.** Strict
   means the test flips loudly (xpass → failure) the moment the fix lands, so we
   can't forget to promote it.
4. **When the fix is in ShopStream's Protean pin, drop the marker.** The test is
   now a permanent green guard.

A regression falls into one of three states:

- **guard** — fix present in the pin; the test passes and protects against
  regression.
- **open** — bug still open upstream; `xfail(strict)` documents it and flips when
  fixed.
- **tripwire** — fixed upstream but *not yet in ShopStream's Protean pin*;
  `xfail(strict)` flips when the pin is bumped, prompting the upgrade cleanup.

`test_manifest_matches_markers.py` checks the manifest below against the tests:
every **open** row's test must carry an xfail marker, and every **guard** row's
test must not.

## Manifest

Every Protean issue ShopStream has filed, and where it is guarded. (Reproductions
live either here or in `verification/oracles/`; some framework bugs have no natural
ShopStream reproduction and are noted as such.)

| Issue | State | Bug | Guard |
|-------|-------|-----|-------|
| [#1038](https://github.com/proteanhq/protean/issues/1038) | fixed | No `Decimal` field — money as `Float` loses precision | no ShopStream repro (money still modelled as `Float`) |
| [#1039](https://github.com/proteanhq/protean/issues/1039) | **guard** | Datetime payloads serialized with `str()`, not ISO/UTC | `regression/test_protean_regressions.py::test_1039_event_datetime_serialized_as_iso_utc` |
| [#1040](https://github.com/proteanhq/protean/issues/1040) | **guard** | Event-store append happened *after* the DB commit (crash window) | `oracles/test_crash_window_reconcile.py` (append-first durability) |
| [#1041](https://github.com/proteanhq/protean/issues/1041) | **guard** | `target_broker` nullable → unique-index bypass | `oracles/test_outbox_exactly_once.py` |
| [#1042](https://github.com/proteanhq/protean/issues/1042) | fixed | No consume-side idempotency → projector double-counts | no ShopStream use of the opt-in `idempotent=True`. `oracles/test_p20_projector_idempotency.py` guards ShopStream's own dedup in `ProductRatingProjector` |
| [#1046](https://github.com/proteanhq/protean/issues/1046) | fixed | `Date` field on a command/event breaks the message checksum | no ShopStream repro (no `Date` field on commands/events) |
| [#1048](https://github.com/proteanhq/protean/issues/1048) | **guard** | Multi-step process managers don't cascade under `sync` | `tests/loyalty/**` RedemptionSaga (full-cascade completion tests, xfails flipped) |
| [#1055](https://github.com/proteanhq/protean/issues/1055) | fixed | `Engine(test_mode).run()` unreliable in CI vs Redis | `tests/loyalty/integration/test_dlq.py` (`-m engine`, local-only). Closed upstream; CI still deselects `-m engine` until the engine job is re-added |
| [#1056](https://github.com/proteanhq/protean/issues/1056) | fixed | `repository.add()` doesn't reflect `Auto(increment=True)` back onto the aggregate | no ShopStream repro (no `increment=True` in any domain) |
| [#1065](https://github.com/proteanhq/protean/issues/1065) | fixed | `process_and_wait` belongs in `protean.testing` | adopted: `protean.testing.process_and_wait`/`drain`; local seed removed. CI pin (sync path only): `verification/support/test_processing.py::test_process_and_wait_sync_settles_inline`. `tests/loyalty/integration/test_dlq.py` uses `drain` but is `-m engine`, local-only |
| [#1071](https://github.com/proteanhq/protean/issues/1071) | **guard** | In-memory adapter ignores `Index(unique=True)` | `regression/test_protean_regressions.py::test_1071_memory_adapter_enforces_unique_index` (+ `oracles/test_outbox_exactly_once.py`, Postgres) |
| [#1073](https://github.com/proteanhq/protean/issues/1073) | **guard** | `reconcile_outbox` no-op on Message-DB (`read_last_message("$all")` is None) | `oracles/test_crash_window_reconcile.py::test_reconcile_restores_the_lost_outbox_row` |
| [#1076](https://github.com/proteanhq/protean/issues/1076) | fixed | Projectors reject `retries`/`retry_exceptions` options | `src/inventory/projections/low_stock_report.py` uses `retries`/`retry_exceptions` (guarded by `oracles/test_lowstock_projector_concurrency.py`, Postgres) |
| [#1078](https://github.com/proteanhq/protean/issues/1078) | **guard** | All-default ValueObject round-trips to `None` | `regression/test_protean_regressions.py::test_1078_all_default_value_object_round_trips` |
| [#1632](https://github.com/proteanhq/protean/issues/1632) | **open** (feature request) | `current_domain` has no warning-free probe: `getattr`/`isinstance` outside a context warn "Working outside of domain context" (pytest collection). Predates the 0.16.0 → main bump | `regression/test_protean_regressions.py::test_current_domain_probe_outside_context_is_silent` |
| [#1630](https://github.com/proteanhq/protean/issues/1630) | **guard** | The `is_event_sourced` deprecation warning was attributed to `protean/domain/__init__.py` instead of the decorator that used the option (`stacklevel` one frame short). Fixed in proteanhq/protean#1643 (`3dd06a4`) | `regression/test_protean_regressions.py::test_is_event_sourced_warning_points_at_the_decorator` |
| [#1631](https://github.com/proteanhq/protean/issues/1631) | **open** | The outermost UnitOfWork rolls back a transaction a nested UnitOfWork doomed, then returns without raising, so the caller sees success for writes that were lost | `regression/test_protean_regressions.py::test_outer_commit_of_a_doomed_transaction_raises` |
| [#1629](https://github.com/proteanhq/protean/issues/1629) | **open** | A top-level `[lint]` table in `domain.toml` is dropped by the config loader, while an env overlay (`[test.lint]`) loads. The key filter is applied to one and not the other | `regression/test_protean_regressions.py::test_lint_table_in_domain_toml_is_loaded` |
| [#1628](https://github.com/proteanhq/protean/issues/1628) | **guard** | A stale write on an event-sourced aggregate that raises a published event failed with an outbox `IntegrityError` instead of `ExpectedVersionError`: the UnitOfWork wrote outbox rows before the Message-DB append, and the external-broker row's unique check autoflushed the internal row, whose `<stream>-<version>` key clashed with the winner's. Version retry never ran. The in-memory outbox had the same clash. Fixed in proteanhq/protean#1637 (`68ed330`) | `regression/test_protean_regressions.py::test_stale_event_sourced_write_raises_expected_version_error` (memory and Postgres) (+ `oracles/test_no_lost_updates.py`, liveness) |
| [#1662](https://github.com/proteanhq/protean/issues/1662) | **open** | `protean verify`'s tests stage removes `PROTEAN_ENV` from the pytest subprocess, so init and check run under the caller's env while the tests run under the plugin default (`test`, Postgres). `scripts/verify-domains.sh` passes `--protean-env memory` in `PYTEST_ADDOPTS` | `regression/test_protean_regressions.py::test_verify_tests_stage_keeps_protean_env` |
| [#1661](https://github.com/proteanhq/protean/issues/1661) | **open** | `protean verify` takes the failed-test count from the first `<N> failed` anywhere in pytest's output, so a failure message such as psycopg2's "port 15432 failed" is reported as 15432 failures. The pass/fail status is right | `regression/test_protean_regressions.py::test_verify_tests_stage_counts_failures_from_the_summary` |
| [#1661](https://github.com/proteanhq/protean/issues/1661) | **open** | `protean verify` takes the passed-test count from the first `<N> passed` anywhere in pytest's output. With `-ra` in addopts, a skip reason such as "0 passed on this platform" is read as the count. `scripts/verify-domains.sh` gates on `passed > 0`, so this count feeds its gate | `regression/test_protean_regressions.py::test_verify_tests_stage_counts_passes_from_the_summary` |
| [#1659](https://github.com/proteanhq/protean/issues/1659) | **open** (feature request) | `BaseEventSourcedRepository` has no `get_or_none`. [#1279](https://github.com/proteanhq/protean/issues/1279) added it to `BaseRepository` only, so a lookup on an event-sourced aggregate that may miss still has to catch `ObjectNotFoundError` (`src/inventory/stock/expiry.py`) | `regression/test_protean_regressions.py::test_event_sourced_repository_get_or_none_returns_none_on_a_miss` |
| [#1663](https://github.com/proteanhq/protean/issues/1663) | **open** | Saving an aggregate runs its `@invariant.pre` checks again when `BaseDAO._apply_pre_persist_hooks` stamps `auto_now` fields and runs aggregate enrichers, because both assign through `setattr`. A pre-invariant that rejects changes in the new state (loyalty's `closed_accounts_are_immutable`) then blocks the save of the transition that reached it: `close()` works, and saving the closed `RewardAccount` raises `ValidationError` | `regression/test_protean_regressions.py::test_auto_now_stamp_does_not_run_pre_invariants` |
| [#1682](https://github.com/proteanhq/protean/issues/1682) | **open** | `UnitOfWork.commit` turns a `ValueError` into `ExpectedVersionError` unless it was raised while saving outbox rows. Sync dispatch runs later in the same `try`, so a `ValueError` from an event handler is reported as a version conflict, whatever the outbox setting, and version retry runs the committed command 4 times. #1682 describes the commit path; sync dispatch is a second route | `regression/test_protean_regressions.py::test_1682_value_error_from_a_sync_handler_is_not_a_version_conflict` |
| not filed yet | **open** | Under sync dispatch, an event handler that raises `ExpectedVersionError` makes the command handler's version retry run the command again, though its commit already succeeded. With `max_retries = 3` the command runs 4 times. In inventory, a `ReceiveStock` of 30 is applied 4 times (on hand 50 to 170) | `regression/test_protean_regressions.py::test_committed_command_is_not_rerun_when_a_sync_handler_raises_expected_version_error` |
| [#1634](https://github.com/proteanhq/protean/issues/1634) | fixed | `DomainFixture.domain_context()` reset `current_domain`'s providers, brokers and event store instead of its own domain's. Fixed in proteanhq/protean#1644 (`c60a71d`) | no dedicated test. Every per-package `tests/*/conftest.py` enters `DomainFixture.domain_context()` per test, so the full suite exercises it |
| [#1635](https://github.com/proteanhq/protean/issues/1635) | **guard** | `protean server` with one worker calls `configure_logging(level=PROTEAN_LOG_LEVEL or "INFO")` before `Domain.init()`. Init then found root handlers and skipped all of `Domain.configure_logging`: the `[logging]` level, redaction, the correlation processor and filter, the OpenTelemetry processor and `per_logger`. So engine logs carried no `correlation_id`. `protean observatory` had the same gap. Fixed in proteanhq/protean#1640 (`e79a817`): both commands now call `apply_domain_logging` after the domain loads, which replaces the early setup. `protean observatory` applies only the first `--domain`'s `[logging]` | `regression/test_protean_regressions.py::test_server_single_worker_applies_domain_toml_logging_level` (server path only; checks the level and the correlation filter) |
| [#1636](https://github.com/proteanhq/protean/issues/1636) | **open** | `Domain.configure_logging` attaches `ProteanCorrelationFilter` to the root logger, but Python runs a logger's filters only for records logged on that logger. Records from named loggers such as `logging.getLogger("ordering.x")` get no `correlation_id` attribute. Rendered lines still show the ids through the formatter's `foreign_pre_chain`. The OpenTelemetry filter has the same limit | no test (known gap) |

**Run**

```bash
# fast (memory) — the regression guards
.venv/bin/python -m pytest verification/regression/ --protean-env memory -q
# full (real adapters) — everything, incl. the Postgres/Message-DB oracles
.venv/bin/python -m pytest verification/ --protean-env test -q
```
