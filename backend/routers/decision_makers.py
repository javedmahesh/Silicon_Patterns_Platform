from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend import company_intelligence as cintel
from backend import dm_intelligence_jobs as dm_jobs
from backend import relationship_intelligence as reli
from backend import services
from backend.dependencies import Pagination, get_session, pagination
from backend.schemas import (
    CompanyContactsOut,
    CompanyIntelligenceOut,
    CompanyRelationshipsOut,
    ContactIn,
    ContactOut,
    DecisionMakerCompanies,
    DecisionMakerDetailOut,
    DecisionMakerNoteIn,
    DecisionMakerNoteOut,
    DecisionMakerNoteUpdate,
    DecisionMakerOut,
    DecisionMakerUpdate,
    DmIntelligenceJobOut,
    DmIntelligenceRunIn,
    Page,
)
from backend.security import get_current_user, require_admin, require_manager
from master_db.models import User

router = APIRouter(prefix="/decision-makers", tags=["decision-makers"])


@router.get("/companies", response_model=DecisionMakerCompanies,
            summary="Decision-maker counts grouped by company")
def decision_maker_companies(session: Session = Depends(get_session)):
    return services.decision_maker_companies(session)


@router.get("", response_model=Page[DecisionMakerOut], summary="List/filter decision makers")
def list_decision_makers(
    session: Session = Depends(get_session),
    page: Pagination = Depends(pagination),
    company_domain: str | None = Query(None, description="Filter by company"),
    seniority: str | None = Query(None, description="Filter by seniority (e.g. 'senior')"),
    senior: bool = Query(False, description="Only senior leadership (CxO / founder / VP / director)"),
):
    return services.list_decision_makers(
        session, pagination=page, company_domain=company_domain, seniority=seniority, senior=senior
    )


# --------------------- manual Decision Maker Intelligence (paid Apify) --------
# Declared BEFORE the dynamic /{dm_id} route so these static paths win. Running the
# engine is a management action (it costs money): manager+ only (RBAC), matching the
# frontend gate. Reads are open to any authenticated user so progress can be watched.
@router.post("/intelligence-runs", response_model=DmIntelligenceJobOut,
             status_code=status.HTTP_201_CREATED,
             summary="Run Decision Maker Intelligence for one-or-many companies "
                     "(each with its own count) — manager+ only")
def run_decision_maker_intelligence(
    body: DmIntelligenceRunIn,
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(require_manager),
):
    try:
        job = dm_jobs.create_job(
            session, items=body.items, requested_by_id=actor.id, requested_by_email=actor.email,
        )
    except dm_jobs.JobValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    # Execute on a background thread; the request returns the queued job immediately.
    dm_jobs.start_job_async(request.app, job.id)
    return DmIntelligenceJobOut.model_validate(job)


@router.get("/intelligence-runs", response_model=list[DmIntelligenceJobOut],
            summary="Recent Decision Maker Intelligence jobs (manual-run history)")
def list_intelligence_runs(session: Session = Depends(get_session),
                           _: User = Depends(get_current_user)):
    return [DmIntelligenceJobOut.model_validate(j) for j in dm_jobs.list_jobs(session, limit=20)]


@router.get("/intelligence-runs/{job_id}", response_model=DmIntelligenceJobOut,
            summary="One Decision Maker Intelligence job with live per-company progress")
def get_intelligence_run(job_id: int, session: Session = Depends(get_session),
                         _: User = Depends(get_current_user)):
    job = dm_jobs.get_job(session, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    return DmIntelligenceJobOut.model_validate(job)


@router.get("/company/{domain}", response_model=CompanyContactsOut,
            summary="Ranked contacts + contact map + org hierarchy for a company (decision intelligence)")
def company_contacts(domain: str, session: Session = Depends(get_session),
                     _: User = Depends(get_current_user)):
    return services.company_contacts(session, domain)


@router.get("/company/{domain}/intelligence", response_model=CompanyIntelligenceOut,
            summary="Company intelligence bundle: committee/dept coverage, completeness, "
                    "engagement, risk, heatmap, opportunity alignment, timeline")
def company_intelligence(domain: str, session: Session = Depends(get_session),
                         _: User = Depends(get_current_user)):
    return cintel.company_intelligence(session, domain)


@router.get("/company/{domain}/relationships", response_model=CompanyRelationshipsOut,
            summary="Relationship intelligence: next best contacts/actions, follow-ups, "
                    "opportunity intelligence, alerts and the relationship graph")
def company_relationships(domain: str, session: Session = Depends(get_session),
                          _: User = Depends(get_current_user)):
    return reli.company_relationships(session, domain)


@router.get("/{dm_id}", response_model=DecisionMakerDetailOut,
            summary="Full enrichment profile for one decision maker (lazy-loaded by the panel)")
def get_decision_maker(dm_id: int, session: Session = Depends(get_session),
                       _: User = Depends(get_current_user)):
    return services.get_decision_maker_detail(session, dm_id)


@router.patch("/{dm_id}", response_model=DecisionMakerOut,
              summary="Edit a decision maker's fields (admin only)")
def update_decision_maker(dm_id: int, body: DecisionMakerUpdate,
                          session: Session = Depends(get_session), _: User = Depends(require_admin)):
    return services.update_decision_maker(session, dm_id, body.model_dump(exclude_unset=True))


@router.delete("/{dm_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Permanently delete a decision maker (admin only)")
def delete_decision_maker(dm_id: int, session: Session = Depends(get_session),
                          _: User = Depends(require_admin)):
    services.delete_decision_maker(session, dm_id)


@router.get("/{dm_id}/contact", response_model=ContactOut | None,
            summary="Professional contact details for a decision maker (any authenticated user)")
def get_contact(dm_id: int, session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return services.get_dm_contact(session, dm_id)


@router.put("/{dm_id}/contact", response_model=ContactOut,
            summary="Set professional contact details (work email / phone only) — admin/manager only")
def put_contact(dm_id: int, payload: ContactIn, session: Session = Depends(get_session),
                actor: User = Depends(require_manager)):
    # Editing is a management action: admin/manager only. Members have read-only
    # access via GET (intelligence data stays visible to everyone).
    return services.put_dm_contact(session, dm_id, payload, actor)


# ----------------------------------------------------------- collaboration notes
@router.get("/{dm_id}/notes", response_model=list[DecisionMakerNoteOut],
            summary="Notes for a decision maker: all team notes + the caller's own personal notes")
def list_notes(dm_id: int, session: Session = Depends(get_session),
               user: User = Depends(get_current_user)):
    return services.list_dm_notes(session, dm_id, user)


@router.post("/{dm_id}/notes", response_model=DecisionMakerNoteOut, status_code=status.HTTP_201_CREATED,
             summary="Add a note. 'team' notes require admin/manager; 'personal' notes are private to the author")
def create_note(dm_id: int, payload: DecisionMakerNoteIn, session: Session = Depends(get_session),
                actor: User = Depends(get_current_user)):
    return services.create_dm_note(session, dm_id, payload, actor)


@router.patch("/{dm_id}/notes/{note_id}", response_model=DecisionMakerNoteOut,
              summary="Edit a note — team: admin/manager; personal: the author only")
def update_note(dm_id: int, note_id: int, payload: DecisionMakerNoteUpdate,
                session: Session = Depends(get_session), actor: User = Depends(get_current_user)):
    return services.update_dm_note(session, dm_id, note_id, payload, actor)


@router.delete("/{dm_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a note — team: admin/manager; personal: the author only")
def delete_note(dm_id: int, note_id: int, session: Session = Depends(get_session),
                actor: User = Depends(get_current_user)):
    services.delete_dm_note(session, dm_id, note_id, actor)
