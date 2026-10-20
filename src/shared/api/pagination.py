"""Shared pagination response envelope for collection GET endpoints."""

from typing import Any

from pydantic import BaseModel


class PaginatedResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
