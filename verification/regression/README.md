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
| [#1038](https://github.com/proteanhq/protean/issues/1038) | **guard** | No `Decimal` field — money as `Float` loses precision | `../tests/payments/integration/test_decimal_money.py` and `../tests/ordering/application/test_daily_order_stats_decimal.py` (the `DailyRevenue`, `PaymentStatusView` and `DailyOrderStats` projections and the Payment `Money` value object store money as `Decimal(precision=19, scale=4)`) |
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
| [#1629](https://github.com/proteanhq/protean/issues/1629) | **guard** | A top-level `[lint]` table in `domain.toml` was dropped by the config loader, while an env overlay (`[test.lint]`) loaded. The key filter was applied to one and not the other. Fixed in proteanhq/protean#1646 (`c421861`) | `regression/test_protean_regressions.py::test_lint_table_in_domain_toml_is_loaded` |
| [#1628](https://github.com/proteanhq/protean/issues/1628) | **guard** | A stale write on an event-sourced aggregate that raises a published event failed with an outbox `IntegrityError` instead of `ExpectedVersionError`: the UnitOfWork wrote outbox rows before the Message-DB append, and the external-broker row's unique check autoflushed the internal row, whose `<stream>-<version>` key clashed with the winner's. Version retry never ran. The in-memory outbox had the same clash. Fixed in proteanhq/protean#1637 (`68ed330`) | `regression/test_protean_regressions.py::test_stale_event_sourced_write_raises_expected_version_error` (memory and Postgres) (+ `oracles/test_no_lost_updates.py`, liveness) |
| [#1662](https://github.com/proteanhq/protean/issues/1662) | **guard** | `protean verify`'s tests stage removed `PROTEAN_ENV` from the pytest subprocess, so init and check ran under the caller's env while the tests ran under the plugin default (`test`, Postgres). Fixed in proteanhq/protean#1810 (`29e1252`): `--env` now sets the environment for all three stages. `scripts/verify-domains.sh` passes `--env memory` | `regression/test_protean_regressions.py::test_verify_tests_stage_keeps_protean_env` |
| [#1661](https://github.com/proteanhq/protean/issues/1661) | **guard** | `protean verify` took the failed-test count from the first `<N> failed` anywhere in pytest's output, so a failure message such as psycopg2's "port 15432 failed" was reported as 15432 failures. The pass/fail status was right. Fixed in proteanhq/protean#1801 (`0a5103f`) | `regression/test_protean_regressions.py::test_verify_tests_stage_counts_failures_from_the_summary` |
| [#1661](https://github.com/proteanhq/protean/issues/1661) | **guard** | `protean verify` took the passed-test count from the first `<N> passed` anywhere in pytest's output. With `-ra` in addopts, a skip reason such as "0 passed on this platform" was read as the count. `scripts/verify-domains.sh` gates on `passed > 0`, so this count feeds its gate. Fixed in proteanhq/protean#1801 (`0a5103f`) | `regression/test_protean_regressions.py::test_verify_tests_stage_counts_passes_from_the_summary` |
| [#1659](https://github.com/proteanhq/protean/issues/1659) | **guard** | `BaseEventSourcedRepository` had no `get_or_none`. [#1279](https://github.com/proteanhq/protean/issues/1279) added it to `BaseRepository` only, so a lookup on an event-sourced aggregate that may miss had to catch `ObjectNotFoundError`. Fixed in proteanhq/protean#1824 (`9f20ad1`); `src/inventory/stock/expiry.py` now uses it | `regression/test_protean_regressions.py::test_event_sourced_repository_get_or_none_returns_none_on_a_miss` |
| [#1663](https://github.com/proteanhq/protean/issues/1663) | **guard** | Saving an aggregate ran its `@invariant.pre` checks again when `BaseDAO._apply_pre_persist_hooks` stamped `auto_now` fields and ran aggregate enrichers, because both assign through `setattr`. A pre-invariant that rejects changes in the new state (loyalty's `closed_accounts_are_immutable`) then blocked the save of the transition that reached it: `close()` worked, and saving the closed `RewardAccount` raised `ValidationError`. Fixed in proteanhq/protean#1811 (`3a546f3`) | `regression/test_protean_regressions.py::test_auto_now_stamp_does_not_run_pre_invariants` |
| [#1682](https://github.com/proteanhq/protean/issues/1682) | **guard** | `UnitOfWork.commit` turned a `ValueError` into `ExpectedVersionError` unless it was raised while saving outbox rows. Sync dispatch runs later in the same `try`, so a `ValueError` from an event handler was reported as a version conflict, whatever the outbox setting, and version retry ran the committed command 4 times. Fixed in proteanhq/protean#1760 (`64c023d`) | `regression/test_protean_regressions.py::test_1682_value_error_from_a_sync_handler_is_not_a_version_conflict` |
| [#1883](https://github.com/proteanhq/protean/issues/1883) | **guard** | Under sync dispatch, an event handler that raised `ExpectedVersionError` made the command handler's version retry run the command again, though its commit had already succeeded. With `max_retries = 3` the command ran 4 times: in inventory, `ReceiveStock` ran 4 times and `StockReceived` was dispatched 4 times. Fixed in proteanhq/protean#1888 (`6aad05f`): the commit wraps the handler's failure in `TransactionError` | `regression/test_protean_regressions.py::test_1883_committed_command_is_not_rerun_when_a_sync_handler_raises_expected_version_error` |
| not filed yet | **open** | `BaseEventStore.verify()` raises `TypeError` on a Message DB row whose `data` is SQL NULL (the column is nullable). The Message DB client calls `json.loads(None)` while `verify` reads `$all`, so no report comes back and the row is never named, though `verify`'s docstring says a corrupt row is reported | `oracles/test_eventstore_integrity.py::test_null_message_data_is_reported_not_raised` (Message DB) |
| not filed yet | **open** | `protean eventstore verify --json` exits 1, its code for "violations found", when Message DB is unreachable, and prints a traceback with no JSON envelope. The connection error is raised inside `store.verify()`, after the domain loaded, so the CLI's handler does not map it to exit 2, which the CLI exit-code rule keeps for an environment error. `scripts/eventstore-verify.sh` prints "returned no JSON report" in this case | `oracles/test_eventstore_integrity.py::test_cli_exits_2_with_an_error_envelope_when_message_db_is_unreachable` (Message DB) |
| not filed yet | **open** | `protean check` reports `AGGREGATE_WITHOUT_COMMAND_HANDLER` for an aggregate declared with `abstract=True`. Protean accepts a command handler for one, but an abstract aggregate is never loaded or saved, so the handler would have nothing to act on. The rule skips only `protean.adapters.*`, while its sibling cluster rules skip abstract aggregates through `_abstract_aggregate_fqns()`. Loyalty's `Auditable` base trips it; `src/loyalty/domain.toml` suppresses it | `regression/test_protean_regressions.py::test_abstract_aggregate_is_not_flagged_without_command_handler` |
| not filed yet | **open** | `protean ir diff` exits 2 for "non-breaking changes only", the same code Click uses for a usage error such as an unknown option. A gate that reads exit 2 as a safe change passes when its own command line is broken. `scripts/ir-gate.sh` accepts exit 2 only with a JSON report whose summary has changes and no breaking change. The test compares the two codes, so it flips whichever one Protean moves | `regression/test_protean_regressions.py::test_ir_diff_usage_error_does_not_share_the_non_breaking_exit_code` |
| not filed yet | **open** | `protean ir diff` exits 1 for a breaking change and also for an error before any diff runs, such as a missing baseline file (`typer.Abort()`). The CLI exit-code rule keeps exit 2 for an environment error. `scripts/ir-gate.sh` reruns the diff in text format on exit 1, so the reason is printed either way | `regression/test_protean_regressions.py::test_ir_diff_load_error_does_not_share_the_breaking_exit_code` |
| [#1634](https://github.com/proteanhq/protean/issues/1634) | fixed | `DomainFixture.domain_context()` reset `current_domain`'s providers, brokers and event store instead of its own domain's. Fixed in proteanhq/protean#1644 (`c60a71d`) | no dedicated test. Every per-package `tests/*/conftest.py` enters `DomainFixture.domain_context()` per test, so the full suite exercises it |
| [#1635](https://github.com/proteanhq/protean/issues/1635) | **guard** | `protean server` with one worker calls `configure_logging(level=PROTEAN_LOG_LEVEL or "INFO")` before `Domain.init()`. Init then found root handlers and skipped all of `Domain.configure_logging`: the `[logging]` level, redaction, the correlation processor and filter, the OpenTelemetry processor and `per_logger`. So engine logs carried no `correlation_id`. `protean observatory` had the same gap. Fixed in proteanhq/protean#1640 (`e79a817`): both commands now call `apply_domain_logging` after the domain loads, which replaces the early setup. `protean observatory` applies only the first `--domain`'s `[logging]` | `regression/test_protean_regressions.py::test_server_single_worker_applies_domain_toml_logging_level` (server path only; checks the level and the correlation filter) |
| [#1636](https://github.com/proteanhq/protean/issues/1636) | fixed | `Domain.configure_logging` attached `ProteanCorrelationFilter` to the root logger, but Python runs a logger's filters only for records logged on that logger. Records from named loggers such as `logging.getLogger("ordering.x")` got no `correlation_id` attribute. Rendered lines still showed the ids through the formatter's `foreign_pre_chain`. The OpenTelemetry filter had the same limit. Fixed in proteanhq/protean#1665 (`f5690a7`) | no test |

**Run**

```bash
# fast (memory) — the regression guards
.venv/bin/python -m pytest verification/regression/ --protean-env memory -q
# full (real adapters) — everything, incl. the Postgres/Message-DB oracles
.venv/bin/python -m pytest verification/ --protean-env test -q
```
