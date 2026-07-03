---
name: check
description: Run ShopStream's full quality pipeline — ruff lint + format, mypy types, src-cleanliness, protean domain checks across all 9 domains, and IR-baseline staleness. Use whenever the user says "check the code", "run checks", "lint", "validate", "is the code clean", "anything wrong before I commit/PR", or wants to verify code health. Fix the code to satisfy each checker; never weaken the rule.
argument-hint: "[--fix]"
---

# Run All Quality Checks

Run the full quality pipeline across ShopStream. Each check catches a different
class of problem, so run them in sequence — code that lints clean can still have
type errors, pass mypy but violate DDD design rules, or drift its committed IR
baseline. Stop and report at the first hard failure unless the user wants the
whole sweep; otherwise run them all and summarize.

All commands run from the repo root. They use `uv run` under the hood via the
Makefile — don't prefix with `cd`.

## Step 1: Lint with ruff

```bash
make lint          # uv run ruff check src/ tests/
```

Many violations are auto-fixable:

```bash
uv run ruff check --fix src/ tests/
```

Re-run `make lint` to confirm nothing manual remains.

## Step 2: Format with ruff

```bash
uv run ruff format --check src/ tests/
```

If files need formatting, just apply it — formatting is mechanical:

```bash
make format        # uv run ruff format src/ tests/
```

## Step 3: src/ cleanliness

```bash
make check-src-clean
```

`src/` is reference code — it must not import test/verification tools (pytest,
hypothesis, schemathesis, toxiproxy). If this fails, the import belongs in
`tests/` or `verification/`, not `src/`.

## Step 4: Type check with mypy

```bash
make typecheck     # uv run mypy src/
```

Type errors usually need reading the source to find the intended types. Add
annotations or fix the real logic bug — don't sprinkle `# type: ignore`.

## Step 5: Domain validation (protean check)

```bash
make domain-check
```

Protean's own domain linter, run across all 9 domains (identity, catalogue,
ordering, inventory, payments, fulfillment, reviews, notifications, loyalty). It
catches DDD-level design issues ruff and mypy can't see — missing command
handlers, orphaned elements, invariant problems, cluster wiring. A failure in
ANY domain fails the step; read the per-domain output to find which.

## Step 6: IR baseline staleness

```bash
make ir-check
```

Each domain has a committed canonical IR baseline in `.protean/<domain>/ir.json`.
This reports whether the live domain still matches it. If a domain shows stale,
inspect the change with `make ir-diff`, and if the change is intended, regenerate
with `make ir` and commit the updated baseline. An **unexpected** IR change is a
signal — often a real Protean regression worth surfacing upstream, per the
ShopStream mandate.

## Handling failures

When a step fails, fix the code to satisfy the checker — not the other way
around. Weakening a lint rule, loosening mypy, adding blanket ignores, or
hand-editing an IR baseline to hide a diff is the wrong response. The rules were
chosen deliberately. If a rule genuinely seems wrong for a case, flag it to the
user rather than suppressing it.

Because ShopStream exists to keep Protean honest: if a `protean check` or IR
failure looks like a framework bug rather than a ShopStream mistake, say so and
propose surfacing it upstream instead of working around it.
