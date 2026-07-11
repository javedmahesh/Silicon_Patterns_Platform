"""Enterprise CRM Phase 4: Customer Success & Account Management service layer."""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend import cs_repo as repo
from backend import workflow_service
from backend.schemas import (
    CsAccountCreate,
    CsAccountOut,
    CsAccountPatch,
    CsAnalyticsOut,
    CsContactCreate,
    CsContactOut,
    CsContactPatch,
    CsContractCreate,
    CsContractOut,
    CsContractPatch,
    CsDashboardOut,
    CsHealthScoreCreate,
    CsHealthScoreOut,
    CsLifecycleEventOut,
    CsMilestoneCreate,
    CsMilestoneOut,
    CsMilestonePatch,
    CsRiskCreate,
    CsRiskOut,
    CsRiskPatch,
    CsSuccessPlanCreate,
    CsSuccessPlanOut,
    CsSuccessPlanPatch,
    CsTimelineEvent,
    Page,
)
from master_db.models import CsAccount, CsContract, CsRisk, OutreachTask, User

from backend.timeutil import utc as _utc, utcnow as _utcnow


def _load_user_emails(session: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = session.scalars(select(User).where(User.id.in_(ids))).all()
    return {u.id: u.email for u in rows}


# ----------------------------------------------------------------- serializers
def _acct_out(a: CsAccount, owner_email: str = "",
              score: float | None = None, grade: str | None = None,
              trend: str | None = None) -> CsAccountOut:
    return CsAccountOut(
        id=a.id, name=a.name, company_domain=a.company_domain,
        owner_id=a.owner_id, owner_email=owner_email,
        status=a.status, tier=a.tier, industry=a.industry,
        arr=a.arr, mrr=a.mrr, contract_value=a.contract_value,
        currency=a.currency, renewal_date=_utc(a.renewal_date),
        lifecycle_stage=a.lifecycle_stage, notes=a.notes,
        tags=list(a.tags or []),
        health_score=score, health_grade=grade, health_trend=trend,
        created_at=_utc(a.created_at), updated_at=_utc(a.updated_at),
    )


def _contact_out(c, owner_email: str = "") -> CsContactOut:
    return CsContactOut(
        id=c.id, account_id=c.account_id,
        first_name=c.first_name, last_name=c.last_name,
        email=c.email, phone=c.phone, title=c.title,
        role=c.role, is_primary=c.is_primary,
        owner_id=c.owner_id, owner_email=owner_email,
        notes=c.notes,
        created_at=_utc(c.created_at), updated_at=_utc(c.updated_at),
    )


def _health_out(h) -> CsHealthScoreOut:
    return CsHealthScoreOut(
        id=h.id, account_id=h.account_id,
        score=h.score, grade=h.grade, trend=h.trend,
        product_adoption=h.product_adoption,
        meeting_activity=h.meeting_activity,
        email_activity=h.email_activity,
        opportunity_activity=h.opportunity_activity,
        open_issues=h.open_issues,
        renewal_status=h.renewal_status,
        executive_engagement=h.executive_engagement,
        detail=dict(h.detail or {}),
        created_at=_utc(h.created_at),
    )


def _contract_out(c, owner_email: str = "") -> CsContractOut:
    return CsContractOut(
        id=c.id, account_id=c.account_id, name=c.name,
        status=c.status, value=c.value, currency=c.currency,
        start_date=_utc(c.start_date), end_date=_utc(c.end_date),
        auto_renew=c.auto_renew, renewal_probability=c.renewal_probability,
        owner_id=c.owner_id, owner_email=owner_email, notes=c.notes,
        created_at=_utc(c.created_at), updated_at=_utc(c.updated_at),
    )


def _plan_out(p, owner_email: str = "") -> CsSuccessPlanOut:
    return CsSuccessPlanOut(
        id=p.id, account_id=p.account_id, name=p.name,
        status=p.status, owner_id=p.owner_id, owner_email=owner_email,
        goals=list(p.goals or []), notes=p.notes,
        due_date=_utc(p.due_date),
        created_at=_utc(p.created_at), updated_at=_utc(p.updated_at),
    )


def _ms_out(m, owner_email: str = "") -> CsMilestoneOut:
    return CsMilestoneOut(
        id=m.id, plan_id=m.plan_id, account_id=m.account_id, name=m.name,
        status=m.status, due_date=_utc(m.due_date),
        completed_at=_utc(m.completed_at),
        owner_id=m.owner_id, owner_email=owner_email, notes=m.notes,
        created_at=_utc(m.created_at), updated_at=_utc(m.updated_at),
    )


def _risk_out(r, owner_email: str = "") -> CsRiskOut:
    return CsRiskOut(
        id=r.id, account_id=r.account_id, title=r.title,
        description=r.description, severity=r.severity, status=r.status,
        owner_id=r.owner_id, owner_email=owner_email,
        due_date=_utc(r.due_date), resolved_at=_utc(r.resolved_at),
        created_at=_utc(r.created_at), updated_at=_utc(r.updated_at),
    )


# ================================================================== health scoring
_WEIGHTS = {
    "product_adoption": 0.25,
    "meeting_activity": 0.15,
    "email_activity": 0.10,
    "opportunity_activity": 0.10,
    "open_issues": 0.15,
    "renewal_status": 0.15,
    "executive_engagement": 0.10,
}


def _compute_score(signals: dict) -> tuple[float, str, str]:
    """Deterministic weighted average → grade → trend (stub: no prior)."""
    score = sum(signals.get(k, 0.0) * w for k, w in _WEIGHTS.items())
    score = round(max(0.0, min(100.0, score)), 1)
    if score >= 85:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 55:
        grade = "C"
    elif score >= 35:
        grade = "D"
    else:
        grade = "F"
    return score, grade, "stable"   # trend requires prior snapshot; always stable on creation


# ================================================================== accounts
def list_accounts(
    session: Session, user,
    status: str | None, tier: str | None,
    lifecycle_stage: str | None, limit: int, offset: int,
) -> Page:
    accounts, total = repo.list_accounts(
        session, status=status, tier=tier,
        lifecycle_stage=lifecycle_stage, limit=limit, offset=offset,
    )
    owner_ids = [a.owner_id for a in accounts if a.owner_id]
    email_map = _load_user_emails(session, owner_ids)
    health_map = repo.latest_health_batch(session, [a.id for a in accounts])
    items = []
    for a in accounts:
        h = health_map.get(a.id)
        items.append(_acct_out(
            a, email_map.get(a.owner_id, ""),
            score=h.score if h else None,
            grade=h.grade if h else None,
            trend=h.trend if h else None,
        ))
    return Page.build(items, total, max(1, offset // limit + 1) if limit else 1, limit)


def get_account(session: Session, account_id: int, user) -> CsAccountOut:
    a = repo.get_account(session, account_id)
    if not a:
        raise HTTPException(404, "account not found")
    email_map = _load_user_emails(session, [a.owner_id] if a.owner_id else [])
    h = repo.latest_health(session, a.id)
    return _acct_out(
        a, email_map.get(a.owner_id, ""),
        score=h.score if h else None,
        grade=h.grade if h else None,
        trend=h.trend if h else None,
    )


def create_account(session: Session, data: CsAccountCreate, user) -> CsAccountOut:
    a = repo.create_account(
        session, name=data.name, company_domain=data.company_domain,
        owner_id=data.owner_id or user.id,
        status=data.status, tier=data.tier, industry=data.industry,
        arr=data.arr, mrr=data.mrr, contract_value=data.contract_value,
        currency=data.currency, renewal_date=data.renewal_date,
        lifecycle_stage=data.lifecycle_stage, notes=data.notes,
        tags=data.tags or [],
    )
    repo.add_lifecycle_event(
        session, account_id=a.id, stage=data.lifecycle_stage,
        from_stage="", changed_by=user.id,
    )
    workflow_service.fire_event(
        session, "customer_created", "customer", a.id,
        {"owner_id": a.owner_id, "company_domain": a.company_domain, "tier": a.tier,
         "status": a.status, "arr": a.arr, "name": a.name},
        actor=user,
    )
    session.commit()
    email_map = _load_user_emails(session, [a.owner_id] if a.owner_id else [])
    return _acct_out(a, email_map.get(a.owner_id, ""))


def patch_account(session: Session, account_id: int, data: CsAccountPatch, user) -> CsAccountOut:
    a = repo.get_account(session, account_id)
    if not a:
        raise HTTPException(404, "account not found")
    old_stage = a.lifecycle_stage
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(a, field, val)
    if data.lifecycle_stage and data.lifecycle_stage != old_stage:
        repo.add_lifecycle_event(
            session, account_id=a.id, stage=data.lifecycle_stage,
            from_stage=old_stage, changed_by=user.id,
        )
    session.commit()
    email_map = _load_user_emails(session, [a.owner_id] if a.owner_id else [])
    h = repo.latest_health(session, a.id)
    return _acct_out(
        a, email_map.get(a.owner_id, ""),
        score=h.score if h else None, grade=h.grade if h else None, trend=h.trend if h else None,
    )


def delete_account(session: Session, account_id: int, user) -> None:
    a = repo.get_account(session, account_id)
    if not a:
        raise HTTPException(404, "account not found")
    session.delete(a)
    session.commit()


# ================================================================== contacts
def list_contacts(session: Session, account_id: int, user) -> list[CsContactOut]:
    contacts = repo.list_contacts(session, account_id)
    owner_ids = [c.owner_id for c in contacts if c.owner_id]
    email_map = _load_user_emails(session, owner_ids)
    return [_contact_out(c, email_map.get(c.owner_id, "")) for c in contacts]


def create_contact(session: Session, data: CsContactCreate, user) -> CsContactOut:
    c = repo.create_contact(session, **data.model_dump())
    session.commit()
    email_map = _load_user_emails(session, [c.owner_id] if c.owner_id else [])
    return _contact_out(c, email_map.get(c.owner_id, ""))


def patch_contact(session: Session, contact_id: int, data: CsContactPatch, user) -> CsContactOut:
    c = repo.get_contact(session, contact_id)
    if not c:
        raise HTTPException(404, "contact not found")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(c, field, val)
    session.commit()
    email_map = _load_user_emails(session, [c.owner_id] if c.owner_id else [])
    return _contact_out(c, email_map.get(c.owner_id, ""))


def delete_contact(session: Session, contact_id: int, user) -> None:
    c = repo.get_contact(session, contact_id)
    if not c:
        raise HTTPException(404, "contact not found")
    session.delete(c)
    session.commit()


# ================================================================== health
def score_account(session: Session, account_id: int, data: CsHealthScoreCreate, user) -> CsHealthScoreOut:
    a = repo.get_account(session, account_id)
    if not a:
        raise HTTPException(404, "account not found")
    signals = {
        "product_adoption": data.product_adoption,
        "meeting_activity": data.meeting_activity,
        "email_activity": data.email_activity,
        "opportunity_activity": data.opportunity_activity,
        "open_issues": data.open_issues,
        "renewal_status": data.renewal_status,
        "executive_engagement": data.executive_engagement,
    }
    score, grade, _ = _compute_score(signals)
    # Compute trend vs prior
    prior = repo.latest_health(session, account_id)
    if prior is None:
        trend = "stable"
    elif score > prior.score + 5:
        trend = "up"
    elif score < prior.score - 5:
        trend = "down"
    else:
        trend = "stable"
    h = repo.create_health_score(
        session, account_id=account_id,
        score=score, grade=grade, trend=trend,
        detail=data.detail or {},
        **signals,
    )
    if prior is None or prior.grade != grade:
        workflow_service.fire_event(
            session, "health_changed", "customer", account_id,
            {"owner_id": a.owner_id, "company_domain": a.company_domain, "tier": a.tier,
             "grade": grade, "score": score, "prior_grade": prior.grade if prior else "", "trend": trend},
            actor=user,
        )
    session.commit()
    return _health_out(h)


def get_health(session: Session, account_id: int, user) -> CsHealthScoreOut:
    h = repo.latest_health(session, account_id)
    if not h:
        raise HTTPException(404, "no health score recorded")
    return _health_out(h)


def health_history(session: Session, account_id: int, user) -> list[CsHealthScoreOut]:
    return [_health_out(h) for h in repo.health_history(session, account_id)]


# ================================================================== lifecycle
def lifecycle_history(session: Session, account_id: int, user) -> list[CsLifecycleEventOut]:
    events = repo.lifecycle_history(session, account_id)
    return [
        CsLifecycleEventOut(
            id=e.id, account_id=e.account_id, stage=e.stage,
            from_stage=e.from_stage, changed_by=e.changed_by,
            note=e.note, created_at=_utc(e.created_at),
        )
        for e in events
    ]


# ================================================================== contracts
def list_contracts(
    session: Session, account_id: int | None, status: str | None,
    limit: int, offset: int, user,
) -> Page:
    contracts, total = repo.list_contracts(
        session, account_id=account_id, status=status, limit=limit, offset=offset
    )
    owner_ids = [c.owner_id for c in contracts if c.owner_id]
    email_map = _load_user_emails(session, owner_ids)
    items = [_contract_out(c, email_map.get(c.owner_id, "")) for c in contracts]
    return Page.build(items, total, max(1, offset // limit + 1) if limit else 1, limit)


def create_contract(session: Session, data: CsContractCreate, user) -> CsContractOut:
    c = repo.create_contract(session, **data.model_dump())
    session.commit()
    email_map = _load_user_emails(session, [c.owner_id] if c.owner_id else [])
    return _contract_out(c, email_map.get(c.owner_id, ""))


def patch_contract(session: Session, contract_id: int, data: CsContractPatch, user) -> CsContractOut:
    c = repo.get_contract(session, contract_id)
    if not c:
        raise HTTPException(404, "contract not found")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(c, field, val)
    session.commit()
    email_map = _load_user_emails(session, [c.owner_id] if c.owner_id else [])
    return _contract_out(c, email_map.get(c.owner_id, ""))


def delete_contract(session: Session, contract_id: int, user) -> None:
    c = repo.get_contract(session, contract_id)
    if not c:
        raise HTTPException(404, "contract not found")
    session.delete(c)
    session.commit()


# ================================================================== success plans
def list_plans(session: Session, account_id: int, user) -> list[CsSuccessPlanOut]:
    plans = repo.list_plans(session, account_id)
    owner_ids = [p.owner_id for p in plans if p.owner_id]
    email_map = _load_user_emails(session, owner_ids)
    return [_plan_out(p, email_map.get(p.owner_id, "")) for p in plans]


def create_plan(session: Session, data: CsSuccessPlanCreate, user) -> CsSuccessPlanOut:
    p = repo.create_plan(session, **data.model_dump())
    session.commit()
    email_map = _load_user_emails(session, [p.owner_id] if p.owner_id else [])
    return _plan_out(p, email_map.get(p.owner_id, ""))


def patch_plan(session: Session, plan_id: int, data: CsSuccessPlanPatch, user) -> CsSuccessPlanOut:
    p = repo.get_plan(session, plan_id)
    if not p:
        raise HTTPException(404, "success plan not found")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(p, field, val)
    session.commit()
    email_map = _load_user_emails(session, [p.owner_id] if p.owner_id else [])
    return _plan_out(p, email_map.get(p.owner_id, ""))


def delete_plan(session: Session, plan_id: int, user) -> None:
    p = repo.get_plan(session, plan_id)
    if not p:
        raise HTTPException(404, "success plan not found")
    session.delete(p)
    session.commit()


# ================================================================== milestones
def list_milestones(session: Session, plan_id: int, user) -> list[CsMilestoneOut]:
    milestones = repo.list_milestones(session, plan_id)
    owner_ids = [m.owner_id for m in milestones if m.owner_id]
    email_map = _load_user_emails(session, owner_ids)
    return [_ms_out(m, email_map.get(m.owner_id, "")) for m in milestones]


def create_milestone(session: Session, data: CsMilestoneCreate, user) -> CsMilestoneOut:
    m = repo.create_milestone(session, **data.model_dump())
    session.commit()
    email_map = _load_user_emails(session, [m.owner_id] if m.owner_id else [])
    return _ms_out(m, email_map.get(m.owner_id, ""))


def patch_milestone(session: Session, milestone_id: int, data: CsMilestonePatch, user) -> CsMilestoneOut:
    m = repo.get_milestone(session, milestone_id)
    if not m:
        raise HTTPException(404, "milestone not found")
    if data.status == "completed" and m.completed_at is None:
        m.completed_at = _utcnow()
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(m, field, val)
    session.commit()
    email_map = _load_user_emails(session, [m.owner_id] if m.owner_id else [])
    return _ms_out(m, email_map.get(m.owner_id, ""))


def delete_milestone(session: Session, milestone_id: int, user) -> None:
    m = repo.get_milestone(session, milestone_id)
    if not m:
        raise HTTPException(404, "milestone not found")
    session.delete(m)
    session.commit()


# ================================================================== risks
def list_risks(session: Session, account_id: int, status: str | None, user) -> list[CsRiskOut]:
    risks = repo.list_risks(session, account_id, status=status)
    owner_ids = [r.owner_id for r in risks if r.owner_id]
    email_map = _load_user_emails(session, owner_ids)
    return [_risk_out(r, email_map.get(r.owner_id, "")) for r in risks]


def create_risk(session: Session, data: CsRiskCreate, user) -> CsRiskOut:
    r = repo.create_risk(session, **data.model_dump())
    session.commit()
    email_map = _load_user_emails(session, [r.owner_id] if r.owner_id else [])
    return _risk_out(r, email_map.get(r.owner_id, ""))


def patch_risk(session: Session, risk_id: int, data: CsRiskPatch, user) -> CsRiskOut:
    r = repo.get_risk(session, risk_id)
    if not r:
        raise HTTPException(404, "risk not found")
    if data.status in ("mitigated", "closed", "accepted") and r.resolved_at is None:
        r.resolved_at = _utcnow()
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(r, field, val)
    session.commit()
    email_map = _load_user_emails(session, [r.owner_id] if r.owner_id else [])
    return _risk_out(r, email_map.get(r.owner_id, ""))


def delete_risk(session: Session, risk_id: int, user) -> None:
    r = repo.get_risk(session, risk_id)
    if not r:
        raise HTTPException(404, "risk not found")
    session.delete(r)
    session.commit()


# ================================================================== timeline
def account_timeline(
    session: Session, account_id: int, user,
    limit: int = 50, offset: int = 0,
) -> list[CsTimelineEvent]:
    events: list[CsTimelineEvent] = []

    for t in repo.account_tasks(session, account_id, limit=limit // 3):
        events.append(CsTimelineEvent(
            event_id=f"task-{t.id}", event_type="task",
            label=f"Task: {t.title}",
            detail=t.description or "",
            timestamp=_utc(t.created_at) or _utcnow(),
        ))

    for m in repo.account_meetings(session, account_id, limit=limit // 3):
        events.append(CsTimelineEvent(
            event_id=f"meeting-{m.id}", event_type="meeting",
            label=f"Meeting: {m.title}",
            detail=m.notes or "",
            timestamp=_utc(m.scheduled_at) or _utcnow(),
        ))

    for c in repo.account_comments(session, account_id, limit=limit // 3):
        events.append(CsTimelineEvent(
            event_id=f"comment-{c.id}", event_type="comment",
            label="Internal note",
            detail=c.body[:200],
            timestamp=_utc(c.created_at) or _utcnow(),
        ))

    for lc in repo.lifecycle_history(session, account_id):
        events.append(CsTimelineEvent(
            event_id=f"lifecycle-{lc.id}", event_type="lifecycle",
            label=f"Stage → {lc.stage}",
            detail=lc.note,
            timestamp=_utc(lc.created_at) or _utcnow(),
        ))

    events.sort(key=lambda e: e.timestamp, reverse=True)
    return events[offset: offset + limit]


# ================================================================== dashboard
def cs_dashboard(session: Session, user) -> CsDashboardOut:
    totals = repo.arr_mrr_totals(session)
    churn = repo.churn_renewal_rates(session)
    avg_h = repo.avg_health_score(session)
    renewals = repo.renewals_due(session, days=90)
    expansion = repo.expansion_pipeline(session)

    from sqlalchemy import select as sa_select
    from master_db.models import CsAccount as A, CsRisk as R, OutreachTask as T, OutreachMeeting as M
    now = _utcnow()

    at_risk = session.scalar(sa_select(func.count(A.id)).where(A.status == "at_risk")) or 0
    churned = session.scalar(sa_select(func.count(A.id)).where(A.status == "churned")) or 0
    total_all = session.scalar(sa_select(func.count(A.id))) or 0
    open_risks = session.scalar(sa_select(func.count(R.id)).where(R.status == "open")) or 0
    open_tasks = session.scalar(
        sa_select(func.count(T.id)).where(T.status.in_(["pending", "in_progress"]))
    ) or 0
    upcoming_mtg = session.scalar(
        sa_select(func.count(M.id)).where(M.scheduled_at >= now)
    ) or 0

    return CsDashboardOut(
        total_accounts=total_all,
        active_accounts=totals["active_count"],
        at_risk_accounts=at_risk,
        churned_accounts=churned,
        total_arr=totals["total_arr"],
        total_mrr=totals["total_mrr"],
        avg_health_score=avg_h,
        renewals_due_90d=len(renewals),
        open_risks=open_risks,
        expansion_accounts=len(expansion),
        open_tasks=open_tasks,
        upcoming_meetings=upcoming_mtg,
    )


# ================================================================== analytics
def cs_analytics(session: Session, user) -> CsAnalyticsOut:
    totals = repo.arr_mrr_totals(session)
    churn = repo.churn_renewal_rates(session)
    avg_h = repo.avg_health_score(session)
    health_dist = repo.health_distribution(session)
    expansion = repo.expansion_pipeline(session)

    return CsAnalyticsOut(
        total_arr=totals["total_arr"],
        total_mrr=totals["total_mrr"],
        active_count=totals["active_count"],
        churn_rate=churn["churn_rate"],
        renewal_rate=churn["renewal_rate"],
        churn_count=churn["churn_count"],
        avg_health_score=avg_h,
        health_distribution=health_dist,
        expansion_account_count=len(expansion),
        by_status=churn["by_status"],
    )
