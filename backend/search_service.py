"""Enterprise CRM Phase 11: Enterprise Search & Knowledge Platform.

Global/Full-Text Search are the same engine (_run_search) over different default entity
type sets — see search_repo's per-type query functions. AI Knowledge Assistance is
deterministic (tag/category overlap scoring, substring keyword matching) — no external
LLM calls, consistent with Phase 8's AI infrastructure.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import search_repo as repo
from backend.schemas import (
    ContextSuggestionOut,
    KbArticleCreate,
    KbArticleOut,
    KbArticlePatch,
    KbArticleVersionOut,
    KbAttachmentCreate,
    KbAttachmentOut,
    KbCategoryCreate,
    KbCategoryOut,
    KbCategoryPatch,
    KnowledgeSummaryOut,
    Page,
    RelatedArticleOut,
    SavedSearchCreate,
    SavedSearchOut,
    SavedSearchPatch,
    SearchAnalyticsOut,
    SearchDashboardOut,
    SearchHistoryOut,
    SearchResponseOut,
    SearchResultOut,
)
from config.enums import FULL_TEXT_ENTITY_TYPES, GLOBAL_SEARCH_ENTITY_TYPES, KB_ARTICLE_STATUSES

from backend.timeutil import utc as _utc, utcnow as _utcnow


def _is_manager(user) -> bool:
    return getattr(user, "role", "member") in ("admin", "manager")


def _require_manager(user) -> None:
    if not _is_manager(user):
        raise HTTPException(403, "manager or admin required")


# ================================================================== relevance scoring
def _score(title: str, q: str) -> float:
    t, needle = (title or "").lower(), q.lower()
    if not needle:
        return 0.0
    if t == needle:
        return 100.0
    if t.startswith(needle):
        return 80.0
    if needle in t:
        return 50.0
    return 10.0


_SEARCH_DISPATCH = {
    "company": repo.search_companies,
    "contact": repo.search_contacts,
    "deal": repo.search_deals,
    "customer": repo.search_customers,
    "opportunity": repo.search_opportunities,
    "campaign": repo.search_campaigns,
    "workflow": repo.search_workflows,
    "custom_object": repo.search_custom_objects,
    "activity": repo.search_activities,
    "task": repo.search_tasks,
    "meeting": repo.search_meetings,
    "ai_insight": repo.search_ai_insights,
    "kb_article": repo.search_kb_articles,
    "note": repo.search_notes,
    "comment": repo.search_comments,
    "ai_summary": repo.search_ai_summaries,
}
_ALL_TYPES = set(_SEARCH_DISPATCH)


def _run_search(session: Session, q: str, entity_types: list[str]) -> list[SearchResultOut]:
    results = []
    for et in entity_types:
        fn = _SEARCH_DISPATCH.get(et)
        if not fn:
            continue
        for entity_id, title, snippet in fn(session, q):
            results.append(SearchResultOut(
                entity_type=et, entity_id=entity_id, title=title or "",
                snippet=(snippet or "")[:200], score=_score(title or "", q),
            ))
    results.sort(key=lambda r: r.score, reverse=True)
    return results


def _execute(session: Session, user, *, q: str, entity_types: list[str] | None, default_types: tuple[str, ...], sort: str, limit: int, offset: int) -> SearchResponseOut:
    t0 = time.monotonic()
    types = [t for t in (entity_types or list(default_types)) if t in _ALL_TYPES]
    results = _run_search(session, q, types) if q else []
    if sort == "title":
        results.sort(key=lambda r: r.title.lower())
    total = len(results)
    page = results[offset:offset + limit]
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    repo.log_search(session, user_id=getattr(user, "id", None), query_text=q, entity_types=types, result_count=total, response_time_ms=elapsed_ms)
    session.commit()
    return SearchResponseOut(query=q, results=page, total=total, response_time_ms=elapsed_ms)


def global_search(session: Session, user, *, q: str, entity_types: list[str] | None = None, sort: str = "relevance", limit: int = 20, offset: int = 0) -> SearchResponseOut:
    return _execute(session, user, q=q, entity_types=entity_types, default_types=GLOBAL_SEARCH_ENTITY_TYPES, sort=sort, limit=limit, offset=offset)


def full_text_search(session: Session, user, *, q: str, entity_types: list[str] | None = None, sort: str = "relevance", limit: int = 20, offset: int = 0) -> SearchResponseOut:
    return _execute(session, user, q=q, entity_types=entity_types, default_types=FULL_TEXT_ENTITY_TYPES, sort=sort, limit=limit, offset=offset)


# ================================================================== saved searches
def _saved_search_out(s) -> SavedSearchOut:
    return SavedSearchOut(
        id=s.id, name=s.name, query=s.query or {}, owner_id=s.owner_id,
        is_favorite=s.is_favorite, is_shared=s.is_shared,
        created_at=_utc(s.created_at), updated_at=_utc(s.updated_at),
    )


def create_saved_search(session: Session, data: SavedSearchCreate, user) -> SavedSearchOut:
    s = repo.create_saved_search(session, name=data.name, query=data.query, owner_id=user.id, is_favorite=data.is_favorite, is_shared=data.is_shared)
    session.commit()
    return _saved_search_out(s)


def list_saved_searches(session: Session, user, *, favorites_only: bool = False) -> list[SavedSearchOut]:
    return [_saved_search_out(s) for s in repo.list_saved_searches(session, owner_id=user.id, favorites_only=favorites_only)]


def patch_saved_search(session: Session, search_id: int, data: SavedSearchPatch, user) -> SavedSearchOut:
    s = repo.get_saved_search(session, search_id)
    if not s:
        raise HTTPException(404, "saved search not found")
    if s.owner_id != user.id and not _is_manager(user):
        raise HTTPException(403, "only the owner or a manager may edit this saved search")
    for field in ("name", "query", "is_favorite", "is_shared"):
        val = getattr(data, field)
        if val is not None:
            setattr(s, field, val)
    session.commit()
    return _saved_search_out(s)


def delete_saved_search(session: Session, search_id: int, user) -> None:
    s = repo.get_saved_search(session, search_id)
    if not s:
        raise HTTPException(404, "saved search not found")
    if s.owner_id != user.id and not _is_manager(user):
        raise HTTPException(403, "only the owner or a manager may delete this saved search")
    repo.delete_saved_search(session, search_id)
    session.commit()


def run_saved_search(session: Session, search_id: int, user, *, limit: int = 20, offset: int = 0) -> SearchResponseOut:
    s = repo.get_saved_search(session, search_id)
    if not s:
        raise HTTPException(404, "saved search not found")
    query = s.query or {}
    return global_search(session, user, q=query.get("q", ""), entity_types=query.get("entity_types"), limit=limit, offset=offset)


def _history_out(h) -> SearchHistoryOut:
    return SearchHistoryOut(
        id=h.id, query_text=h.query_text, entity_types=h.entity_types or [],
        result_count=h.result_count, response_time_ms=h.response_time_ms, created_at=_utc(h.created_at),
    )


def recent_searches(session: Session, user, *, limit: int = 10) -> list[SearchHistoryOut]:
    return [_history_out(h) for h in repo.recent_searches(session, user.id, limit=limit)]


# ================================================================== knowledge base: categories
def _category_out(c) -> KbCategoryOut:
    return KbCategoryOut(
        id=c.id, name=c.name, description=c.description, parent_id=c.parent_id,
        created_at=_utc(c.created_at), updated_at=_utc(c.updated_at),
    )


def create_category(session: Session, data: KbCategoryCreate, user) -> KbCategoryOut:
    _require_manager(user)
    c = repo.create_category(session, name=data.name, description=data.description, parent_id=data.parent_id)
    session.commit()
    return _category_out(c)


def list_categories(session: Session, user) -> list[KbCategoryOut]:
    return [_category_out(c) for c in repo.list_categories(session)]


def patch_category(session: Session, category_id: int, data: KbCategoryPatch, user) -> KbCategoryOut:
    _require_manager(user)
    c = repo.get_category(session, category_id)
    if not c:
        raise HTTPException(404, "category not found")
    for field in ("name", "description", "parent_id"):
        val = getattr(data, field)
        if val is not None:
            setattr(c, field, val)
    session.commit()
    return _category_out(c)


def delete_category(session: Session, category_id: int, user) -> None:
    _require_manager(user)
    if not repo.delete_category(session, category_id):
        raise HTTPException(404, "category not found")
    session.commit()


# ================================================================== knowledge base: articles
def _article_out(a) -> KbArticleOut:
    return KbArticleOut(
        id=a.id, category_id=a.category_id, title=a.title, body=a.body, status=a.status,
        tags=a.tags or [], owner_id=a.owner_id, version=a.version, view_count=a.view_count,
        created_by=a.created_by, created_at=_utc(a.created_at), updated_at=_utc(a.updated_at),
        published_at=_utc(a.published_at),
    )


def create_article(session: Session, data: KbArticleCreate, user) -> KbArticleOut:
    a = repo.create_article(
        session, category_id=data.category_id, title=data.title, body=data.body,
        tags=data.tags, owner_id=user.id, created_by=user.id, status="draft",
    )
    session.commit()
    return _article_out(a)


def get_article(session: Session, article_id: int, user, *, log_view: bool = True) -> KbArticleOut:
    a = repo.get_article(session, article_id)
    if not a:
        raise HTTPException(404, "article not found")
    if log_view:
        repo.log_article_view(session, article_id, getattr(user, "id", None))
        a.view_count += 1
        session.commit()
    return _article_out(a)


def list_articles(session: Session, user, *, category_id: int | None = None, status: str | None = None, owner_id: int | None = None, limit: int = 50, offset: int = 0) -> Page:
    rows, total = repo.list_articles(session, category_id=category_id, status=status, owner_id=owner_id, limit=limit, offset=offset)
    return Page.build([_article_out(a) for a in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


def _require_owner_or_manager(a, user) -> None:
    if a.owner_id != user.id and not _is_manager(user):
        raise HTTPException(403, "only the article owner or a manager may modify this article")


def patch_article(session: Session, article_id: int, data: KbArticlePatch, user) -> KbArticleOut:
    """Field edits only — status transitions go through submit/publish/archive below,
    which enforce the draft -> pending_approval -> published -> archived lifecycle."""
    a = repo.get_article(session, article_id)
    if not a:
        raise HTTPException(404, "article not found")
    _require_owner_or_manager(a, user)
    if data.status is not None:
        raise HTTPException(422, "use /submit, /publish, or /archive to change status")
    changing_content = (data.title is not None and data.title != a.title) or (data.body is not None and data.body != a.body)
    if changing_content:
        repo.create_version(session, article_id=a.id, version=a.version, title=a.title, body=a.body, edited_by=user.id)
        a.version += 1
    for field in ("title", "body", "category_id", "tags"):
        val = getattr(data, field)
        if val is not None:
            setattr(a, field, val)
    session.commit()
    return _article_out(a)


def submit_for_approval(session: Session, article_id: int, user) -> KbArticleOut:
    a = repo.get_article(session, article_id)
    if not a:
        raise HTTPException(404, "article not found")
    _require_owner_or_manager(a, user)
    if a.status != "draft":
        raise HTTPException(409, f"cannot submit an article in status {a.status!r}")
    a.status = "pending_approval"
    session.commit()
    return _article_out(a)


def publish_article(session: Session, article_id: int, user) -> KbArticleOut:
    _require_manager(user)
    a = repo.get_article(session, article_id)
    if not a:
        raise HTTPException(404, "article not found")
    if a.status not in ("pending_approval", "draft"):
        raise HTTPException(409, f"cannot publish an article in status {a.status!r}")
    a.status = "published"
    a.published_at = _utcnow()
    session.commit()
    return _article_out(a)


def archive_article(session: Session, article_id: int, user) -> KbArticleOut:
    a = repo.get_article(session, article_id)
    if not a:
        raise HTTPException(404, "article not found")
    _require_owner_or_manager(a, user)
    a.status = "archived"
    session.commit()
    return _article_out(a)


def delete_article(session: Session, article_id: int, user) -> None:
    a = repo.get_article(session, article_id)
    if not a:
        raise HTTPException(404, "article not found")
    _require_owner_or_manager(a, user)
    repo.delete_article(session, article_id)
    session.commit()


def list_versions(session: Session, article_id: int, user) -> list[KbArticleVersionOut]:
    return [
        KbArticleVersionOut(id=v.id, article_id=v.article_id, version=v.version, title=v.title, body=v.body, edited_by=v.edited_by, created_at=_utc(v.created_at))
        for v in repo.list_versions(session, article_id)
    ]


def add_attachment(session: Session, article_id: int, data: KbAttachmentCreate, user) -> KbAttachmentOut:
    if not repo.get_article(session, article_id):
        raise HTTPException(404, "article not found")
    att = repo.create_attachment(session, article_id=article_id, filename=data.filename, content_type=data.content_type, size_bytes=data.size_bytes, uploaded_by=user.id)
    session.commit()
    return KbAttachmentOut(id=att.id, article_id=att.article_id, filename=att.filename, content_type=att.content_type, size_bytes=att.size_bytes, uploaded_by=att.uploaded_by, created_at=_utc(att.created_at))


def list_attachments(session: Session, article_id: int, user) -> list[KbAttachmentOut]:
    return [
        KbAttachmentOut(id=a.id, article_id=a.article_id, filename=a.filename, content_type=a.content_type, size_bytes=a.size_bytes, uploaded_by=a.uploaded_by, created_at=_utc(a.created_at))
        for a in repo.list_attachments(session, article_id)
    ]


# ================================================================== AI knowledge assistance (deterministic)
def _tag_overlap_score(a, tags: set[str], category_id: int | None) -> float:
    score = float(len(set(a.tags or []) & tags) * 10)
    if category_id is not None and a.category_id == category_id:
        score += 5.0
    return score


def related_articles(session: Session, article_id: int, user, *, limit: int = 5) -> list[RelatedArticleOut]:
    a = repo.get_article(session, article_id)
    if not a:
        raise HTTPException(404, "article not found")
    tags = set(a.tags or [])
    scored = [(c, _tag_overlap_score(c, tags, a.category_id)) for c in repo.published_articles(session, exclude_id=article_id)]
    scored = sorted((cs for cs in scored if cs[1] > 0), key=lambda cs: cs[1], reverse=True)[:limit]
    return [
        RelatedArticleOut(article_id=c.id, title=c.title, score=s, reason="shared tags" if set(c.tags or []) & tags else "same category")
        for c, s in scored
    ]


def context_suggestions(session: Session, entity_type: str, entity_id: str, user, *, limit: int = 5) -> ContextSuggestionOut:
    """Deterministic keyword heuristic: articles tagged with entity_type, or whose title
    mentions it. ponytail: no embeddings/semantic search — upgrade path if this proves
    too coarse in practice."""
    scored = []
    for c in repo.published_articles(session, limit=200):
        s = 0.0
        if entity_type in (c.tags or []):
            s += 10.0
        if entity_type.lower() in c.title.lower():
            s += 5.0
        if s > 0:
            scored.append((c, s))
    scored.sort(key=lambda cs: cs[1], reverse=True)
    return ContextSuggestionOut(
        entity_type=entity_type, entity_id=str(entity_id),
        articles=[RelatedArticleOut(article_id=c.id, title=c.title, score=s, reason="tag/title match") for c, s in scored[:limit]],
    )


def similar_records(session: Session, user, *, entity_type: str, q: str, limit: int = 5) -> list[SearchResultOut]:
    if entity_type not in GLOBAL_SEARCH_ENTITY_TYPES:
        raise HTTPException(422, f"invalid entity_type: {entity_type}")
    return _run_search(session, q, [entity_type])[:limit]


def knowledge_summary(session: Session, article_id: int, user) -> KnowledgeSummaryOut:
    a = repo.get_article(session, article_id)
    if not a:
        raise HTTPException(404, "article not found")
    body = a.body or ""
    summary = body[:280] + ("..." if len(body) > 280 else "")
    return KnowledgeSummaryOut(article_id=a.id, title=a.title, summary=summary, tags=a.tags or [], view_count=a.view_count)


# ================================================================== dashboard + analytics
def search_dashboard(session: Session, user) -> SearchDashboardOut:
    recent = repo.recent_searches(session, user.id, limit=10)
    popular = repo.popular_searches(session, limit=10)
    stats = repo.search_stats(session)
    status_counts = repo.article_status_counts(session)
    top = repo.top_articles_by_views(session, limit=5)
    return SearchDashboardOut(
        recent_searches=[_history_out(h) for h in recent],
        popular_searches=[q for q, _ in popular],
        knowledge_activity=status_counts,
        avg_response_time_ms=stats["avg_response_ms"],
        top_articles=[_article_out(a) for a in top],
    )


def search_analytics(session: Session, user) -> SearchAnalyticsOut:
    stats = repo.search_stats(session)
    popular = repo.popular_searches(session, limit=20)
    since = _utcnow() - timedelta(days=30)
    recent_view_counts = repo.article_view_counts_since(session, since)
    all_articles = {a.id: a for a in repo.top_articles_by_views(session, limit=100)}
    article_views = {all_articles[aid].title: cnt for aid, cnt in recent_view_counts.items() if aid in all_articles}
    article_usage = {a.title: a.view_count for a in all_articles.values()}
    return SearchAnalyticsOut(
        search_volume=stats["total"], zero_result_searches=stats["zero_result"],
        popular_records=dict(popular), article_views=article_views, article_usage=article_usage,
        avg_search_response_ms=stats["avg_response_ms"],
    )
