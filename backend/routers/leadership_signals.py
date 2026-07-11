from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import services
from backend.dependencies import Pagination, get_session, pagination
from backend.schemas import LeadershipSignalOut, Page

router = APIRouter(prefix="/leadership-signals", tags=["leadership-signals"])


@router.get("", response_model=Page[LeadershipSignalOut],
            summary="List/filter person-level leadership-movement signals (director+)")
def list_leadership_signals(
    session: Session = Depends(get_session),
    page: Pagination = Depends(pagination),
    company_domain: str | None = Query(None, description="Filter by company"),
    movement_type: str | None = Query(
        None, description="promotion | role_change | new_executive_hire | executive_departure "
                          "| board_appointment | founder_change | executive_reshuffle"),
    seniority_band: str | None = Query(None, description="Filter by band (c_level, vp, director, ...)"),
    source: str | None = Query(None, description="linkedin_history | blog_event"),
):
    return services.list_leadership_signals(
        session, pagination=page, company_domain=company_domain,
        movement_type=movement_type, seniority_band=seniority_band, source=source,
    )
