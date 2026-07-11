"""Shared FastAPI dependencies: DB session + pagination + sort parsing."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Query, Request
from sqlalchemy.orm import Session


def get_session(request: Request) -> Iterator[Session]:
    """Yield a session from the app's pooled session factory (per-request)."""
    db = request.app.state.db
    with db.sessionmaker() as session:
        yield session


@dataclass(slots=True)
class Pagination:
    limit: int
    offset: int
    page: int
    page_size: int


def pagination(
    request: Request,
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int | None = Query(None, ge=1, description="items per page"),
) -> Pagination:
    settings = request.app.state.settings
    size = min(page_size or settings.default_page_size, settings.max_page_size)
    return Pagination(limit=size, offset=(page - 1) * size, page=page, page_size=size)


def sort_order(
    order: str = Query("desc", pattern="^(asc|desc)$", description="asc or desc"),
) -> str:
    return order
