from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from backend import services
from backend.dependencies import Pagination, get_session, pagination, sort_order
from backend.repositories import COMPANY_SORT_FIELDS
from backend.schemas import CompanyProfile, CompanySummary, Page

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=Page[CompanySummary], summary="List/search/filter companies")
def list_companies(
    session: Session = Depends(get_session),
    page: Pagination = Depends(pagination),
    q: str | None = Query(None, description="Search by company name (substring, case-insensitive)"),
    domain: str | None = Query(None, description="Search by company_domain (substring)"),
    tier: str | None = Query(None, description="Filter by company_tier"),
    prospect_type: str | None = Query(None, description="Filter by prospect_type"),
    grade: str | None = Query(None, description="Filter by lead grade (A+/A/B/C)"),
    sort: str = Query("company_name", description=f"Sort field: {', '.join(COMPANY_SORT_FIELDS)}"),
    order: str = Depends(sort_order),
):
    if sort not in COMPANY_SORT_FIELDS:
        sort = "company_name"
    return services.list_companies(
        session, pagination=page, q=q, domain=domain, tier=tier,
        prospect_type=prospect_type, grade=grade, sort=sort, order=order,
    )


@router.get("/{domain}", response_model=CompanyProfile, summary="Unified company profile")
def company_profile(
    domain: str = Path(..., description="company_domain, e.g. tenstorrent.com"),
    session: Session = Depends(get_session),
):
    return services.get_company_profile(session, domain)
