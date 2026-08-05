"""Data access for Enterprise CRM Phase 6: Workflow Automation & Business Process Engine."""
from __future__ import annotations


from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from master_db.models import (
    ApprovalRequest,
    SlaPolicy,
    SlaTracker,
    Workflow,
    WorkflowExecution,
)


# ----------------------------------------------------------------- workflows
def create_workflow(session: Session, **kw) -> Workflow:
    w = Workflow(**kw)
    session.add(w)
    session.flush()
    return w


def get_workflow(session: Session, workflow_id: int) -> Workflow | None:
    return session.get(Workflow, workflow_id)


def list_workflows(
    session: Session, *, status: str | None = None, trigger_event: str | None = None,
    limit: int = 50, offset: int = 0,
) -> tuple[list[Workflow], int]:
    q = select(Workflow)
    filters = []
    if status:
        filters.append(Workflow.status == status)
    if trigger_event:
        filters.append(Workflow.trigger_event == trigger_event)
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(Workflow.id.desc()).limit(limit).offset(offset)))
    return rows, total


def active_workflows_for_trigger(session: Session, trigger_event: str) -> list[Workflow]:
    """Enabled + active workflows matching this trigger. 1 query."""
    return list(session.scalars(
        select(Workflow).where(
            Workflow.trigger_event == trigger_event,
            Workflow.status == "active",
            Workflow.is_enabled.is_(True),
        )
    ))


def delete_workflow(session: Session, workflow_id: int) -> bool:
    w = session.get(Workflow, workflow_id)
    if not w:
        return False
    session.delete(w)
    return True


def get_workflow_names(session: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = session.execute(select(Workflow.id, Workflow.name).where(Workflow.id.in_(ids))).all()
    return {r[0]: r[1] for r in rows}


def count_active_workflows(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(Workflow).where(Workflow.status == "active", Workflow.is_enabled.is_(True))
    ) or 0


# ----------------------------------------------------------------- executions
def create_execution(session: Session, **kw) -> WorkflowExecution:
    e = WorkflowExecution(**kw)
    session.add(e)
    session.flush()
    return e


def list_executions(
    session: Session, *, workflow_id: int | None = None, entity_type: str | None = None,
    entity_id: str | None = None, limit: int = 50, offset: int = 0,
) -> tuple[list[WorkflowExecution], int]:
    q = select(WorkflowExecution)
    filters = []
    if workflow_id is not None:
        filters.append(WorkflowExecution.workflow_id == workflow_id)
    if entity_type:
        filters.append(WorkflowExecution.entity_type == entity_type)
    if entity_id:
        filters.append(WorkflowExecution.entity_id == entity_id)
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(WorkflowExecution.id.desc()).limit(limit).offset(offset)))
    return rows, total


def execution_stats(session: Session) -> dict:
    """Total/success/failure counts + avg duration. 1 query."""
    row = session.execute(
        select(
            func.count(WorkflowExecution.id),
            func.count(WorkflowExecution.id).filter(WorkflowExecution.status == "success"),
            func.count(WorkflowExecution.id).filter(WorkflowExecution.status == "failed"),
            func.coalesce(func.avg(WorkflowExecution.duration_ms), 0),
        )
    ).one()
    total, success, failed, avg_ms = row
    return {"total": total, "success": success, "failed": failed, "avg_duration_ms": float(avg_ms)}


def most_used_workflows(session: Session, limit: int = 5) -> list[tuple[int, str, int]]:
    """(workflow_id, name, execution_count), 1 query."""
    rows = session.execute(
        select(Workflow.id, Workflow.name, func.count(WorkflowExecution.id).label("cnt"))
        .join(WorkflowExecution, WorkflowExecution.workflow_id == Workflow.id)
        .group_by(Workflow.id, Workflow.name)
        .order_by(func.count(WorkflowExecution.id).desc())
        .limit(limit)
    ).all()
    return [(r[0], r[1], r[2]) for r in rows]


def recent_executions(session: Session, limit: int = 10) -> list[WorkflowExecution]:
    return list(session.scalars(select(WorkflowExecution).order_by(WorkflowExecution.id.desc()).limit(limit)))


# ----------------------------------------------------------------- approvals
def create_approval(session: Session, **kw) -> ApprovalRequest:
    a = ApprovalRequest(**kw)
    session.add(a)
    session.flush()
    return a


def get_approval(session: Session, approval_id: int) -> ApprovalRequest | None:
    return session.get(ApprovalRequest, approval_id)


def list_approvals(
    session: Session, *, status: str | None = None, approval_type: str | None = None,
    limit: int = 50, offset: int = 0,
) -> tuple[list[ApprovalRequest], int]:
    q = select(ApprovalRequest)
    filters = []
    if status:
        filters.append(ApprovalRequest.status == status)
    if approval_type:
        filters.append(ApprovalRequest.approval_type == approval_type)
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(ApprovalRequest.id.desc()).limit(limit).offset(offset)))
    return rows, total


def count_pending_approvals(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(ApprovalRequest).where(ApprovalRequest.status == "pending")
    ) or 0


def avg_approval_time_hours(session: Session) -> float | None:
    row = session.execute(
        select(ApprovalRequest.requested_at, ApprovalRequest.decided_at)
        .where(ApprovalRequest.decided_at.isnot(None))
    ).all()
    if not row:
        return None
    total_hours = 0.0
    for requested_at, decided_at in row:
        r = requested_at if requested_at.tzinfo else requested_at.replace(tzinfo=None)
        d = decided_at if decided_at.tzinfo else decided_at.replace(tzinfo=None)
        total_hours += (d - r).total_seconds() / 3600
    return round(total_hours / len(row), 2)


# ----------------------------------------------------------------- SLA
def create_policy(session: Session, **kw) -> SlaPolicy:
    p = SlaPolicy(**kw)
    session.add(p)
    session.flush()
    return p


def get_policy(session: Session, policy_id: int) -> SlaPolicy | None:
    return session.get(SlaPolicy, policy_id)


def list_policies(session: Session, *, entity_type: str | None = None) -> list[SlaPolicy]:
    q = select(SlaPolicy)
    if entity_type:
        q = q.where(SlaPolicy.entity_type == entity_type)
    return list(session.scalars(q.order_by(SlaPolicy.id.desc())))


def create_tracker(session: Session, **kw) -> SlaTracker:
    t = SlaTracker(**kw)
    session.add(t)
    session.flush()
    return t


def get_tracker(session: Session, tracker_id: int) -> SlaTracker | None:
    return session.get(SlaTracker, tracker_id)


def list_trackers(
    session: Session, *, status: str | None = None, limit: int = 50, offset: int = 0,
) -> tuple[list[SlaTracker], int]:
    q = select(SlaTracker)
    if status:
        q = q.where(SlaTracker.status == status)
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(SlaTracker.id.desc()).limit(limit).offset(offset)))
    return rows, total


def open_trackers(session: Session) -> list[SlaTracker]:
    """Trackers not yet resolved — candidates for the breach/escalation sweep. 1 query."""
    return list(session.scalars(
        select(SlaTracker).where(SlaTracker.status.in_(("on_track", "at_risk")))
    ))


def count_breaches(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(SlaTracker).where(SlaTracker.status.in_(("breached", "escalated")))
    ) or 0


def sla_compliance_rate(session: Session) -> float:
    """Fraction of resolved trackers that resolved before breaching. 1 query."""
    row = session.execute(
        select(
            func.count(SlaTracker.id).filter(SlaTracker.status == "resolved"),
            func.count(SlaTracker.id).filter(SlaTracker.status.in_(("breached", "escalated", "resolved"))),
        )
    ).one()
    resolved_clean, total_closed = row
    if not total_closed:
        return 1.0
    return round(resolved_clean / total_closed, 4)
