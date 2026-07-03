#!/bin/bash
# Stop hook: Auto-format and lint changed Python after every Claude response.
# Runs ruff check --fix (auto-fixable lint issues) then ruff format.
# Only operates on files git sees as modified, to avoid full-tree scans.

set -e
cd "$CLAUDE_PROJECT_DIR"

# Changed Python files under src/ and tests/ (staged + unstaged + untracked)
CHANGED=$(git diff --name-only --diff-filter=ACMR HEAD -- 'src/**/*.py' 'tests/**/*.py' 'verification/**/*.py' 2>/dev/null || true)
UNSTAGED=$(git diff --name-only --diff-filter=ACMR -- 'src/**/*.py' 'tests/**/*.py' 'verification/**/*.py' 2>/dev/null || true)
UNTRACKED=$(git ls-files --others --exclude-standard -- 'src/**/*.py' 'tests/**/*.py' 'verification/**/*.py' 2>/dev/null || true)

FILES=$(printf '%s\n%s\n%s\n' "${CHANGED}" "${UNSTAGED}" "${UNTRACKED}" | sort -u | grep -v '^$' || true)

if [ -z "$FILES" ]; then
    exit 0
fi

# Auto-fix lint, then format — changed files only.
echo "$FILES" | xargs uv run ruff check --fix --quiet 2>&1 | tail -20 || true
echo "$FILES" | xargs uv run ruff format --quiet 2>&1 | tail -10 || true

exit 0
