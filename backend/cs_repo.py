"""Data access for Enterprise CRM Phase 4: Customer Success & Account Management."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from master_db.models import (
    CrmComment,
    CsAccount,
    CsContact,
    CsContract,
    CsHealthScore,
    CsLifecycleEvent,
    CsMilestone,
    CsRisk,
    CsSuccessPlan,
    OutreachMeeting,
    OutreachTask,
)

from backend.timeutil import utcnow as _utcnow


# ----------------------------------------------------------------- accounts
def get_account(session: Session, account_id: int) -> CsAccount | None:
    return session.get(CsAccount, account_id)


def list_accounts(
    session: Session,
    status: str | None = None,
    tier: str | None = None,
    owner_id: int | None = None,
    lifecycle_stage: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[CsAccount], int]:
    q = select(CsAccount)
    if status:
        q = q.where(CsAccount.status == status)
    if tier:
        q = q.where(CsAccount.tier == tier)
    if owner_id:
        q = q.where(CsAccount.owner_id == owner_id)
    if lifecycle_stage:
        q = q.where(CsAccount.lifecycle_stage == lifecycle_stage)
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(
        q.order_by(CsAccount.updated_at.desc()).limit(limit).offset(offset)
    ))
    return rows, total


def create_account(session: Session, **kw) -> CsAccount:
    a = CsAccount(**kw)
    session.add(a)
    session.flush()
    return a


# ----------------------------------------------------------------- contacts
def get_contact(session: Session, contact_id: int) -> CsContact | None:
    return session.get(CsContact, contact_id)


def list_contacts(session: Session, account_id: int) -> list[CsContact]:
    return list(session.scalars(
        select(CsContact).where(CsContact.account_id == account_id)
        .order_by(CsContact.is_primary.desc(), CsContact.created_at)
    ))


def create_contact(session: Session, **kw) -> CsContact:
    c = CsContact(**kw)
    session.add(c)
    session.flush()
    return c


# ----------------------------------------------------------------- health
def latest_health(session: Session, account_id: int) -> CsHealthScore | None:
    return session.scalar(
        select(CsHealthScore)
        .where(CsHealthScore.account_id == account_id)
        .order_by(CsHealthScore.created_at.desc())
        .limit(1)
    )


def latest_health_batch(session: Session, account_ids: list[int]) -> dict[int, CsHealthScore]:
    """Latest CsHealthScore per account, 1 query — avoids N+1 across list_accounts()."""
    if not account_ids:
        return {}
    rows = session.scalars(
        select(CsHealthScore)
        .where(CsHealthScore.account_id.in_(account_ids))
        .order_by(CsHealthScore.account_id, CsHealthScore.created_at.desc())
    )
    latest: dict[int, CsHealthScore] = {}
    for r in rows:
        latest.setdefault(r.account_id, r)
    return latest


def health_history(
    session: Session, account_id: int, limit: int = 30
) -> list[CsHealthScore]:
    return list(session.scalars(
        select(CsHealthScore)
        .where(CsHealthScore.account_id == account_id)
        .order_by(CsHealthScore.created_at.desc())
        .limit(limit)
    ))


def create_health_score(session: Session, **kw) -> CsHealthScore:
    h = CsHealthScore(**kw)
    session.add(h)
    session.flush()
    return h


def health_distribution(session: Session) -> dict[str, int]:
    """Count accounts per health grade (latest snapshot per account). 1 subquery."""
    # Latest health id per account via GROUP BY
    sub = (
        select(
            CsHealthScore.account_id,
            func.max(CsHealthScore.id).label("max_id"),
        )
        .group_by(CsHealthScore.account_id)
        .subquery()
    )
    rows = session.execute(
        select(CsHealthScore.grade, func.count(CsHealthScore.id))
        .join(sub, and_(
            CsHealthScore.account_id == sub.c.account_id,
            CsHealthScore.id == sub.c.max_id,
        ))
        .group_by(CsHealthScore.grade)
    ).all()
    return {r[0]: r[1] for r in rows}


# ----------------------------------------------------------------- lifecycle
def add_lifecycle_event(session: Session, **kw) -> CsLifecycleEvent:
    e = CsLifecycleEvent(**kw)
    session.add(e)
    session.flush()
    return e


def lifecycle_history(session: Session, account_id: int) -> list[CsLifecycleEvent]:
    return list(session.scalars(
        select(CsLifecycleEvent)
        .where(CsLifecycleEvent.account_id == account_id)
        .order_by(CsLifecycleEvent.created_at.desc())
        .limit(50)
    ))


# ----------------------------------------------------------------- contracts
def get_contract(session: Session, contract_id: int) -> CsContract | None:
    return session.get(CsContract, contract_id)


def list_contracts(
    session: Session, account_id: int | None = None,
    status: str | None = None, limit: int = 50, offset: int = 0
) -> tuple[list[CsContract], int]:
    q = select(CsContract)
    if account_id:
        q = q.where(CsContract.account_id == account_id)
    if status:
        q = q.where(CsContract.status == status)
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(CsContract.end_date.asc().nullslast()).limit(limit).offset(offset)))
    return rows, total


def create_contract(session: Session, **kw) -> CsContract:
    c = CsContract(**kw)
    session.add(c)
    session.flush()
    return c


def renewals_due(session: Session, days: int = 90) -> list[CsContract]:
    """Contracts expiring within `days` days that are still active."""
    cutoff = _utcnow() + timedelta(days=days)
    return list(session.scalars(
        select(CsContract)
        .where(
            CsContract.status == "active",
            CsContract.end_date.isnot(None),
            CsContract.end_date <= cutoff,
        )
        .order_by(CsContract.end_date)
        .limit(100)
    ))


# ----------------------------------------------------------------- success plans
def get_plan(session: Session, plan_id: int) -> CsSuccessPlan | None:
    return session.get(CsSuccessPlan, plan_id)


def list_plans(session: Session, account_id: int) -> list[CsSuccessPlan]:
    return list(session.scalars(
        select(CsSuccessPlan).where(CsSuccessPlan.account_id == account_id)
        .order_by(CsSuccessPlan.created_at.desc())
    ))


def create_plan(session: Session, **kw) -> CsSuccessPlan:
    p = CsSuccessPlan(**kw)
    session.add(p)
    session.flush()
    return p


# ----------------------------------------------------------------- milestones
def get_milestone(session: Session, milestone_id: int) -> CsMilestone | None:
    return session.get(CsMilestone, milestone_id)


def list_milestones(session: Session, plan_id: int) -> list[CsMilestone]:
    return list(session.scalars(
        select(CsMilestone).where(CsMilestone.plan_id == plan_id)
        .order_by(CsMilestone.due_date.asc().nullslast())
    ))


def create_milestone(session: Session, **kw) -> CsMilestone:
    m = CsMilestone(**kw)
    session.add(m)
    session.flush()
    return m


# ----------------------------------------------------------------- risks
def get_risk(session: Session, risk_id: int) -> CsRisk | None:
    return session.get(CsRisk, risk_id)


def list_risks(
    session: Session, account_id: int, status: str | None = None
) -> list[CsRisk]:
    q = select(CsRisk).where(CsRisk.account_id == account_id)
    if status:
        q = q.where(CsRisk.status == status)
    return list(session.scalars(q.order_by(CsRisk.created_at.desc())))


def create_risk(session: Session, **kw) -> CsRisk:
    r = CsRisk(**kw)
    session.add(r)
    session.flush()
    return r


# ----------------------------------------------------------------- analytics
def arr_mrr_totals(session: Session) -> dict:
    row = session.execute(
        select(
            func.sum(CsAccount.arr).label("total_arr"),
            func.sum(CsAccount.mrr).label("total_mrr"),
            func.count(CsAccount.id).label("count"),
        ).where(CsAccount.status == "active")
    ).one()
    return {
        "total_arr": float(row.total_arr or 0),
        "total_mrr": float(row.total_mrr or 0),
        "active_count": int(row.count or 0),
    }


def churn_renewal_rates(session: Session) -> dict:
    """Count churned and total for simple rate computation."""
    rows = session.execute(
        select(CsAccount.status, func.count(CsAccount.id).label("cnt"))
        .group_by(CsAccount.status)
    ).all()
    counts = {r.status: r.cnt for r in rows}
    total = sum(counts.values()) or 1
    churned = counts.get("churned", 0)
    return {
        "churn_count": churned,
        "total_count": total,
        "churn_rate": round(churned / total, 4),
        "renewal_rate": round(1 - churned / total, 4),
        "by_status": counts,
    }


def expansion_pipeline(session: Session) -> list[CsAccount]:
    """Accounts in expansion lifecycle stage."""
    return list(session.scalars(
        select(CsAccount)
        .where(CsAccount.lifecycle_stage == "expansion")
        .order_by(CsAccount.arr.desc())
        .limit(50)
    ))


def avg_health_score(session: Session) -> float | None:
    """Average of the latest health score per account."""
    sub = (
        select(func.max(CsHealthScore.id).label("max_id"))
        .group_by(CsHealthScore.account_id)
        .subquery()
    )
    result = session.scalar(
        select(func.avg(CsHealthScore.score))
        .where(CsHealthScore.id.in_(select(sub.c.max_id)))
    )
    return float(result) if result is not None else None


# ----------------------------------------------------------------- timeline helpers
def account_tasks(session: Session, account_id: int, limit: int = 20) -> list[OutreachTask]:
    acct = session.get(CsAccount, account_id)
    if not acct or not acct.company_domain:
        return []
    return list(session.scalars(
        select(OutreachTask)
        .where(OutreachTask.company_domain == acct.company_domain)
        .order_by(OutreachTask.created_at.desc())
        .limit(limit)
    ))


def account_meetings(session: Session, account_id: int, limit: int = 20) -> list[OutreachMeeting]:
    acct = session.get(CsAccount, account_id)
    if not acct or not acct.company_domain:
        return []
    return list(session.scalars(
        select(OutreachMeeting)
        .where(OutreachMeeting.company_domain == acct.company_domain)
        .order_by(OutreachMeeting.scheduled_at.desc())
        .limit(limit)
    ))


def account_comments(session: Session, account_id: int, limit: int = 20) -> list[CrmComment]:
    return list(session.scalars(
        select(CrmComment)
        .where(
            CrmComment.entity_type == "cs_account",
            CrmComment.entity_id == str(account_id),
        )
        .order_by(CrmComment.created_at.desc())
        .limit(limit)
    ))
