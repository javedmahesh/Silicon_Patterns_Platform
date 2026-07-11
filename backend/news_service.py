"""News Intelligence service — opportunity detail assembly + manual review.

Detail assembly stitches the rich opportunity intelligence together with its
reporting sources, related opportunities, the company event timeline, and the
append-only review history — reusing the repository queries.

Manual review applies analyst actions (not_relevant / merge / split / change_type /
archive / restore / note). Every action is recorded as history with a before/after
snapshot and NEVER overwrites the AI extraction outputs — it only mutates lifecycle,
relevance, type, or the merge pointer.
"""
from __future__ import annotations

from fastapi import HTTPException, status

from backend import repositories as repo
from backend.schemas import (
    OpportunityDetailOut,
    OpportunityOut,
    OpportunityReviewOut,
    OpportunitySourceOut,
    OpportunityTimelineItemOut,
)
from config.enums import (
    NEWS_ADAPTER_TYPES,
    OPPORTUNITY_LIFECYCLE_STATUSES,
    OPPORTUNITY_REVIEW_ACTIONS,
)
from master_db.models import NewsSource, Opportunity
from sqlalchemy import select
from sqlalchemy.orm import Session


def get_opportunity_detail(session: Session, opportunity_id: str) -> OpportunityDetailOut:
    opp = repo.get_opportunity(session, opportunity_id)
    if opp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "opportunity not found")

    sources = [OpportunitySourceOut.model_validate(s) for s in repo.opportunity_sources(session, opportunity_id)]
    related = [OpportunityOut.model_validate(o) for o in repo.related_opportunities(session, opp)]
    reviews = [OpportunityReviewOut.model_validate(r) for r in repo.opportunity_reviews(session, opportunity_id)]
    timeline = [
        OpportunityTimelineItemOut(
            opportunity_id=o.opportunity_id,
            opportunity_type=o.opportunity_type or "",
            opportunity_subtype=o.opportunity_subtype or "",
            article_title=o.article_title or "",
            published_date=o.published_date or "",
            lifecycle_status=o.lifecycle_status or "NEW",
            effective_opportunity_score=o.effective_opportunity_score or 0,
            is_current=(o.opportunity_id == opportunity_id),
        )
        for o in repo.company_opportunity_timeline(session, opp.company_domain)
    ]

    detail = OpportunityDetailOut.model_validate(opp)
    detail.sources = sources
    detail.related = related
    detail.reviews = reviews
    detail.timeline = timeline
    return detail


def _snapshot(opp: Opportunity) -> dict:
    """Small before/after snapshot — the mutable review fields only (AI outputs are
    never touched, so they need not be snapshotted)."""
    return {
        "lifecycle_status": opp.lifecycle_status,
        "is_relevant": opp.is_relevant,
        "opportunity_type": opp.opportunity_type,
        "opportunity_subtype": opp.opportunity_subtype,
        "merged_into": opp.merged_into,
        "validation_status": opp.validation_status,
    }


def review_opportunity(session: Session, opportunity_id: str, *, action: str,
                       actor_email: str, detail: str = "",
                       target_opportunity_id: str | None = None,
                       new_type: str | None = None) -> OpportunityDetailOut:
    """Apply a manual-review *action*, record history, return the refreshed detail."""
    if action not in OPPORTUNITY_REVIEW_ACTIONS:
        raise HTTPException(422, f"unknown review action '{action}'")
    opp = repo.get_opportunity(session, opportunity_id)
    if opp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "opportunity not found")

    before = _snapshot(opp)

    if action == "not_relevant":
        opp.is_relevant = False
        opp.lifecycle_status = "ARCHIVED"
        opp.validation_status = "REJECTED"
    elif action == "archive":
        opp.lifecycle_status = "ARCHIVED"
    elif action == "restore":
        opp.lifecycle_status = "ACTIVE"
        opp.is_relevant = True
        if opp.validation_status == "REJECTED":
            opp.validation_status = "REVIEW_REQUIRED"
    elif action == "change_type":
        if not new_type:
            raise HTTPException(422, "change_type requires new_type")
        opp.opportunity_type = new_type.strip().upper()
    elif action == "merge":
        if not target_opportunity_id:
            raise HTTPException(422, "merge requires target_opportunity_id")
        target = repo.get_opportunity(session, target_opportunity_id)
        if target is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "merge target not found")
        if target_opportunity_id == opportunity_id:
            raise HTTPException(422, "cannot merge an opportunity into itself")
        # Re-parent this opp's reporting sources onto the target, then archive this one.
        _merge_sources(session, source_id=opportunity_id, target=target)
        opp.merged_into = target_opportunity_id
        opp.lifecycle_status = "ARCHIVED"
        opp.is_relevant = False
        if not target.related_group_id and opp.related_group_id:
            target.related_group_id = opp.related_group_id
    elif action == "split":
        # Splitting shares the group so the pieces stay linked; the concrete new
        # opportunity is created by re-running extraction. Here we just record intent
        # and mark the source as monitoring so it stays visible.
        opp.lifecycle_status = "MONITORING"
    elif action == "note":
        pass  # note-only: history row is the note; no field change

    session.flush()
    repo.add_opportunity_review(
        session, opportunity_id, action=action, actor_email=actor_email, detail=detail,
        before=before, after=_snapshot(opp),
    )
    session.commit()
    return get_opportunity_detail(session, opportunity_id)


def _merge_sources(session: Session, *, source_id: str, target: Opportunity) -> None:
    from master_db.models import OpportunityArticle
    from integration.news import dedup

    existing = {s.canonical_url for s in repo.opportunity_sources(session, target.opportunity_id)}
    for src in repo.opportunity_sources(session, source_id):
        canon = src.canonical_url or dedup.canonical_url(src.url or "") or src.url
        if canon in existing:
            continue
        session.add(OpportunityArticle(
            opportunity_id=target.opportunity_id, article_id=src.article_id, url=src.url,
            canonical_url=canon, publisher=src.publisher, source_name=src.source_name,
            source_type=src.source_type, title=src.title, credibility=src.credibility,
            published_at=src.published_at,
        ))
        existing.add(canon)
    session.flush()


# ---------------------------------------------------- news source configuration
def list_news_sources(session: Session) -> list[NewsSource]:
    return list(session.scalars(select(NewsSource).order_by(NewsSource.name)))


def _validate_adapter(adapter_type: str) -> str:
    if adapter_type not in NEWS_ADAPTER_TYPES:
        raise HTTPException(422, f"unknown adapter_type '{adapter_type}' (allowed: {NEWS_ADAPTER_TYPES})")
    return adapter_type


def create_news_source(session: Session, *, name: str, adapter_type: str, url: str,
                       publisher: str, credibility: int, enabled: bool) -> NewsSource:
    _validate_adapter(adapter_type)
    if not name.strip():
        raise HTTPException(422, "name is required")
    if session.scalar(select(NewsSource).where(NewsSource.name == name.strip())):
        raise HTTPException(409, f"a news source named '{name}' already exists")
    src = NewsSource(name=name.strip(), adapter_type=adapter_type, url=url.strip(),
                     publisher=publisher.strip(), credibility=int(credibility), enabled=bool(enabled))
    session.add(src)
    session.commit()
    session.refresh(src)
    return src


def update_news_source(session: Session, source_id: int, *, patch: dict) -> NewsSource:
    src = session.get(NewsSource, source_id)
    if src is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "news source not found")
    if "adapter_type" in patch and patch["adapter_type"] is not None:
        _validate_adapter(patch["adapter_type"])
    for field in ("name", "adapter_type", "url", "publisher", "credibility", "enabled"):
        if patch.get(field) is not None:
            setattr(src, field, patch[field])
    session.commit()
    session.refresh(src)
    return src


def seed_default_sources(session: Session) -> dict:
    """Idempotently seed the curated production feeds (config/DB-driven)."""
    from integration.news.engine import seed_news_sources

    result = seed_news_sources(session)
    session.commit()
    return result


def set_lifecycle(session: Session, opportunity_id: str, *, lifecycle_status: str,
                  actor_email: str) -> OpportunityDetailOut:
    """Explicit lifecycle transition (New/Active/Monitoring/Resolved/Archived)."""
    lifecycle_status = (lifecycle_status or "").strip().upper()
    if lifecycle_status not in OPPORTUNITY_LIFECYCLE_STATUSES:
        raise HTTPException(422,
                            f"unknown lifecycle_status '{lifecycle_status}'")
    opp = repo.get_opportunity(session, opportunity_id)
    if opp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "opportunity not found")
    before = _snapshot(opp)
    opp.lifecycle_status = lifecycle_status
    if lifecycle_status == "ARCHIVED":
        pass
    elif not opp.is_relevant:
        opp.is_relevant = True
    session.flush()
    repo.add_opportunity_review(
        session, opportunity_id, action="restore" if lifecycle_status != "ARCHIVED" else "archive",
        actor_email=actor_email, detail=f"lifecycle -> {lifecycle_status}",
        before=before, after=_snapshot(opp),
    )
    session.commit()
    return get_opportunity_detail(session, opportunity_id)
