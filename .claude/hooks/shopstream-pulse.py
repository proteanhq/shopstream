#!/usr/bin/env python3
"""SessionStart pulse: surface ShopStream drift that nothing else flags.

Local-only and fast. Prints NOTHING when everything is clean (a pulse that always
fires becomes wallpaper), so every check here is rare + high-signal. Always exits
0 — never blocks session start. No network, no subprocess that can hang.

Checks:
  1. Which Protean build is installed — local dev wheel vs the pinned git rev.
     ShopStream's CLAUDE.md documents the "stale local wheel" footgun; this makes
     the current state visible so you never forget you're on a hand-built wheel.
  2. Interpreter drift — `protean` on PATH resolving outside the project .venv
     (a stale pyenv/global shim → phantom import errors).
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys
from pathlib import Path


def project_dir() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def _site_packages(venv: Path):
    for lib in (venv / "lib").glob("python*"):
        sp = lib / "site-packages"
        if sp.is_dir():
            return sp
    return None


def protean_build(root: Path):
    """Report when the installed Protean is a local wheel/editable, not the pin.

    Reads the dist-info direct_url.json (PEP 610). A `file://` url or
    dir_info.editable means you're on a hand-built local Protean — easy to forget
    after `uv pip install --reinstall protean-*.whl`, and it silently overrides
    the pyproject git pin until you `uv sync`.
    """
    venv = root / ".venv"
    sp = _site_packages(venv) if venv.is_dir() else None
    if not sp:
        return None
    dist = next(iter(sp.glob("protean-*.dist-info")), None)
    if not dist:
        return None
    durl = dist / "direct_url.json"
    if not durl.exists():
        return None
    try:
        data = json.loads(durl.read_text())
    except Exception:
        return None
    url = data.get("url", "")
    vcs = data.get("vcs_info", {})
    if vcs:  # git-pinned install — the normal, expected state
        return None
    if url.startswith("file://") or data.get("dir_info", {}).get("editable"):
        loc = url.replace("file://", "") or "local path"
        return (
            f"Protean is a LOCAL build ({loc}), not the pyproject git pin — "
            "run `uv sync` to restore the pinned version when done testing local changes"
        )
    return None


def interpreter_drift(root: Path):
    venv = root / ".venv"
    if not venv.is_dir():
        return None
    resolved = shutil.which("protean")
    if not resolved:
        return None
    try:
        if Path(resolved).resolve().parent != (venv / "bin").resolve():
            return (
                f"`protean` on PATH is {resolved} (not the project .venv) — "
                "use `uv run protean ...` or `make ...` to avoid a stale interpreter"
            )
    except Exception:
        return None
    return None


def main() -> None:
    root = project_dir()
    checks = (protean_build, interpreter_drift)
    lines = []
    for fn in checks:
        try:
            result = fn(root)
        except Exception:
            result = None
        if result:
            lines.append(f"  • {result}")
    if lines:
        print("⏩ shopstream-pulse — drift to review:")
        print("\n".join(lines))


if __name__ == "__main__":
    with contextlib.suppress(Exception):
        main()
    sys.exit(0)
