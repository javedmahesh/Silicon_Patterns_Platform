"""Import review & approval (Phase 5).

Seeds a reviewable item per preview record, records per-field keep-platform/
accept-historical decisions and an immutable audit trail, and builds the
**approved** preview the (unchanged) transaction engine consumes at commit —
so only approved/resolved records ever reach the database and rejected records
never do. No synchronization or matching logic lives here.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config.enums import REVIEW_IMPORTABLE_STATES
from master_db.models import ImportJob, ImportReviewEvent, ImportReviewItem

_PENDING_CATEGORIES = {
    "new_company", "updated_company", "new_decision_maker", "updated_decision_maker", "conflict",
}
_DECISION_STATE = {"approve": "approved", "reject": "rejected", "skip": "skipped"}


# ---------------------------------------------------------------- derivation
def _category(kind: str, classification: str) -> str:
    if classification == "new":
        return "new_company" if kind == "company" else "new_decision_maker"
    if classification == "update":
        return "updated_company" if kind == "company" else "updated_decision_maker"
    return classification  # conflict | duplicate | invalid | unchanged


def _default_state(category: str) -> str:
    return "pending" if category in _PENDING_CATEGORIES else "skipped"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _preview_maps(job: ImportJob) -> tuple[dict, dict]:
    prev = job.preview or {}
    co = {r.get("source_ref"): r for r in prev.get("companies", {}).get("results", [])}
    dm = {r.get("source_ref"): r for r in prev.get("decision_makers", {}).get("results", [])}
    return co, dm


def field_diffs(orig: dict, decisions: dict) -> list[dict]:
    """Field-level review rows for one record: platform vs historical + current choice."""
    out: list[dict] = []
    for c in orig.get("changes", []):
        out.append({"field": c["field"], "platform_value": c["current"],
                    "historical_value": c["proposed"], "is_conflict": False,
                    "decision": decisions.get(c["field"], "accept_historical")})
    for c in orig.get("conflicts", []):
        out.append({"field": c["field"], "platform_value": c["current"],
                    "historical_value": c["proposed"], "is_conflict": True,
                    "decision": decisions.get(c["field"], "keep_platform")})
    return out


# ---------------------------------------------------------------- seeding
def seed_review_items(session: Session, job: ImportJob) -> int:
    """Create one review item per preview record (idempotent per job)."""
    if session.scalar(select(func.count()).select_from(ImportReviewItem)
                      .where(ImportReviewItem.job_id == job.id)):
        return 0
    prev = job.preview or {}
    items: list[ImportReviewItem] = []
    for kind, key, label_key in (("company", "companies", "raw_name"),
                                 ("decision_maker", "decision_makers", "full_name")):
        for res in prev.get(key, {}).get("results", []):
            cat = _category(kind, res.get("classification", ""))
            items.append(ImportReviewItem(
                job_id=job.id, record_kind=kind, source_ref=res.get("source_ref", ""),
                category=cat, state=_default_state(cat), label=res.get(label_key) or "",
                field_decisions={},
            ))
    session.add_all(items)
    session.commit()
    return len(items)


# ---------------------------------------------------------------- queries
def _get_item(session: Session, job: ImportJob, kind: str, source_ref: str) -> ImportReviewItem | None:
    return session.scalar(select(ImportReviewItem).where(
        ImportReviewItem.job_id == job.id, ImportReviewItem.record_kind == kind,
        ImportReviewItem.source_ref == source_ref))


def item_to_dict(item: ImportReviewItem, orig: dict) -> dict[str, Any]:
    return {
        "record_kind": item.record_kind, "source_ref": item.source_ref,
        "category": item.category, "state": item.state, "label": item.label,
        "reviewer": item.reviewer, "reason": item.reason,
        "match_type": orig.get("match_type"),
        "resolved_domain": orig.get("resolved_domain") or orig.get("resolved_company_domain"),
        "fields": field_diffs(orig, item.field_decisions or {}),
    }


def list_review_items(session: Session, job: ImportJob, *, category=None, state=None) -> list[dict]:
    q = select(ImportReviewItem).where(ImportReviewItem.job_id == job.id)
    if category:
        q = q.where(ImportReviewItem.category == category)
    if state:
        q = q.where(ImportReviewItem.state == state)
    co, dm = _preview_maps(job)
    return [item_to_dict(it, (co if it.record_kind == "company" else dm).get(it.source_ref, {}))
            for it in session.scalars(q.order_by(ImportReviewItem.id)).all()]


def statistics(session: Session, job: ImportJob) -> dict[str, Any]:
    items = session.scalars(select(ImportReviewItem).where(ImportReviewItem.job_id == job.id)).all()
    by_state = Counter(i.state for i in items)
    by_category = Counter(i.category for i in items)
    importable = sum(by_state.get(s, 0) for s in REVIEW_IMPORTABLE_STATES)
    return {"total": len(items), "by_state": dict(by_state), "by_category": dict(by_category),
            "importable": importable, "pending": by_state.get("pending", 0)}


# ---------------------------------------------------------------- mutations
def _event(session, job, item, action, *, field="", prev="", approved="", reviewer="", reason="") -> None:
    session.add(ImportReviewEvent(
        job_id=job.id, review_item_id=(item.id if item else None),
        record_kind=(item.record_kind if item else ""),
        source_ref=(item.source_ref if item else ""), action=action, field=field,
        previous_value=str(prev), approved_value=str(approved), reviewer=reviewer, reason=reason))


def decide(session: Session, job: ImportJob, *, kind: str, source_ref: str,
           decision: str, reviewer: str = "", reason: str = "") -> ImportReviewItem | None:
    item = _get_item(session, job, kind, source_ref)
    if item is None or decision not in _DECISION_STATE:
        return None
    prev = item.state
    item.state = _DECISION_STATE[decision]
    item.reviewer, item.reason, item.decided_at = reviewer, reason, _now()
    _event(session, job, item, decision, prev=prev, approved=item.state, reviewer=reviewer, reason=reason)
    session.commit()
    return item


def resolve_field(session: Session, job: ImportJob, *, kind: str, source_ref: str, field: str,
                  choice: str, reviewer: str = "", reason: str = "") -> ImportReviewItem | None:
    item = _get_item(session, job, kind, source_ref)
    if item is None or choice not in ("keep_platform", "accept_historical"):
        return None
    co, dm = _preview_maps(job)
    orig = (co if kind == "company" else dm).get(source_ref, {})
    diff = {d["field"]: d for d in field_diffs(orig, item.field_decisions or {})}.get(field)
    item.field_decisions = {**(item.field_decisions or {}), field: choice}   # reassign for JSON change-tracking
    if item.category == "conflict":
        conflict_fields = [c["field"] for c in orig.get("conflicts", [])]
        decided = {f: item.field_decisions.get(f) for f in conflict_fields}
        if all(decided.values()):
            item.state = "resolved" if any(v == "accept_historical" for v in decided.values()) else "skipped"
    item.reviewer, item.decided_at = reviewer, _now()
    prev = diff["platform_value"] if diff else ""
    approved = (diff["historical_value"] if (diff and choice == "accept_historical")
                else (diff["platform_value"] if diff else ""))
    _event(session, job, item, "resolve_field", field=field, prev=prev, approved=approved,
           reviewer=reviewer, reason=reason)
    session.commit()
    return item


def bulk(session: Session, job: ImportJob, *, action: str, reviewer: str = "",
         refs: list[dict] | None = None, category: str | None = None) -> int:
    approve = action.startswith("approve")
    target = "approved" if approve else "rejected"
    refset = {(r.get("kind"), r.get("source_ref")) for r in refs} if refs else None
    changed = 0
    for it in session.scalars(select(ImportReviewItem).where(ImportReviewItem.job_id == job.id)).all():
        if action in ("approve_all", "reject_all"):
            if it.state != "pending":
                continue
        elif action in ("approve_category", "reject_category"):
            if it.category != category:
                continue
        elif action in ("approve_selected", "reject_selected"):
            if (it.record_kind, it.source_ref) not in (refset or set()):
                continue
        else:
            return 0
        it.state, it.reviewer, it.decided_at = target, reviewer, _now()
        changed += 1
    _event(session, job, None, "bulk_approve" if approve else "bulk_reject",
           approved=str(changed), reviewer=reviewer, reason=(category or action))
    session.commit()
    return changed


def audit_trail(session: Session, job: ImportJob) -> list[dict]:
    rows = session.scalars(select(ImportReviewEvent).where(ImportReviewEvent.job_id == job.id)
                           .order_by(ImportReviewEvent.id)).all()
    return [{"action": e.action, "record_kind": e.record_kind, "source_ref": e.source_ref,
             "field": e.field, "previous_value": e.previous_value, "approved_value": e.approved_value,
             "reviewer": e.reviewer, "reason": e.reason,
             "at": e.created_at.isoformat() if e.created_at else None} for e in rows]


# ---------------------------------------------------- feed the import engine
def build_approved_previews(session: Session, job: ImportJob) -> tuple[dict, dict]:
    """Assemble the company + DM preview dicts of ONLY approved/resolved records, with
    each record's changes filtered by its field decisions (keep-platform dropped,
    accept-historical conflict fields promoted to updates). Consumed as-is by the
    unchanged transaction engine — rejected/skipped/pending records never appear."""
    co_map, dm_map = _preview_maps(job)
    items = session.scalars(select(ImportReviewItem).where(
        ImportReviewItem.job_id == job.id,
        ImportReviewItem.state.in_(REVIEW_IMPORTABLE_STATES))).all()
    co_results: list[dict] = []
    dm_results: list[dict] = []
    for it in items:
        orig = (co_map if it.record_kind == "company" else dm_map).get(it.source_ref)
        if not orig:
            continue
        decisions = it.field_decisions or {}
        changes = [c for c in orig.get("changes", []) if decisions.get(c["field"]) != "keep_platform"]
        for c in orig.get("conflicts", []):
            if decisions.get(c["field"]) == "accept_historical":
                changes.append({**c, "action": "update"})
        result = {**orig, "changes": changes}
        if orig.get("classification") == "conflict":
            result["classification"] = "update"     # apply the resolved fields as an update
        (co_results if it.record_kind == "company" else dm_results).append(result)
    return {"results": co_results}, {"results": dm_results}
