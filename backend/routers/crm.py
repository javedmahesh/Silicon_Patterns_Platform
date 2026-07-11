from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import services
from backend.dependencies import get_session
from backend.schemas import ActivityItem, CompanyNoteIn, CompanyNoteOut
from backend.security import get_current_user
from master_db.models import User

# Company CRM sub-resources. Notes/activity are visible to ANY authenticated user
# (the platform is a shared intelligence repository); writing a note records the author.
router = APIRouter(prefix="/companies", tags=["crm"])


@router.get("/{domain}/notes", response_model=list[CompanyNoteOut], summary="Company notes")
def list_notes(domain: str, session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return services.list_company_notes(session, domain)


@router.post("/{domain}/notes", response_model=CompanyNoteOut, summary="Add a company note")
def add_note(domain: str, payload: CompanyNoteIn, session: Session = Depends(get_session),
             actor: User = Depends(get_current_user)):
    return services.add_company_note(session, domain, payload, actor)


@router.get("/{domain}/activity", response_model=list[ActivityItem],
            summary="Company activity timeline (notes + assignment events + score changes)")
def activity(domain: str, session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return services.company_activity(session, domain)
