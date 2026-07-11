from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query
from sqlalchemy.orm import Session

from backend import repositories as repo
from backend import review_service
from backend.dependencies import Pagination, get_session, pagination
from backend.schemas import (
    AliasBody,
    MergeBody,
    Page,
    RejectBody,
    ReviewActionOut,
    ReviewActionResult,
    ReviewItemOut,
)

router = APIRouter(prefix="/review-queue", tags=["review-queue"])


@router.get("", response_model=Page[ReviewItemOut], summary="List review-queue items")
def list_items(
    session: Session = Depends(get_session),
    page: Pagination = Depends(pagination),
    status: str | None = Query(None, description="pending | approved | rejected | merged"),
    source_engine: str | None = Query(None),
    match_type: str | None = Query(None),
):
    rows, total = repo.list_review(
        session, status=status, source_engine=source_engine, match_type=match_type,
        limit=page.limit, offset=page.offset,
    )
    items = [ReviewItemOut.model_validate(r) for r in rows]
    return Page.build(items, total, page.page, page.page_size)


@router.get("/{review_id}", response_model=ReviewItemOut, summary="One review item")
def get_item(review_id: int = Path(...), session: Session = Depends(get_session)):
    item = repo.get_review(session, review_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"review item {review_id} not found")
    return item


@router.get("/{review_id}/actions", response_model=list[ReviewActionOut], summary="Audit trail")
def get_actions(review_id: int = Path(...), session: Session = Depends(get_session)):
    return repo.list_review_actions(session, review_id)


@router.post("/{review_id}/approve", response_model=ReviewActionResult, summary="Confirm the stub company")
def approve(review_id: int, session: Session = Depends(get_session),
            actor: str | None = Header(default=None, alias="X-Actor")):
    return review_service.approve(session, review_id, actor=actor or "api")


@router.post("/{review_id}/merge", response_model=ReviewActionResult, summary="Merge stub into a canonical company")
def merge(body: MergeBody, review_id: int, session: Session = Depends(get_session),
          actor: str | None = Header(default=None, alias="X-Actor")):
    return review_service.merge(session, review_id, body.target_domain, actor=actor or "api")


@router.post("/{review_id}/reject", response_model=ReviewActionResult, summary="Reject (not a prospect)")
def reject(review_id: int, body: RejectBody | None = None, session: Session = Depends(get_session),
           actor: str | None = Header(default=None, alias="X-Actor")):
    return review_service.reject(session, review_id, body.reason if body else None, actor=actor or "api")


@router.post("/{review_id}/alias", response_model=ReviewActionResult, summary="Create a name->domain alias")
def create_alias(body: AliasBody, review_id: int, session: Session = Depends(get_session),
                 actor: str | None = Header(default=None, alias="X-Actor")):
    return review_service.create_alias(session, review_id, body.name, body.company_domain, actor=actor or "api")
