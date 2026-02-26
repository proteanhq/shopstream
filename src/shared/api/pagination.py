"""Shared pagination response envelope for collection GET endpoints."""

from pydantic import BaseModel


class PaginatedResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
