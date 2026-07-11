"""Data access for Enterprise CRM Phase 11: Enterprise Search & Knowledge Platform.

Global/full-text search is federated: each entity type gets a small dedicated query
function returning plain (id, title, snippet) rows via a case-insensitive substring
match on its existing table (no new search index infrastructure — reuses the existing
tables and their existing indexes on id/name columns). search_service merges and ranks
the per-type results in Python.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from master_db.models import (
    AiCopilotQuery,
    AiInsight,
    Campaign,
    Company,
    CrmComment,
    CrmDeal,
    CsAccount,
    CustomObject,
    DecisionMaker,
    KbArticle,
    KbArticleVersion,
    KbArticleView,
    KbAttachment,
    KbCategory,
    Opportunity,
    OutreachActivity,
    OutreachMeeting,
    OutreachTask,
    SavedSearch,
    SearchHistory,
    Workflow,
)

_ROW_LIMIT = 25  # ponytail: per-type candidate cap before ranking/merge — plenty at this data scale


# ----------------------------------------------------------------- federated search (one fn per type)
def search_companies(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(
        select(Company).where(or_(Company.company_name.ilike(f"%{q}%"), Company.company_domain.ilike(f"%{q}%")))
        .limit(_ROW_LIMIT)
    )
    return [(r.company_domain, r.company_name, r.company_domain) for r in rows]


def search_contacts(session: Session, q: str) -> list[tuple[str, str, str]]:
    like = f"%{q}%"
    rows = session.scalars(
        select(DecisionMaker).where(or_(
            DecisionMaker.full_name.ilike(like), DecisionMaker.first_name.ilike(like),
            DecisionMaker.last_name.ilike(like), DecisionMaker.headline.ilike(like),
        )).limit(_ROW_LIMIT)
    )
    return [(str(r.id), r.full_name or f"{r.first_name} {r.last_name}".strip(), r.headline) for r in rows]


def search_deals(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(select(CrmDeal).where(CrmDeal.title.ilike(f"%{q}%")).limit(_ROW_LIMIT))
    return [(str(r.id), r.title, r.company_domain) for r in rows]


def search_customers(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(select(CsAccount).where(CsAccount.name.ilike(f"%{q}%")).limit(_ROW_LIMIT))
    return [(str(r.id), r.name, r.company_domain or "") for r in rows]


def search_opportunities(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(select(Opportunity).where(Opportunity.article_title.ilike(f"%{q}%")).limit(_ROW_LIMIT))
    return [(r.opportunity_id, r.article_title, r.company_name) for r in rows]


def search_campaigns(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(select(Campaign).where(Campaign.name.ilike(f"%{q}%")).limit(_ROW_LIMIT))
    return [(str(r.id), r.name, r.status) for r in rows]


def search_workflows(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(select(Workflow).where(Workflow.name.ilike(f"%{q}%")).limit(_ROW_LIMIT))
    return [(str(r.id), r.name, r.trigger_event) for r in rows]


def search_custom_objects(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(
        select(CustomObject).where(or_(CustomObject.name.ilike(f"%{q}%"), CustomObject.description.ilike(f"%{q}%")))
        .limit(_ROW_LIMIT)
    )
    return [(str(r.id), r.name, r.description[:200]) for r in rows]


def search_activities(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(select(OutreachActivity).where(OutreachActivity.detail.ilike(f"%{q}%")).limit(_ROW_LIMIT))
    return [(str(r.id), r.type, r.detail[:200]) for r in rows]


def search_tasks(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(select(OutreachTask).where(OutreachTask.title.ilike(f"%{q}%")).limit(_ROW_LIMIT))
    return [(str(r.id), r.title, r.status) for r in rows]


def search_meetings(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(select(OutreachMeeting).where(OutreachMeeting.title.ilike(f"%{q}%")).limit(_ROW_LIMIT))
    return [(str(r.id), r.title, r.meeting_type) for r in rows]


def search_ai_insights(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(
        select(AiInsight).where(or_(AiInsight.title.ilike(f"%{q}%"), AiInsight.detail.ilike(f"%{q}%")))
        .limit(_ROW_LIMIT)
    )
    return [(str(r.id), r.title, r.detail[:200]) for r in rows]


# ----------------------------------------------------------------- full-text-only entity types
def search_kb_articles(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(
        select(KbArticle).where(and_(
            KbArticle.status == "published",
            or_(KbArticle.title.ilike(f"%{q}%"), KbArticle.body.ilike(f"%{q}%")),
        )).limit(_ROW_LIMIT)
    )
    return [(str(r.id), r.title, r.body[:200]) for r in rows]


def search_notes(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(select(CrmDeal).where(CrmDeal.notes.ilike(f"%{q}%")).limit(_ROW_LIMIT))
    return [(str(r.id), r.title, r.notes[:200]) for r in rows]


def search_comments(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(select(CrmComment).where(CrmComment.body.ilike(f"%{q}%")).limit(_ROW_LIMIT))
    return [(str(r.id), f"{r.entity_type}#{r.entity_id}", r.body[:200]) for r in rows]


def search_ai_summaries(session: Session, q: str) -> list[tuple[str, str, str]]:
    rows = session.scalars(select(AiCopilotQuery).where(AiCopilotQuery.response_summary.ilike(f"%{q}%")).limit(_ROW_LIMIT))
    return [(str(r.id), r.query_type, r.response_summary[:200]) for r in rows]


# ----------------------------------------------------------------- saved searches
def create_saved_search(session: Session, **kw) -> SavedSearch:
    s = SavedSearch(**kw)
    session.add(s)
    session.flush()
    return s


def get_saved_search(session: Session, search_id: int) -> SavedSearch | None:
    return session.get(SavedSearch, search_id)


def list_saved_searches(session: Session, *, owner_id: int, favorites_only: bool = False) -> list[SavedSearch]:
    """Visible to the owner, plus every shared search from anyone. 1 query."""
    q = select(SavedSearch).where(or_(SavedSearch.owner_id == owner_id, SavedSearch.is_shared.is_(True)))
    if favorites_only:
        q = q.where(SavedSearch.is_favorite.is_(True))
    return list(session.scalars(q.order_by(SavedSearch.id.desc())))


def delete_saved_search(session: Session, search_id: int) -> bool:
    s = session.get(SavedSearch, search_id)
    if not s:
        return False
    session.delete(s)
    return True


# ----------------------------------------------------------------- search history
def log_search(session: Session, **kw) -> SearchHistory:
    h = SearchHistory(**kw)
    session.add(h)
    session.flush()
    return h


def recent_searches(session: Session, user_id: int, *, limit: int = 10) -> list[SearchHistory]:
    return list(session.scalars(
        select(SearchHistory).where(SearchHistory.user_id == user_id)
        .order_by(SearchHistory.id.desc()).limit(limit)
    ))


def popular_searches(session: Session, *, limit: int = 10) -> list[tuple[str, int]]:
    """(query_text, count) ordered by frequency. 1 query."""
    rows = session.execute(
        select(SearchHistory.query_text, func.count(SearchHistory.id).label("cnt"))
        .where(SearchHistory.query_text != "")
        .group_by(SearchHistory.query_text)
        .order_by(func.count(SearchHistory.id).desc())
        .limit(limit)
    ).all()
    return [(r[0], r[1]) for r in rows]


def search_stats(session: Session) -> dict:
    """Total searches / zero-result count / avg response time. 1 query."""
    row = session.execute(
        select(
            func.count(SearchHistory.id),
            func.count(SearchHistory.id).filter(SearchHistory.result_count == 0),
            func.coalesce(func.avg(SearchHistory.response_time_ms), 0),
        )
    ).one()
    total, zero_result, avg_ms = row
    return {"total": total, "zero_result": zero_result, "avg_response_ms": float(avg_ms)}


# ----------------------------------------------------------------- knowledge base: categories
def create_category(session: Session, **kw) -> KbCategory:
    c = KbCategory(**kw)
    session.add(c)
    session.flush()
    return c


def get_category(session: Session, category_id: int) -> KbCategory | None:
    return session.get(KbCategory, category_id)


def list_categories(session: Session) -> list[KbCategory]:
    return list(session.scalars(select(KbCategory).order_by(KbCategory.name)))


def delete_category(session: Session, category_id: int) -> bool:
    c = session.get(KbCategory, category_id)
    if not c:
        return False
    session.delete(c)
    return True


# ----------------------------------------------------------------- knowledge base: articles
def create_article(session: Session, **kw) -> KbArticle:
    a = KbArticle(**kw)
    session.add(a)
    session.flush()
    return a


def get_article(session: Session, article_id: int) -> KbArticle | None:
    return session.get(KbArticle, article_id)


def list_articles(
    session: Session, *, category_id: int | None = None, status: str | None = None,
    owner_id: int | None = None, limit: int = 50, offset: int = 0,
) -> tuple[list[KbArticle], int]:
    q = select(KbArticle)
    filters = []
    if category_id is not None:
        filters.append(KbArticle.category_id == category_id)
    if status:
        filters.append(KbArticle.status == status)
    if owner_id is not None:
        filters.append(KbArticle.owner_id == owner_id)
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(KbArticle.id.desc()).limit(limit).offset(offset)))
    return rows, total


def delete_article(session: Session, article_id: int) -> bool:
    a = session.get(KbArticle, article_id)
    if not a:
        return False
    session.delete(a)
    return True


def published_articles(session: Session, *, exclude_id: int | None = None, limit: int = 100) -> list[KbArticle]:
    """Candidate pool for Related Articles / Context Suggestions — tag-overlap and
    category-match scoring happens in Python (search_service) after this bounded fetch;
    JSON-array containment isn't portably indexable across SQLite/Postgres at this
    article-count scale."""
    q = select(KbArticle).where(KbArticle.status == "published")
    if exclude_id is not None:
        q = q.where(KbArticle.id != exclude_id)
    return list(session.scalars(q.order_by(KbArticle.id.desc()).limit(limit)))


def create_version(session: Session, **kw) -> KbArticleVersion:
    v = KbArticleVersion(**kw)
    session.add(v)
    session.flush()
    return v


def list_versions(session: Session, article_id: int) -> list[KbArticleVersion]:
    return list(session.scalars(
        select(KbArticleVersion).where(KbArticleVersion.article_id == article_id).order_by(KbArticleVersion.version.desc())
    ))


def create_attachment(session: Session, **kw) -> KbAttachment:
    a = KbAttachment(**kw)
    session.add(a)
    session.flush()
    return a


def list_attachments(session: Session, article_id: int) -> list[KbAttachment]:
    return list(session.scalars(select(KbAttachment).where(KbAttachment.article_id == article_id)))


def log_article_view(session: Session, article_id: int, viewed_by: int | None) -> None:
    session.add(KbArticleView(article_id=article_id, viewed_by=viewed_by))


def article_view_counts_since(session: Session, since: datetime) -> dict[int, int]:
    rows = session.execute(
        select(KbArticleView.article_id, func.count(KbArticleView.id))
        .where(KbArticleView.created_at >= since)
        .group_by(KbArticleView.article_id)
    ).all()
    return {r[0]: r[1] for r in rows}


def top_articles_by_views(session: Session, *, limit: int = 10) -> list[KbArticle]:
    return list(session.scalars(select(KbArticle).order_by(KbArticle.view_count.desc()).limit(limit)))


def article_status_counts(session: Session) -> dict[str, int]:
    rows = session.execute(select(KbArticle.status, func.count(KbArticle.id)).group_by(KbArticle.status)).all()
    return {r[0]: r[1] for r in rows}
