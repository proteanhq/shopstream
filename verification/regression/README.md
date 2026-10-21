# Protean regression set

ShopStream is Protean's proving ground. **Every Protean bug it finds becomes one
permanent, named test**, so a fixed bug can never quietly come back.

This is the habit. When you surface a Protean bug:

1. **File it upstream** on [proteanhq/protean](https://github.com/proteanhq/protean/issues).
2. **Add a named test with a `protean_bug` marker** that asserts the *correct*
   (post-fix) behavior. Put it here as `test_<issue>_<slug>`, in the file for its
   Protean area, or as an oracle under `verification/oracles/` when the bug is
   really a property. The marker names the issue, the state and the bug:

   ```python
   @pytest.mark.protean_bug(issue=1913, state="open", bug="`protean projection rebuild` keeps ...")
   ```

   Use `issue=None` for a bug not filed yet, and fill it in once it is.
3. **`xfail(strict=True)` while the installed Protean still has the bug.** Strict
   means the test flips loudly (xpass → failure) the moment the fix lands, so we
   can't forget to promote it.
4. **When the fix is in ShopStream's Protean pin, drop the xfail** and set the
   marker's state to `guard`. The test is now a permanent green guard.

A regression is in one of four states, the marker's `state`:

- **guard**: fix present in the pin; the test passes and protects against
  regression.
- **open**: bug still open upstream; `xfail(strict=True)` documents it and flips
  when fixed.
- **tripwire**: fixed upstream but *not yet in ShopStream's Protean pin*;
  `xfail(strict=True)` flips when the pin is bumped, prompting the upgrade cleanup.
- **fixed**: fixed in the pin and covered by a test that does more than pin the
  bug, such as an oracle or a feature test.

## Where the tests live

The tests here are split by Protean area. Put a new regression test in the file
for its area. Add a new file only for an area none of the five covers.

| File | Area |
|------|------|
| `test_persistence.py` | Repositories, adapters, value objects and the unit of work |
| `test_event_sourcing.py` | Event-sourced repositories, version conflicts, sync dispatch and snapshots |
| `test_messaging.py` | Brokers, streams, engine outbox processors, dead-letter queues and projection rebuilds |
| `test_ir.py` | `protean ir diff` |
| `test_tooling.py` | `current_domain`, config loading, `protean check`, `protean server` and `protean verify` |

## Manifest

Run `make regression-manifest` to list every Protean bug ShopStream guards, with
its state and test. The table is built from the `protean_bug` markers across
`verification/` and `tests/`, so a PR that adds a regression edits only its test.
The table is not committed, because every such PR would then edit the same lines.

`test_manifest_matches_markers.py` checks the markers against the tests:

- an **open** or **tripwire** test carries `xfail(strict=True)`;
- a **guard** or **fixed** test carries no xfail;
- every xfail test in `verification/` and `tests/` has a `protean_bug` marker;
- every marker names one of the four states, and a bug.

## History

Bugs ShopStream filed that no test guards. This table is frozen: a new bug gets a
test and a marker instead.

| Issue | State | Bug | Why there is no test |
|-------|-------|-----|----------------------|
| [#1046](https://github.com/proteanhq/protean/issues/1046) | fixed | `Date` field on a command/event breaks the message checksum | no ShopStream repro (no `Date` field on commands/events) |
| [#1056](https://github.com/proteanhq/protean/issues/1056) | fixed | `repository.add()` doesn't reflect `Auto(increment=True)` back onto the aggregate | no ShopStream repro (no `increment=True` in any domain) |
| [#1634](https://github.com/proteanhq/protean/issues/1634) | fixed | `DomainFixture.domain_context()` reset `current_domain`'s providers, brokers and event store instead of its own domain's. Fixed in proteanhq/protean#1644 (`c60a71d`) | no dedicated test. Every per-package `tests/*/conftest.py` enters `DomainFixture.domain_context()` per test, so the full suite exercises it |
| [#1636](https://github.com/proteanhq/protean/issues/1636) | fixed | `Domain.configure_logging` attached `ProteanCorrelationFilter` to the root logger, but Python runs a logger's filters only for records logged on that logger. Records from named loggers such as `logging.getLogger("ordering.x")` got no `correlation_id` attribute. Rendered lines still showed the ids through the formatter's `foreign_pre_chain`. The OpenTelemetry filter had the same limit. Fixed in proteanhq/protean#1665 (`f5690a7`) | no test |

**Run**

```bash
# fast (memory) — the regression guards
.venv/bin/python -m pytest verification/regression/ --protean-env memory -q
# full (real adapters) — everything, incl. the Postgres/Message-DB oracles
.venv/bin/python -m pytest verification/ --protean-env test -q
```
