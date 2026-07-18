from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from backend import services
from backend.dependencies import Pagination, get_session, pagination, sort_order
from backend.repositories import COMPANY_SORT_FIELDS
from backend.schemas import CompanyCreate, CompanyProfile, CompanySummary, CompanyUpdate, Page
from backend.security import require_admin, require_manager
from master_db.models import User

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


@router.post("", response_model=CompanySummary, status_code=201,
             summary="Manually add a company to the universe (manager+)")
def create_company(
    body: CompanyCreate,
    session: Session = Depends(get_session),
    actor: User = Depends(require_manager),
):
    return services.create_company(session, payload=body, actor=actor)


@router.get("/{domain}", response_model=CompanyProfile, summary="Unified company profile")
def company_profile(
    domain: str = Path(..., description="company_domain, e.g. tenstorrent.com"),
    session: Session = Depends(get_session),
):
    return services.get_company_profile(session, domain)


@router.patch("/{domain}", response_model=CompanySummary,
              summary="Edit a company's descriptive fields (admin only)")
def update_company(
    body: CompanyUpdate,
    domain: str = Path(..., description="company_domain"),
    session: Session = Depends(get_session),
    _: User = Depends(require_admin),
):
    return services.update_company(session, domain, body.model_dump(exclude_unset=True))


@router.delete("/{domain}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Permanently delete a company + its dependent data (admin only)")
def delete_company(
    domain: str = Path(..., description="company_domain"),
    session: Session = Depends(get_session),
    _: User = Depends(require_admin),
):
    services.delete_company(session, domain)
