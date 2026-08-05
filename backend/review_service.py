"""Review-queue resolution: approve / merge / reject / create-alias.

Each action mutates the master DB (the one write surface of the API), updates the
``resolution_review_queue`` item, and writes a ``review_actions`` audit row.
"""
from __future__ import annotations


from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import repositories as repo
from backend.schemas import ReviewActionResult
from integration.merge import merge_company
from integration.resolver import CompanyResolver
from master_db.models import Company, ResolutionReviewQueue, ReviewAction

from backend.timeutil import utcnow as _utcnow


def _require_pending(session: Session, review_id: int) -> ResolutionReviewQueue:
    item = repo.get_review(session, review_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"review item {review_id} not found")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail=f"review item {review_id} already {item.status}")
    return item


def _audit(session, item, action, actor, from_domain, to_domain, detail) -> None:
    session.add(ReviewAction(
        review_id=item.id, action=action, actor=actor or "api",
        from_domain=from_domain or "", to_domain=to_domain or "", detail=detail or "",
    ))


def approve(session: Session, review_id: int, actor: str = "api") -> ReviewActionResult:
    item = _require_pending(session, review_id)
    domain = item.suggested_domain or item.resolved_domain
    company = session.get(Company, domain) if domain else None
    if company is not None:
        company.is_stub = False
        if company.validation_status in ("STUB", "PENDING"):
            company.validation_status = "VALID"
    item.status = "approved"
    item.resolved_domain = domain or ""
    item.reviewed_at = _utcnow()
    detail = f"approved company {domain}" if company else "approved (no company row)"
    _audit(session, item, "approve", actor, domain, domain, detail)
    session.commit()
    return ReviewActionResult(id=item.id, status=item.status, action="approve",
                              resolved_domain=domain, detail=detail)


def reject(session: Session, review_id: int, reason: str | None = None, actor: str = "api") -> ReviewActionResult:
    item = _require_pending(session, review_id)
    domain = item.suggested_domain
    company = session.get(Company, domain) if domain else None
    if company is not None and company.is_stub:
        company.validation_status = "REJECTED"
    item.status = "rejected"
    if reason:
        item.notes = (item.notes + f" | rejected: {reason}").strip(" |")
    item.reviewed_at = _utcnow()
    _audit(session, item, "reject", actor, domain, "", reason or "")
    session.commit()
    return ReviewActionResult(id=item.id, status=item.status, action="reject", detail=reason or "")


def merge(session: Session, review_id: int, target_domain: str, actor: str = "api") -> ReviewActionResult:
    item = _require_pending(session, review_id)
    source = item.suggested_domain
    if not source:
        raise HTTPException(status_code=400, detail="review item has no suggested_domain to merge from")
    src = session.get(Company, source)
    if src is None:
        raise HTTPException(status_code=404, detail=f"source company {source} not found")
    if not src.is_stub:
        raise HTTPException(status_code=409, detail=f"refusing to merge non-stub company {source}")
    try:
        moved = merge_company(session, source, target_domain)
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    item.status = "merged"
    item.resolved_domain = target_domain
    item.reviewed_at = _utcnow()
    detail = f"merged {source} -> {target_domain}: {moved}"
    _audit(session, item, "merge", actor, source, target_domain, detail)
    session.commit()
    return ReviewActionResult(id=item.id, status=item.status, action="merge",
                              resolved_domain=target_domain, detail=detail, moved=moved)


def create_alias(session: Session, review_id: int, name: str, company_domain: str,
                 actor: str = "api") -> ReviewActionResult:
    item = _require_pending(session, review_id)
    if session.get(Company, company_domain) is None:
        raise HTTPException(status_code=404, detail=f"target company {company_domain} not found")
    alias = CompanyResolver(session).register_alias(name, company_domain, source="review")
    if alias is None:
        raise HTTPException(status_code=400, detail="could not create alias (empty name or missing company)")
    item.status = "approved"
    item.resolved_domain = company_domain
    item.reviewed_at = _utcnow()
    detail = f"alias '{name}' -> {company_domain}"
    _audit(session, item, "create_alias", actor, "", company_domain, detail)
    session.commit()
    return ReviewActionResult(id=item.id, status=item.status, action="create_alias",
                              resolved_domain=company_domain, detail=detail)
