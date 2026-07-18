from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import services
from backend.dependencies import Pagination, get_session, pagination
from backend.schemas import LeadershipSignalOut, LeadershipSignalUpdate, Page
from backend.security import require_admin
from master_db.models import User

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


@router.patch("/{signal_id}", response_model=LeadershipSignalOut,
              summary="Edit a leadership signal's fields (admin only)")
def update_leadership_signal(
    signal_id: str,
    body: LeadershipSignalUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_admin),
):
    return services.update_leadership_signal(session, signal_id, body.model_dump(exclude_unset=True))


@router.delete("/{signal_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Permanently delete a leadership signal (admin only)")
def delete_leadership_signal(
    signal_id: str,
    session: Session = Depends(get_session),
    _: User = Depends(require_admin),
):
    services.delete_leadership_signal(session, signal_id)
