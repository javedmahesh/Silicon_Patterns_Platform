from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import services
from backend.dependencies import Pagination, get_session, pagination
from backend.schemas import LeadOut, Page

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=Page[LeadOut], summary="Leads ranked by lead score")
def list_leads(
    session: Session = Depends(get_session),
    page: Pagination = Depends(pagination),
    grade: str | None = Query(None, description="Filter by grade (A+/A/B/C)"),
    tier: str | None = Query(None, description="Filter by company_tier"),
    prospect_type: str | None = Query(None, description="Filter by prospect_type"),
    sort: str = Query("model", pattern="^(model|human|combined)$",
                      description="Ranking: model score · human assessment · combined priority"),
):
    return services.list_leads(
        session, pagination=page, grade=grade, tier=tier, prospect_type=prospect_type, sort=sort
    )
