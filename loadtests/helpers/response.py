"""Response error extraction for load test observability.

Parses ShopStream API error responses into human-readable messages.
Handles two response shapes:

- Pydantic validation (422): {"detail": [{"loc": [...], "msg": "...", "type": "..."}]}
- Domain errors (400/404/409/422): {"error": "msg"} or {"error": {"field": "msg"}}
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from requests import Response


def extract_error_detail(response: Response) -> str:
    """Extract a human-readable error message from an API error response.

    Returns a compact string suitable for Locust failure messages and log lines.
    Gracefully handles unparseable bodies and missing fields.
    """
    try:
        body = response.json()
    except Exception:
        # Not JSON — return raw text, truncated
        text = getattr(response, "text", "") or ""
        return text[:300] or "(empty response body)"

    # Pydantic validation errors: {"detail": [{"loc": [...], "msg": "..."}]}
    if "detail" in body and isinstance(body["detail"], list):
        parts = []
        for err in body["detail"]:
            loc = ".".join(str(p) for p in err.get("loc", []))
            msg = err.get("msg", str(err))
            parts.append(f"{loc}: {msg}" if loc else msg)
        return " | ".join(parts)

    # Domain errors: {"error": "msg"} or {"error": {"field": "msg"}}
    if "error" in body:
        error = body["error"]
        if isinstance(error, dict):
            return " | ".join(f"{k}: {v}" for k, v in error.items())
        return str(error)

    # Unknown shape — stringify and truncate
    return str(body)[:300]
