"""Enterprise CRM Phase 6: Workflow Automation & Business Process Engine.

The engine is deliberately small: `fire_event()` is the single entry point every
other service calls after a business mutation. It loads the (cached) active
workflow definitions for that trigger, evaluates their conditions against a
plain ``fields`` dict the caller assembles from data it already has in scope,
and executes matching actions by delegating to the existing repos (deal_repo,
cs_repo, outreach_repo, collab_repo) — no new side-effect infrastructure.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import admin_service
from backend import cs_repo
from backend import deal_repo
from backend import integration_service
from backend import outreach_repo
from backend import collab_repo
from backend import workflow_repo as repo
from backend.tick_lock import single_flight
from backend.schemas import (
    ApprovalDecisionIn,
    ApprovalRequestCreate,
    ApprovalRequestOut,
    Page,
    RenewalScanResultOut,
    SlaPolicyCreate,
    SlaPolicyOut,
    SlaPolicyPatch,
    SlaTickResultOut,
    SlaTrackerCreate,
    SlaTrackerOut,
    WorkflowActionResult,
    WorkflowAnalyticsOut,
    WorkflowCreate,
    WorkflowDashboardOut,
    WorkflowExecutionOut,
    WorkflowOut,
    WorkflowPatch,
    WorkflowUsageOut,
)
from config.enums import COLLAB_ENTITY_TYPES, COLLAB_NOTIF_TYPES
from master_db.models import CsAccount, User

from backend.timeutil import utc as _utc, utcnow as _utcnow


def _is_manager(user) -> bool:
    return getattr(user, "role", "member") in ("admin", "manager")


def _require_manager(user) -> None:
    if not _is_manager(user):
        raise HTTPException(403, "manager or admin required")


def _load_user_emails(session: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    from sqlalchemy import select
    rows = session.scalars(select(User).where(User.id.in_(ids))).all()
    return {u.id: u.email for u in rows}


# ================================================================== condition evaluation
def _eval_rule(fields: dict, rule: dict) -> bool:
    actual = fields.get(rule.get("field"))
    target = rule.get("value")
    op = rule.get("op", "eq")
    if op == "eq":
        return actual == target
    if op == "neq":
        return actual != target
    if op == "gt":
        return actual is not None and target is not None and actual > target
    if op == "gte":
        return actual is not None and target is not None and actual >= target
    if op == "lt":
        return actual is not None and target is not None and actual < target
    if op == "lte":
        return actual is not None and target is not None and actual <= target
    if op == "in":
        return actual in (target or [])
    if op == "contains":
        return target in (actual or [])
    return False


def _eval_group(fields: dict, group: dict) -> bool:
    rules = group.get("rules") or []
    if not rules:
        return True
    results = [_eval_rule(fields, r) for r in rules]
    return all(results) if group.get("logic", "AND") == "AND" else any(results)


def evaluate_conditions(fields: dict, conditions: dict | None) -> bool:
    """Deterministic AND/OR condition-group evaluation. No conditions == always match."""
    conditions = conditions or {}
    groups = conditions.get("groups") or []
    if not groups:
        return True
    results = [_eval_group(fields, g) for g in groups]
    return all(results) if conditions.get("logic", "AND") == "AND" else any(results)


# ================================================================== action execution
def _task_action(session: Session, fields: dict, params: dict, actor, *, kind: str) -> WorkflowActionResult:
    due_hours = params.get("due_in_hours", params.get("remind_in_hours", 24))
    title = params.get("title") or f"{kind.replace('_', ' ').title()}: {fields.get('title') or fields.get('name') or ''}".strip()
    task = outreach_repo.create_task(
        session,
        title=title[:512], description=params.get("description", ""),
        company_domain=fields.get("company_domain"),
        assigned_to=params.get("assigned_to") or fields.get("owner_id"),
        priority=params.get("priority", "medium"),
        due_at=_utcnow() + timedelta(hours=due_hours) if due_hours else None,
        created_by=getattr(actor, "id", None),
    )
    return WorkflowActionResult(type=kind, ok=True, detail=f"created task #{task.id}")


def _assign_owner_action(session: Session, entity_type: str, entity_id: str, params: dict, fields: dict, actor) -> WorkflowActionResult:
    user_id = params.get("user_id") or fields.get("owner_id")
    if not user_id:
        return WorkflowActionResult(type="assign_owner", ok=False, detail="no user_id resolved")
    if entity_type in COLLAB_ENTITY_TYPES:
        collab_repo.create_assignment(
            session, entity_type=entity_type, entity_id=str(entity_id), user_id=user_id,
            role=params.get("role", "owner"), assigned_by=getattr(actor, "id", None), note="",
        )
        return WorkflowActionResult(type="assign_owner", ok=True, detail=f"assigned user {user_id} on {entity_type}#{entity_id}")
    if entity_type == "customer":
        acct = session.get(CsAccount, int(entity_id)) if entity_id else None
        if not acct:
            return WorkflowActionResult(type="assign_owner", ok=False, detail="cs account not found")
        acct.owner_id = user_id
        return WorkflowActionResult(type="assign_owner", ok=True, detail=f"assigned user {user_id} on customer#{entity_id}")
    return WorkflowActionResult(type="assign_owner", ok=False, detail=f"unsupported entity_type: {entity_type}")


def _notify_action(session: Session, entity_type: str, entity_id: str, params: dict, fields: dict, actor) -> WorkflowActionResult:
    user_id = params.get("user_id") or fields.get("owner_id")
    if not user_id:
        return WorkflowActionResult(type="send_notification", ok=False, detail="no user_id resolved")
    notif_type = params.get("notif_type")
    if notif_type not in COLLAB_NOTIF_TYPES:
        notif_type = "task_due"
    collab_repo.notify(
        session, user_id=user_id, notif_type=notif_type,
        title=params.get("title", "Workflow notification"), body=params.get("body", ""),
        entity_type=entity_type if entity_type in COLLAB_ENTITY_TYPES else None,
        entity_id=str(entity_id) if entity_type in COLLAB_ENTITY_TYPES else None,
    )
    return WorkflowActionResult(type="send_notification", ok=True, detail=f"notified user {user_id}")


_DEAL_UPDATABLE_FIELDS = {"probability", "forecast_category", "notes", "lost_reason", "won_reason"}
_CUSTOMER_UPDATABLE_FIELDS = {"status", "tier", "lifecycle_stage", "notes"}


def _update_fields_action(session: Session, entity_type: str, entity_id: str, params: dict) -> WorkflowActionResult:
    updates = params.get("fields") or {}
    if entity_type == "deal":
        deal = deal_repo.get_deal(session, int(entity_id)) if entity_id else None
        if not deal:
            return WorkflowActionResult(type="update_fields", ok=False, detail="deal not found")
        applied = {k: v for k, v in updates.items() if k in _DEAL_UPDATABLE_FIELDS}
        for k, v in applied.items():
            setattr(deal, k, v)
        return WorkflowActionResult(type="update_fields", ok=True, detail=f"updated {list(applied)} on deal#{entity_id}")
    if entity_type == "customer":
        acct = session.get(CsAccount, int(entity_id)) if entity_id else None
        if not acct:
            return WorkflowActionResult(type="update_fields", ok=False, detail="cs account not found")
        applied = {k: v for k, v in updates.items() if k in _CUSTOMER_UPDATABLE_FIELDS}
        for k, v in applied.items():
            setattr(acct, k, v)
        return WorkflowActionResult(type="update_fields", ok=True, detail=f"updated {list(applied)} on customer#{entity_id}")
    return WorkflowActionResult(type="update_fields", ok=False, detail=f"unsupported entity_type: {entity_type}")


def _create_activity_action(session: Session, entity_type: str, entity_id: str, params: dict, actor) -> WorkflowActionResult:
    detail = params.get("detail", "workflow action")
    if entity_type in COLLAB_ENTITY_TYPES:
        collab_repo.create_comment(
            session, entity_type=entity_type, entity_id=str(entity_id),
            author_id=getattr(actor, "id", None), body=f"[automation] {detail}", mentions=[],
        )
        return WorkflowActionResult(type="create_activity", ok=True, detail=f"logged activity on {entity_type}#{entity_id}")
    if entity_type == "customer":
        acct = session.get(CsAccount, int(entity_id)) if entity_id else None
        if not acct:
            return WorkflowActionResult(type="create_activity", ok=False, detail="cs account not found")
        cs_repo.add_lifecycle_event(
            session, account_id=acct.id, stage=acct.lifecycle_stage, from_stage=acct.lifecycle_stage,
            changed_by=getattr(actor, "id", None), note=f"[automation] {detail}",
        )
        return WorkflowActionResult(type="create_activity", ok=True, detail=f"logged activity on customer#{entity_id}")
    return WorkflowActionResult(type="create_activity", ok=False, detail=f"unsupported entity_type: {entity_type}")


def _create_deal_action(session: Session, params: dict, fields: dict, actor) -> WorkflowActionResult:
    pipeline_id, stage_id = params.get("pipeline_id"), params.get("stage_id")
    company_domain = params.get("company_domain") or fields.get("company_domain")
    if not (pipeline_id and stage_id and company_domain):
        return WorkflowActionResult(type="create_deal", ok=False, detail="pipeline_id/stage_id/company_domain required")
    deal = deal_repo.create_deal(
        session, title=params.get("title", "Automated deal"), company_domain=company_domain,
        pipeline_id=pipeline_id, stage_id=stage_id,
        owner_id=params.get("owner_id") or fields.get("owner_id"), created_by=getattr(actor, "id", None),
        value=params.get("value"), currency=params.get("currency", "USD"),
        probability=params.get("probability", 0), forecast_category=params.get("forecast_category", "pipeline"),
        last_activity_at=_utcnow(),
    )
    return WorkflowActionResult(type="create_deal", ok=True, detail=f"created deal #{deal.id}")


def _execute_action(session: Session, action: dict, entity_type: str, entity_id: str, fields: dict, actor) -> WorkflowActionResult:
    atype = action.get("type", "")
    params = action.get("params") or {}
    try:
        if atype in ("create_task", "create_follow_up", "create_success_task"):
            return _task_action(session, fields, params, actor, kind=atype)
        if atype == "schedule_reminder":
            return _task_action(session, fields, params, actor, kind="schedule_reminder")
        if atype == "assign_owner":
            return _assign_owner_action(session, entity_type, entity_id, params, fields, actor)
        if atype == "send_notification":
            return _notify_action(session, entity_type, entity_id, params, fields, actor)
        if atype == "update_fields":
            return _update_fields_action(session, entity_type, entity_id, params)
        if atype == "create_activity":
            return _create_activity_action(session, entity_type, entity_id, params, actor)
        if atype == "create_deal":
            return _create_deal_action(session, params, fields, actor)
        if atype == "create_opportunity":
            # ponytail: Opportunity rows are Blog-Crawler-owned (ingestion pipeline), not
            # CRM-user-owned. Upgrade path: add a manually-sourced Opportunity table if a
            # real product need for user-created opportunities emerges.
            return WorkflowActionResult(type=atype, ok=False, detail="opportunities are ingestion-owned; not creatable from a workflow")
        return WorkflowActionResult(type=atype, ok=False, detail=f"unknown action type: {atype}")
    except Exception as exc:  # noqa: BLE001 - one bad action must not abort the whole run
        return WorkflowActionResult(type=atype, ok=False, detail=str(exc)[:500])


# ================================================================== workflow definition cache
_DEF_TTL_SECONDS = 30
_def_cache: dict[str, tuple[float, list]] = {}


def _cache_key(session: Session, trigger_event: str) -> str:
    try:
        db_url = str(session.get_bind().url)
    except Exception:
        db_url = "default"
    return f"{db_url}::{trigger_event}"


def _active_workflows_cached(session: Session, trigger_event: str) -> list:
    key = _cache_key(session, trigger_event)
    cached = _def_cache.get(key)
    if cached and time.monotonic() - cached[0] < _DEF_TTL_SECONDS:
        return cached[1]
    rows = repo.active_workflows_for_trigger(session, trigger_event)
    _def_cache[key] = (time.monotonic(), rows)
    return rows


def invalidate_workflow_cache() -> None:
    _def_cache.clear()


# Phase 10 Event Bus reuse: maps each existing WORKFLOW_TRIGGER_EVENTS value to an
# EVENT_BUS_CATEGORIES bucket so fire_event can publish without a new taxonomy.
_TRIGGER_EVENT_BUS_CATEGORY = {
    "lead_created": "crm", "opportunity_created": "crm", "deal_created": "crm",
    "deal_stage_changed": "crm", "deal_won": "crm", "deal_lost": "crm",
    "customer_created": "customer", "health_changed": "customer", "contract_renewal_window": "customer",
    "campaign_status_changed": "crm",
}


def _json_safe(value):
    """Coerce a fields dict (may hold datetimes from callers like scan_renewal_windows)
    into something the integration_events JSON column can store without raising at
    flush time — a flush-time TypeError would poison the caller's still-open session."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


# ================================================================== engine entry point
def fire_event(
    session: Session, trigger_event: str, entity_type: str, entity_id: str | int,
    fields: dict, actor=None,
) -> list:
    """Evaluate + run every active workflow matching `trigger_event`. Does not commit —
    caller's own commit (right after this call) persists everything atomically."""
    entity_id = str(entity_id)
    executions = []
    for wf in _active_workflows_cached(session, trigger_event):
        if not evaluate_conditions(fields, wf.conditions):
            continue
        started = _utcnow()
        t0 = time.monotonic()
        results = [
            _execute_action(session, action, entity_type, entity_id, fields, actor)
            for action in (wf.actions or [])
        ]
        duration_ms = int((time.monotonic() - t0) * 1000)
        ok_count = sum(1 for r in results if r.ok)
        if not results or ok_count == len(results):
            status = "success"
        elif ok_count == 0:
            status = "failed"
        else:
            status = "partial"
        execution = repo.create_execution(
            session, workflow_id=wf.id, trigger_event=trigger_event,
            entity_type=entity_type, entity_id=entity_id, status=status,
            actions_executed=[r.model_dump() for r in results],
            error_detail="" if status == "success" else "; ".join(r.detail for r in results if not r.ok),
            started_at=started, completed_at=_utcnow(), duration_ms=duration_ms,
        )
        executions.append(execution)
    try:
        integration_service.publish_event(
            session, category=_TRIGGER_EVENT_BUS_CATEGORY.get(trigger_event, "workflow"),
            event_type=trigger_event, entity_type=entity_type, entity_id=entity_id,
            payload={"executions": len(executions), **_json_safe(fields)},
        )
    except Exception:  # noqa: BLE001 - Event Bus/webhook dispatch must never break the workflow engine
        pass
    return executions


# ================================================================== workflow CRUD
def _workflow_out(w) -> WorkflowOut:
    return WorkflowOut(
        id=w.id, name=w.name, description=w.description, status=w.status,
        trigger_event=w.trigger_event, conditions=w.conditions or {}, actions=w.actions or [],
        version=w.version, is_enabled=w.is_enabled, created_by=w.created_by,
        created_at=_utc(w.created_at), updated_at=_utc(w.updated_at),
    )


def list_workflows(session: Session, user, *, status: str | None = None, trigger_event: str | None = None, limit: int = 50, offset: int = 0) -> Page:
    rows, total = repo.list_workflows(session, status=status, trigger_event=trigger_event, limit=limit, offset=offset)
    return Page.build([_workflow_out(w) for w in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


def create_workflow(session: Session, data: WorkflowCreate, user) -> WorkflowOut:
    _require_manager(user)
    w = repo.create_workflow(
        session, name=data.name, description=data.description, status=data.status,
        trigger_event=data.trigger_event, conditions=data.conditions.model_dump(),
        actions=[a.model_dump() for a in data.actions], is_enabled=data.is_enabled,
        created_by=user.id,
    )
    admin_service.log_audit_event(session, category="workflow_change", action="workflow_created", actor=user, entity_type="workflow", entity_id=w.id)
    session.commit()
    invalidate_workflow_cache()
    return _workflow_out(w)


def get_workflow(session: Session, workflow_id: int, user) -> WorkflowOut:
    w = repo.get_workflow(session, workflow_id)
    if not w:
        raise HTTPException(404, "workflow not found")
    return _workflow_out(w)


def patch_workflow(session: Session, workflow_id: int, data: WorkflowPatch, user) -> WorkflowOut:
    _require_manager(user)
    w = repo.get_workflow(session, workflow_id)
    if not w:
        raise HTTPException(404, "workflow not found")
    if data.name is not None:
        w.name = data.name
    if data.description is not None:
        w.description = data.description
    if data.status is not None:
        w.status = data.status
    if data.conditions is not None:
        w.conditions = data.conditions.model_dump()
    if data.actions is not None:
        w.actions = [a.model_dump() for a in data.actions]
    if data.is_enabled is not None:
        w.is_enabled = data.is_enabled
    if any(f is not None for f in (data.conditions, data.actions, data.status, data.is_enabled)):
        w.version += 1
    admin_service.log_audit_event(session, category="workflow_change", action="workflow_updated", actor=user, entity_type="workflow", entity_id=workflow_id)
    session.commit()
    invalidate_workflow_cache()
    return _workflow_out(w)


def delete_workflow(session: Session, workflow_id: int, user) -> None:
    _require_manager(user)
    if not repo.delete_workflow(session, workflow_id):
        raise HTTPException(404, "workflow not found")
    admin_service.log_audit_event(session, category="workflow_change", action="workflow_deleted", actor=user, entity_type="workflow", entity_id=workflow_id)
    session.commit()
    invalidate_workflow_cache()


def _execution_out(e, name_map: dict[int, str]) -> WorkflowExecutionOut:
    return WorkflowExecutionOut(
        id=e.id, workflow_id=e.workflow_id, workflow_name=name_map.get(e.workflow_id, ""),
        trigger_event=e.trigger_event, entity_type=e.entity_type, entity_id=e.entity_id,
        status=e.status, actions_executed=e.actions_executed or [], error_detail=e.error_detail,
        started_at=_utc(e.started_at), completed_at=_utc(e.completed_at), duration_ms=e.duration_ms,
    )


def list_executions(session: Session, user, *, workflow_id: int | None = None, entity_type: str | None = None, entity_id: str | None = None, limit: int = 50, offset: int = 0) -> Page:
    rows, total = repo.list_executions(session, workflow_id=workflow_id, entity_type=entity_type, entity_id=entity_id, limit=limit, offset=offset)
    name_map = repo.get_workflow_names(session, [r.workflow_id for r in rows])
    return Page.build([_execution_out(e, name_map) for e in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


# ================================================================== approvals
def _approval_out(a, email_map: dict[int, str]) -> ApprovalRequestOut:
    return ApprovalRequestOut(
        id=a.id, approval_type=a.approval_type, entity_type=a.entity_type, entity_id=a.entity_id,
        requested_by=a.requested_by, requested_by_email=email_map.get(a.requested_by, ""),
        approver_id=a.approver_id, approver_email=email_map.get(a.approver_id, ""),
        status=a.status, decision_reason=a.decision_reason,
        workflow_execution_id=a.workflow_execution_id,
        requested_at=_utc(a.requested_at), decided_at=_utc(a.decided_at),
    )


def create_approval(session: Session, data: ApprovalRequestCreate, user) -> ApprovalRequestOut:
    a = repo.create_approval(
        session, approval_type=data.approval_type, entity_type=data.entity_type,
        entity_id=data.entity_id, requested_by=user.id, approver_id=data.approver_id,
    )
    session.commit()
    email_map = _load_user_emails(session, [x for x in (user.id, data.approver_id) if x])
    return _approval_out(a, email_map)


def list_approvals(session: Session, user, *, status: str | None = None, approval_type: str | None = None, limit: int = 50, offset: int = 0) -> Page:
    rows, total = repo.list_approvals(session, status=status, approval_type=approval_type, limit=limit, offset=offset)
    ids = [x for a in rows for x in (a.requested_by, a.approver_id) if x]
    email_map = _load_user_emails(session, ids)
    return Page.build([_approval_out(a, email_map) for a in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


def get_approval(session: Session, approval_id: int, user) -> ApprovalRequestOut:
    a = repo.get_approval(session, approval_id)
    if not a:
        raise HTTPException(404, "approval request not found")
    email_map = _load_user_emails(session, [x for x in (a.requested_by, a.approver_id) if x])
    return _approval_out(a, email_map)


def decide_approval(session: Session, approval_id: int, data: ApprovalDecisionIn, user) -> ApprovalRequestOut:
    a = repo.get_approval(session, approval_id)
    if not a:
        raise HTTPException(404, "approval request not found")
    if a.status != "pending":
        raise HTTPException(409, "approval already decided")
    if data.decision not in ("approved", "rejected"):
        raise HTTPException(422, "decision must be 'approved' or 'rejected'")
    if not _is_manager(user) and a.approver_id != user.id:
        raise HTTPException(403, "only the designated approver or a manager may decide")
    a.status = data.decision
    a.decision_reason = data.comments
    a.approver_id = a.approver_id or user.id
    a.decided_at = _utcnow()
    session.commit()
    email_map = _load_user_emails(session, [x for x in (a.requested_by, a.approver_id) if x])
    return _approval_out(a, email_map)


# ================================================================== SLA management
def _policy_out(p) -> SlaPolicyOut:
    return SlaPolicyOut(
        id=p.id, name=p.name, entity_type=p.entity_type, trigger_event=p.trigger_event,
        due_hours=p.due_hours, escalate_after_hours=p.escalate_after_hours,
        escalate_to_user_id=p.escalate_to_user_id, is_enabled=p.is_enabled,
        created_at=_utc(p.created_at), updated_at=_utc(p.updated_at),
    )


def create_sla_policy(session: Session, data: SlaPolicyCreate, user) -> SlaPolicyOut:
    _require_manager(user)
    p = repo.create_policy(
        session, name=data.name, entity_type=data.entity_type, trigger_event=data.trigger_event,
        due_hours=data.due_hours, escalate_after_hours=data.escalate_after_hours,
        escalate_to_user_id=data.escalate_to_user_id, is_enabled=data.is_enabled,
    )
    session.commit()
    return _policy_out(p)


def list_sla_policies(session: Session, user, *, entity_type: str | None = None) -> list[SlaPolicyOut]:
    return [_policy_out(p) for p in repo.list_policies(session, entity_type=entity_type)]


def patch_sla_policy(session: Session, policy_id: int, data: SlaPolicyPatch, user) -> SlaPolicyOut:
    _require_manager(user)
    p = repo.get_policy(session, policy_id)
    if not p:
        raise HTTPException(404, "policy not found")
    for field in ("name", "due_hours", "escalate_after_hours", "escalate_to_user_id", "is_enabled"):
        val = getattr(data, field)
        if val is not None:
            setattr(p, field, val)
    session.commit()
    return _policy_out(p)


def _tracker_out(t) -> SlaTrackerOut:
    return SlaTrackerOut(
        id=t.id, policy_id=t.policy_id, entity_type=t.entity_type, entity_id=t.entity_id,
        due_at=_utc(t.due_at), status=t.status, escalated_at=_utc(t.escalated_at),
        breached_at=_utc(t.breached_at), resolved_at=_utc(t.resolved_at), created_at=_utc(t.created_at),
    )


def create_sla_tracker(session: Session, data: SlaTrackerCreate, user) -> SlaTrackerOut:
    policy = repo.get_policy(session, data.policy_id)
    if not policy:
        raise HTTPException(404, "policy not found")
    due_at = data.due_at or (_utcnow() + timedelta(hours=policy.due_hours))
    t = repo.create_tracker(
        session, policy_id=data.policy_id, entity_type=data.entity_type,
        entity_id=data.entity_id, due_at=due_at,
    )
    session.commit()
    return _tracker_out(t)


def list_sla_trackers(session: Session, user, *, status: str | None = None, limit: int = 50, offset: int = 0) -> Page:
    rows, total = repo.list_trackers(session, status=status, limit=limit, offset=offset)
    return Page.build([_tracker_out(t) for t in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


def resolve_sla_tracker(session: Session, tracker_id: int, user) -> SlaTrackerOut:
    t = repo.get_tracker(session, tracker_id)
    if not t:
        raise HTTPException(404, "tracker not found")
    t.status = "resolved"
    t.resolved_at = _utcnow()
    session.commit()
    return _tracker_out(t)


def scan_renewal_windows(session: Session, user, *, window_days: int = 90) -> RenewalScanResultOut:
    """Fire `contract_renewal_window` for every contract expiring within `window_days`.

    ponytail: fires on every call with no dedup — a contract inside the window gets
    re-evaluated (and any matching workflow re-run) each tick. Upgrade path: track a
    last-fired-at per contract if duplicate notifications become a real problem.
    """
    contracts = cs_repo.renewals_due(session, days=window_days)
    fired = 0
    for c in contracts:
        acct = cs_repo.get_account(session, c.account_id)
        if not acct:
            continue
        execs = fire_event(
            session, "contract_renewal_window", "customer", acct.id,
            {"owner_id": acct.owner_id, "company_domain": acct.company_domain, "tier": acct.tier,
             "contract_value": c.value, "end_date": _utc(c.end_date)},
            actor=user,
        )
        fired += len(execs)
    session.commit()
    return RenewalScanResultOut(workflows_fired=fired)


_AT_RISK_FRACTION = 0.2  # ponytail: flat 20%-of-window threshold; per-policy tuning if this proves wrong in practice


@single_flight("sla_tick")
def run_sla_tick(session: Session, user) -> SlaTickResultOut:
    """Sweep open trackers: mark at_risk / breached / escalated. Manual or cron-tick, same
    pattern as email_scheduler. single_flight prevents two overlapping cron pokes from
    double-processing the same trackers."""
    now = _utcnow()
    trackers = repo.open_trackers(session)
    policy_cache: dict[int, object] = {}
    checked = at_risk = breached = escalated = 0
    for t in trackers:
        checked += 1
        due_at = _utc(t.due_at)
        policy = policy_cache.setdefault(t.policy_id, repo.get_policy(session, t.policy_id))
        if due_at <= now:
            if t.status != "breached":
                t.status, t.breached_at = "breached", now
                breached += 1
            if policy and policy.escalate_after_hours is not None and now >= due_at + timedelta(hours=policy.escalate_after_hours):
                if t.status != "escalated":
                    t.status, t.escalated_at = "escalated", now
                    escalated += 1
                    if policy.escalate_to_user_id:
                        collab_repo.notify(
                            session, user_id=policy.escalate_to_user_id, notif_type="task_due",
                            title=f"SLA escalation: {policy.name}",
                            body=f"{t.entity_type}#{t.entity_id} breached its SLA and was escalated to you.",
                        )
            continue
        window_hours = policy.due_hours if policy else 24
        remaining_hours = (due_at - now).total_seconds() / 3600
        if remaining_hours <= window_hours * _AT_RISK_FRACTION and t.status == "on_track":
            t.status = "at_risk"
            at_risk += 1
    session.commit()
    return SlaTickResultOut(checked=checked, newly_at_risk=at_risk, newly_breached=breached, newly_escalated=escalated)


# ================================================================== dashboard + analytics
def workflow_dashboard(session: Session, user) -> WorkflowDashboardOut:
    stats = repo.execution_stats(session)
    success_rate = round(stats["success"] / stats["total"], 4) if stats["total"] else 0.0
    recent = repo.recent_executions(session, limit=10)
    name_map = repo.get_workflow_names(session, [r.workflow_id for r in recent])
    return WorkflowDashboardOut(
        active_workflows=repo.count_active_workflows(session),
        total_executions=stats["total"], success_rate=success_rate, failure_count=stats["failed"],
        pending_approvals=repo.count_pending_approvals(session),
        sla_breaches=repo.count_breaches(session),
        recent_executions=[_execution_out(e, name_map) for e in recent],
    )


def workflow_analytics(session: Session, user) -> WorkflowAnalyticsOut:
    stats = repo.execution_stats(session)
    total = stats["total"]
    success_rate = round(stats["success"] / total, 4) if total else 0.0
    failure_rate = round(stats["failed"] / total, 4) if total else 0.0
    most_used = repo.most_used_workflows(session)
    return WorkflowAnalyticsOut(
        execution_count=total, success_count=stats["success"], failure_count=stats["failed"],
        success_rate=success_rate, failure_rate=failure_rate,
        avg_execution_time_ms=round(stats["avg_duration_ms"], 1),
        avg_approval_time_hours=repo.avg_approval_time_hours(session),
        sla_compliance_rate=repo.sla_compliance_rate(session),
        most_used_workflows=[
            WorkflowUsageOut(workflow_id=wid, workflow_name=name, execution_count=cnt)
            for wid, name, cnt in most_used
        ],
    )
