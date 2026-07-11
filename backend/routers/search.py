"""Enterprise CRM Phase 11: Enterprise Search & Knowledge Platform endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import search_service as svc
from backend.dependencies import get_session
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
from backend.security import get_current_user
from master_db.models import User

search_router = APIRouter(prefix="/search", tags=["search"])
knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ============================================================ global / full-text search
@search_router.get("", response_model=SearchResponseOut)
def global_search(
    q: str = Query(""), entity_types: list[str] | None = Query(None),
    sort: str = Query("relevance"), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.global_search(session, user, q=q, entity_types=entity_types, sort=sort, limit=limit, offset=offset)


@search_router.get("/full-text", response_model=SearchResponseOut)
def full_text_search(
    q: str = Query(""), entity_types: list[str] | None = Query(None),
    sort: str = Query("relevance"), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.full_text_search(session, user, q=q, entity_types=entity_types, sort=sort, limit=limit, offset=offset)


@search_router.get("/similar-records", response_model=list[SearchResultOut])
def similar_records(
    entity_type: str = Query(...), q: str = Query(...), limit: int = Query(5, ge=1, le=50),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.similar_records(session, user, entity_type=entity_type, q=q, limit=limit)


@search_router.get("/recent", response_model=list[SearchHistoryOut])
def recent_searches(
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.recent_searches(session, user, limit=limit)


# ============================================================ saved searches
@search_router.get("/saved", response_model=list[SavedSearchOut])
def list_saved_searches(
    favorites_only: bool = Query(False),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_saved_searches(session, user, favorites_only=favorites_only)


@search_router.post("/saved", response_model=SavedSearchOut, status_code=status.HTTP_201_CREATED)
def create_saved_search(
    data: SavedSearchCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_saved_search(session, data, user)


@search_router.patch("/saved/{search_id}", response_model=SavedSearchOut)
def patch_saved_search(
    search_id: int, data: SavedSearchPatch,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.patch_saved_search(session, search_id, data, user)


@search_router.delete("/saved/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_search(
    search_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    svc.delete_saved_search(session, search_id, user)


@search_router.post("/saved/{search_id}/run", response_model=SearchResponseOut)
def run_saved_search(
    search_id: int, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.run_saved_search(session, search_id, user, limit=limit, offset=offset)


# ============================================================ search dashboard + analytics
@search_router.get("/dashboard/summary", response_model=SearchDashboardOut)
def search_dashboard(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.search_dashboard(session, user)


@search_router.get("/analytics/summary", response_model=SearchAnalyticsOut)
def search_analytics(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.search_analytics(session, user)


# ============================================================ knowledge base: categories
@knowledge_router.get("/categories", response_model=list[KbCategoryOut])
def list_categories(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_categories(session, user)


@knowledge_router.post("/categories", response_model=KbCategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    data: KbCategoryCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_category(session, data, user)


@knowledge_router.patch("/categories/{category_id}", response_model=KbCategoryOut)
def patch_category(
    category_id: int, data: KbCategoryPatch,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.patch_category(session, category_id, data, user)


@knowledge_router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    svc.delete_category(session, category_id, user)


# ============================================================ knowledge base: articles
@knowledge_router.get("/articles", response_model=Page)
def list_articles(
    category_id: int | None = Query(None), status_: str | None = Query(None, alias="status"),
    owner_id: int | None = Query(None), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_articles(session, user, category_id=category_id, status=status_, owner_id=owner_id, limit=limit, offset=offset)


@knowledge_router.post("/articles", response_model=KbArticleOut, status_code=status.HTTP_201_CREATED)
def create_article(
    data: KbArticleCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_article(session, data, user)


@knowledge_router.get("/articles/{article_id}", response_model=KbArticleOut)
def get_article(
    article_id: int, log_view: bool = Query(True),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.get_article(session, article_id, user, log_view=log_view)


@knowledge_router.patch("/articles/{article_id}", response_model=KbArticleOut)
def patch_article(
    article_id: int, data: KbArticlePatch,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.patch_article(session, article_id, data, user)


@knowledge_router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    svc.delete_article(session, article_id, user)


@knowledge_router.post("/articles/{article_id}/submit", response_model=KbArticleOut)
def submit_for_approval(
    article_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.submit_for_approval(session, article_id, user)


@knowledge_router.post("/articles/{article_id}/publish", response_model=KbArticleOut)
def publish_article(
    article_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.publish_article(session, article_id, user)


@knowledge_router.post("/articles/{article_id}/archive", response_model=KbArticleOut)
def archive_article(
    article_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.archive_article(session, article_id, user)


@knowledge_router.get("/articles/{article_id}/versions", response_model=list[KbArticleVersionOut])
def list_versions(
    article_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_versions(session, article_id, user)


@knowledge_router.get("/articles/{article_id}/related", response_model=list[RelatedArticleOut])
def related_articles(
    article_id: int, limit: int = Query(5, ge=1, le=20),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.related_articles(session, article_id, user, limit=limit)


@knowledge_router.get("/articles/{article_id}/summary", response_model=KnowledgeSummaryOut)
def knowledge_summary(
    article_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.knowledge_summary(session, article_id, user)


@knowledge_router.post("/articles/{article_id}/attachments", response_model=KbAttachmentOut, status_code=status.HTTP_201_CREATED)
def add_attachment(
    article_id: int, data: KbAttachmentCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.add_attachment(session, article_id, data, user)


@knowledge_router.get("/articles/{article_id}/attachments", response_model=list[KbAttachmentOut])
def list_attachments(
    article_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_attachments(session, article_id, user)


# ============================================================ AI knowledge assistance
@knowledge_router.get("/context-suggestions", response_model=ContextSuggestionOut)
def context_suggestions(
    entity_type: str = Query(...), entity_id: str = Query(...), limit: int = Query(5, ge=1, le=20),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.context_suggestions(session, entity_type, entity_id, user, limit=limit)
