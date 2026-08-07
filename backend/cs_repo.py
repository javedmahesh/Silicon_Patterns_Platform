"""Data access for Enterprise CRM Phase 4: Customer Success & Account Management."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from master_db.models import (
    CsAccount,
    CsContract,
    CsHealthScore,
    CsLifecycleEvent,
    CsRisk,
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


def latest_health(session: Session, account_id: int) -> CsHealthScore | None:
    return session.scalar(
        select(CsHealthScore)
        .where(CsHealthScore.account_id == account_id)
        .order_by(CsHealthScore.created_at.desc())
        .limit(1)
    )


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
def list_risks(
    session: Session, account_id: int, status: str | None = None
) -> list[CsRisk]:
    q = select(CsRisk).where(CsRisk.account_id == account_id)
    if status:
        q = q.where(CsRisk.status == status)
    return list(session.scalars(q.order_by(CsRisk.created_at.desc())))


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


