from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import news_service, services
from backend.dependencies import Pagination, get_session, pagination
from backend.schemas import (
    NewsSeedResult,
    NewsSourceIn,
    NewsSourceOut,
    NewsSourcePatch,
    OpportunityDetailOut,
    OpportunityOut,
    OpportunityReviewIn,
    OpportunityUpdate,
    Page,
)
from backend.security import get_current_user, require_admin, require_manager
from master_db.models import User

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=Page[OpportunityOut], summary="List/filter opportunities")
def list_opportunities(
    session: Session = Depends(get_session),
    page: Pagination = Depends(pagination),
    opportunity_type: str | None = Query(None, description="Filter by opportunity_type"),
    company_domain: str | None = Query(None, description="Filter by company"),
    date_from: str | None = Query(None, description="published_date >= (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="published_date <= (YYYY-MM-DD)"),
    lifecycle_status: str | None = Query(None, description="Filter by lifecycle (NEW/ACTIVE/...)"),
    hide_archived: bool = Query(False, description="Hide archived / not-relevant events"),
    sort: str | None = Query(None, description="Order: newest | oldest | score (default score)"),
    annual_lists_only: bool = Query(False, description="Return only ANNUAL_LIST appearances"),
    company_news_only: bool = Query(False, description="Return only company-news / people-move entries"),
    signal_category: str | None = Query(
        None, description="First-class signal category: LEADERSHIP | NEWS. Leadership "
                          "people-movement events are separated out of the NEWS feed."),
):
    return services.list_opportunities(
        session, pagination=page, opportunity_type=opportunity_type,
        company_domain=company_domain, date_from=date_from, date_to=date_to,
        lifecycle_status=lifecycle_status, hide_archived=hide_archived, sort=sort,
        annual_lists_only=annual_lists_only, company_news_only=company_news_only,
        signal_category=signal_category,
    )


# Static sub-paths declared BEFORE the dynamic {opportunity_id} route so they win.
@router.get("/news-sources", response_model=list[NewsSourceOut], summary="Configured news sources")
def list_news_sources(session: Session = Depends(get_session)):
    return [NewsSourceOut.model_validate(s) for s in news_service.list_news_sources(session)]


@router.post("/news-sources", response_model=NewsSourceOut, status_code=201,
             summary="Add a news source (RSS / Google Alerts URL) — DB-driven config")
def create_news_source(
    body: NewsSourceIn,
    session: Session = Depends(get_session),
    _: User = Depends(require_manager),
):
    return NewsSourceOut.model_validate(news_service.create_news_source(
        session, name=body.name, adapter_type=body.adapter_type, url=body.url,
        publisher=body.publisher, credibility=body.credibility, enabled=body.enabled))


@router.patch("/news-sources/{source_id}", response_model=NewsSourceOut,
              summary="Update / enable / disable a news source")
def update_news_source(
    source_id: int,
    body: NewsSourcePatch,
    session: Session = Depends(get_session),
    _: User = Depends(require_manager),
):
    return NewsSourceOut.model_validate(news_service.update_news_source(
        session, source_id, patch=body.model_dump(exclude_unset=True)))


@router.post("/news-sources/seed", response_model=NewsSeedResult,
             summary="Idempotently seed the curated production news feeds")
def seed_news_sources(
    session: Session = Depends(get_session),
    _: User = Depends(require_manager),
):
    return NewsSeedResult(**news_service.seed_default_sources(session))


@router.get("/{opportunity_id}", response_model=OpportunityDetailOut,
            summary="Full opportunity intelligence (summaries, entities, sources, related, timeline, reviews)")
def get_opportunity(opportunity_id: str, session: Session = Depends(get_session)):
    return news_service.get_opportunity_detail(session, opportunity_id)


@router.post("/{opportunity_id}/review", response_model=OpportunityDetailOut,
             summary="Apply a manual-review action (not_relevant/merge/split/change_type/archive/restore/note)")
def review_opportunity(
    opportunity_id: str,
    body: OpportunityReviewIn,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return news_service.review_opportunity(
        session, opportunity_id, action=body.action, actor_email=user.email,
        detail=body.detail, target_opportunity_id=body.target_opportunity_id,
        new_type=body.new_type,
    )


@router.post("/{opportunity_id}/lifecycle", response_model=OpportunityDetailOut,
             summary="Set opportunity lifecycle (New/Active/Monitoring/Resolved/Archived)")
def set_lifecycle(
    opportunity_id: str,
    lifecycle_status: str = Query(..., description="NEW|ACTIVE|MONITORING|RESOLVED|ARCHIVED"),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return news_service.set_lifecycle(
        session, opportunity_id, lifecycle_status=lifecycle_status, actor_email=user.email)


@router.patch("/{opportunity_id}", response_model=OpportunityOut,
              summary="Edit an opportunity's fields (admin only)")
def update_opportunity(
    opportunity_id: str,
    body: OpportunityUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_admin),
):
    return services.update_opportunity(session, opportunity_id, body.model_dump(exclude_unset=True))


@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Permanently delete an opportunity (admin only)")
def delete_opportunity(
    opportunity_id: str,
    session: Session = Depends(get_session),
    _: User = Depends(require_admin),
):
    services.delete_opportunity(session, opportunity_id)
