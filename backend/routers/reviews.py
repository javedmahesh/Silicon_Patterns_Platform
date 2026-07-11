"""Human lead review + feedback endpoints (P-task viii).

A human analyst's assessment of a lead, kept SEPARATE from the model score (it
never overwrites lead_scores). Open to any authenticated user — this is analyst
feedback, like company notes — with full attribution + an append-only audit
trail. ``/reviews/reports`` powers the model-vs-human reporting (§7).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import services
from backend.dependencies import get_session
from backend.schemas import LeadReviewEventOut, LeadReviewIn, LeadReviewOut, ReviewReports
from backend.security import get_current_user
from master_db.models import User

# Reviews are visible to ANY authenticated user (shared intelligence); writing one
# records the author. Registered with its own auth gate (not the blanket principal).
router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/reports", response_model=ReviewReports,
            summary="Model-vs-human review reports (disagreements, overrides, strategic, false neg/pos)")
def reports(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return services.review_reports(session)


@router.get("/{domain}", response_model=LeadReviewOut | None,
            summary="The current human assessment of a lead (null if unreviewed)")
def get_review(domain: str, session: Session = Depends(get_session),
               _: User = Depends(get_current_user)):
    return services.get_lead_review(session, domain)


@router.put("/{domain}", response_model=LeadReviewOut,
            summary="Set/update the human assessment (does NOT change the model score)")
def put_review(domain: str, payload: LeadReviewIn, session: Session = Depends(get_session),
               actor: User = Depends(get_current_user)):
    return services.set_lead_review(session, domain, payload, actor)


@router.get("/{domain}/history", response_model=list[LeadReviewEventOut],
            summary="The review audit trail for a company (who, when, status change, notes)")
def history(domain: str, session: Session = Depends(get_session),
            _: User = Depends(get_current_user)):
    return services.lead_review_history(session, domain)
