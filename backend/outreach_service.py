"""Outreach business logic: pipeline, drafts/approvals, mock-mail, analytics.

Composes the outreach-only tables (via :mod:`backend.outreach_repo`) with the
platform's existing intelligence (companies, decision_makers, lead_scores,
engagement_recommendations, opportunities, users) read through
:mod:`backend.repositories`. Nothing here duplicates platform data.

Roles (reusing the platform's): admin/manager may approve mail, manage templates,
sync from Discovery and assign owners; any authenticated user (incl. members /
"employees") may view, qualify leads, draft mail, advance stages and add notes.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import dm_intelligence as dmi
from backend import relationship_intelligence as reli
from backend import outreach_repo as orepo
from backend import repositories as repo
from backend import workflow_service
from backend.config import get_settings
from backend.email_providers.registry import get_provider, get_provider_for_user
from backend.schemas import (
    BulkConversationIn,
    BulkMessageIn,
    BulkOperationOut,
    ContactHistoryOut,
    EmailAttachmentIn,
    EmailAttachmentOut,
    EmailConversationOut,
    EmailLabelIn,
    EmailLabelOut,
    EmailProviderAccountIn,
    EmailProviderAccountOut,
    EmailSchedulerTickOut,
    GmailAuthUrlOut,
    GmailConnectOut,
    GmailRefreshOut,
    GmailSyncResultOut,
    MessageForwardIn,
    MessagePreviewOut,
    MessageReplyIn,
    MessageScheduleIn,
    OutreachActivityOut,
    OutreachAnalytics,
    OutreachContactOut,
    OutreachDashboardOut,
    OutreachFollowUpItem,
    OutreachLeadCreate,
    OutreachLeadDetail,
    OutreachLeadOut,
    OutreachLeadPatch,
    OutreachMeetingIn,
    OutreachMeetingOut,
    OutreachMeetingPatch,
    OutreachMessageCreate,
    OutreachMessageOut,
    OutreachMessagePatch,
    OutreachSignalOut,
    OutreachStageCount,
    OutreachSyncResult,
    OutreachTaskIn,
    OutreachTaskOut,
    OutreachTaskPatch,
    OutreachTemplateIn,
    OutreachTemplateOut,
    OutreachThreadOut,
    Page,
    UnifiedTimelineEvent,
)
from config.enums import OUTREACH_OPEN_STAGES, OUTREACH_STAGES
from master_db.models import DecisionMaker

_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

from backend.timeutil import utcnow as _utcnow


def _utc(dt: datetime | None) -> datetime | None:
    """Make a datetime timezone-aware (UTC) — SQLite returns naive datetimes."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ----------------------------------------------------------------- permissions
def _is_manager(user) -> bool:
    return getattr(user, "role", None) in ("admin", "manager")


def _require_manager(user) -> None:
    if not _is_manager(user):
        raise HTTPException(status_code=403, detail="admin or manager role required")


# ----------------------------------------------------------------- mappers
def _priority_from_grade(grade: str | None) -> str:
    g = (grade or "").upper()
    if g in ("A+", "A"):
        return "high"
    if g == "B":
        return "medium"
    return "low" if g else ""


def _contact_out(dm: DecisionMaker, *, is_primary: bool = False) -> OutreachContactOut:
    name = (dm.full_name or " ".join(p for p in (dm.first_name, dm.last_name) if p)
            or dm.resolved_company_name or "Decision maker")
    return OutreachContactOut(
        decision_maker_id=dm.id,
        full_name=name,
        title=dm.current_title or dm.headline or "",
        email=dm.work_email or "",
        seniority=dm.seniority or "",
        linkedin_url=dm.linkedin_url or "",
        is_primary=is_primary,
    )


def _sorted_contacts(dms: list[DecisionMaker]) -> list[DecisionMaker]:
    # Most outreach-worthy first: has a work email, then senior, then match score.
    # Prioritising a reachable contact means the default draft recipient is sendable.
    return sorted(dms, key=lambda d: (not (d.work_email or "").strip(),
                                      d.seniority != "senior", -(d.match_score or 0.0)))


def _pick_primary(session: Session, lead, dms: list[DecisionMaker]) -> DecisionMaker | None:
    if lead.primary_dm_id:
        chosen = next((d for d in dms if d.id == lead.primary_dm_id), None)
        if chosen:
            return chosen
        chosen = repo.get_decision_maker(session, lead.primary_dm_id)
        if chosen:
            return chosen
    return _sorted_contacts(dms)[0] if dms else None


def _derive_service(company, engagement) -> str:
    pt = (getattr(company, "prospect_type", "") or "").upper()
    if engagement and engagement.offering:
        off = engagement.offering.lower()
        if "train" in off:
            return "training"
        if "staff" in off or "recruit" in off:
            return "staffing"
    if "SERVICE" in pt or "EDA" in pt or "FOUNDRY" in pt:
        return "engineering"
    return "engineering"


def _lead_out(session: Session, lead, company, score, *, msg_counts=None) -> OutreachLeadOut:
    dms = repo.decision_makers_for(session, lead.company_domain)
    primary = _pick_primary(session, lead, dms)
    engagement = repo.engagement_for(session, lead.company_domain)
    owner_email = ""
    if lead.owner_id:
        u = repo.get_user(session, lead.owner_id)
        owner_email = u.email if u else ""
    # Use precomputed (batched) counts on the list path; fall back to a per-lead query
    # for single-lead reads. The list NEVER queries opportunities per row — signal_summary
    # falls back to the lead's stored qualification_reason instead (no N+1).
    status_counts = msg_counts if msg_counts is not None else _lead_message_counts(session, lead.id)
    summary = (engagement.business_need if engagement and engagement.business_need
               else lead.qualification_reason) or "Qualified by Discovery lead scoring"
    return OutreachLeadOut(
        id=lead.id,
        company_domain=lead.company_domain,
        company_name=company.company_name if company else lead.company_domain,
        stage=lead.stage,
        service_interest=lead.service_interest,
        source=lead.source,
        owner_id=lead.owner_id,
        owner_email=owner_email,
        lead_score=score.lead_score if score else None,
        grade=score.grade if score else "",
        priority=_priority_from_grade(score.grade if score else None),
        signal_summary=summary,
        qualification_reason=lead.qualification_reason or "",
        primary_contact=_contact_out(primary, is_primary=True) if primary else None,
        open_messages=status_counts["open"],
        sent_messages=status_counts["sent"],
        reply_count=status_counts["replied"],
        next_action_at=lead.next_action_at,
        last_activity_at=lead.last_activity_at,
        qualified_at=lead.qualified_at,
        created_at=lead.created_at,
    )


def _lead_message_counts(session: Session, lead_id: int) -> dict[str, int]:
    msgs = orepo.list_messages_for_lead(session, lead_id)
    open_ = sum(1 for m in msgs if m.status in ("draft", "pending_approval", "approved"))
    sent = sum(1 for m in msgs if m.direction == "outbound" and m.status in ("sent", "replied"))
    replied = sum(1 for m in msgs if m.direction == "inbound")
    return {"open": open_, "sent": sent, "replied": replied}


# ----------------------------------------------------------------- leads: read
def list_leads(session: Session, *, stage=None, owner_id=None, mine_user_id=None,
               open_only=False, search=None, page=1, page_size=50) -> Page[OutreachLeadOut]:
    if mine_user_id is not None:
        owner_id = mine_user_id
    offset = (page - 1) * page_size
    rows, total = orepo.list_leads(session, stage=stage, owner_id=owner_id,
                                   open_only=open_only, search=search,
                                   limit=page_size, offset=offset)
    counts = orepo.message_counts_for_leads(session, [lead.id for lead, _c, _s in rows])
    items = [_lead_out(session, lead, company, score, msg_counts=counts[lead.id])
             for lead, company, score in rows]
    return Page.build(items, total, page, page_size)


def get_lead_detail(session: Session, lead_id: int) -> OutreachLeadDetail:
    lead = orepo.get_lead(session, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="outreach lead not found")
    company = repo.get_company(session, lead.company_domain)
    score = repo.lead_score_for(session, lead.company_domain)
    base = _lead_out(session, lead, company, score)
    engagement = repo.engagement_for(session, lead.company_domain)
    # Phase 2: rank contacts by decision intelligence (influence/confidence/dept/…)
    # and attach the scores + recommendation reason. An explicit primary_dm_id is a
    # manual override that wins over the recommended primary.
    dms = repo.decision_makers_for(session, lead.company_domain)
    ctx = dmi.context_for(session, lead.company_domain)
    ranked = dmi.rank_contacts(dms, ctx)
    override_id = lead.primary_dm_id
    contacts = []
    for rc in ranked:
        is_primary = (rc.dm.id == override_id) if override_id else (rc.rank == "primary")
        co = _contact_out(rc.dm, is_primary=is_primary)
        co.department = rc.intel.department
        co.influence_score = rc.intel.influence_score
        co.confidence_score = rc.intel.confidence_score
        co.confidence_level = rc.intel.confidence_level
        co.recommendation_rank = rc.rank
        co.recommendation_reason = rc.reasons
        contacts.append(co)
    # Phase 3: attach relationship status + the next best action to each contact.
    rel_bundles = reli.bundles_for(session, lead.company_domain)
    for co in contacts:
        b = rel_bundles.get(co.decision_maker_id)
        if b:
            co.relationship_status = b["status"]
            co.next_action = b["action"].action
            co.next_action_reason = b["action"].reason
    contacts.sort(key=lambda c: not c.is_primary)  # primary first (drives the composer default)
    base.primary_contact = next((c for c in contacts if c.is_primary), contacts[0] if contacts else None)
    opps, _ = repo.list_opportunities(session, company_domain=lead.company_domain, limit=5)
    signals = [
        OutreachSignalOut(
            type=(o.opportunity_type or "").lower(),
            label=o.article_title or (o.opportunity_type or "").replace("_", " ").title() or "Signal",
            detail=getattr(o, "summary", "") or "",
            source_url=getattr(o, "article_url", "") or "",
        )
        for o in opps
    ]
    return OutreachLeadDetail(
        **base.model_dump(),
        recommended_pitch=engagement.pitch if engagement else "",
        recommended_offering=engagement.offering if engagement else "",
        contacts=contacts,
        signals=signals,
    )


# ----------------------------------------------------------------- leads: write
def _log(session: Session, *, lead, actor, type: str, detail: str = "") -> None:
    orepo.add_activity(session, lead_id=lead.id, actor_id=getattr(actor, "id", None),
                       actor_email=getattr(actor, "email", ""), type=type, detail=detail)
    orepo.touch_lead(session, lead)


def create_lead(session: Session, payload: OutreachLeadCreate, actor) -> OutreachLeadDetail:
    company = repo.get_company(session, payload.company_domain)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    existing = orepo.get_lead_by_domain(session, payload.company_domain)
    if existing is not None:
        return get_lead_detail(session, existing.id)  # idempotent
    if payload.owner_id is not None and payload.owner_id != getattr(actor, "id", None):
        _require_manager(actor)  # only managers assign to others; members self-own
    engagement = repo.engagement_for(session, payload.company_domain)
    dms = _sorted_contacts(repo.decision_makers_for(session, payload.company_domain))
    lead = orepo.create_lead(
        session,
        company_domain=payload.company_domain,
        owner_id=payload.owner_id,
        primary_dm_id=dms[0].id if dms else None,
        stage="research_complete",
        service_interest=payload.service_interest or _derive_service(company, engagement),
        source="manual",
        qualification_reason=(engagement.business_need if engagement else "") or "",
        qualified_at=_utcnow(),
    )
    _log(session, lead=lead, actor=actor, type="lead_created",
         detail=f"Qualified {company.company_name or payload.company_domain}")
    session.commit()
    return get_lead_detail(session, lead.id)


def patch_lead(session: Session, lead_id: int, payload: OutreachLeadPatch, actor) -> OutreachLeadDetail:
    lead = orepo.get_lead(session, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="outreach lead not found")
    if payload.stage and payload.stage != lead.stage:
        if payload.stage not in OUTREACH_STAGES:
            raise HTTPException(status_code=422, detail="invalid stage")
        old = lead.stage
        lead.stage = payload.stage
        _log(session, lead=lead, actor=actor, type="stage_changed",
             detail=f"{old} → {payload.stage}")
    if payload.owner_id is not None and payload.owner_id != lead.owner_id:
        if payload.owner_id != getattr(actor, "id", None):
            _require_manager(actor)
        lead.owner_id = payload.owner_id
        u = repo.get_user(session, payload.owner_id) if payload.owner_id else None
        _log(session, lead=lead, actor=actor, type="owner_changed",
             detail=f"Assigned to {u.email if u else 'unassigned'}")
    if payload.service_interest is not None:
        lead.service_interest = payload.service_interest
    if payload.primary_dm_id is not None:
        lead.primary_dm_id = payload.primary_dm_id
    if payload.next_action_at is not None:
        lead.next_action_at = payload.next_action_at
    session.commit()
    return get_lead_detail(session, lead.id)


def sync_from_discovery(session: Session, actor, limit: int = 40) -> OutreachSyncResult:
    """Qualify the top-ranked Discovery leads into the outreach pipeline. Idempotent:
    existing leads are left untouched (stage/owner preserved)."""
    _require_manager(actor)
    created = updated = 0
    for score, company in repo.top_leads(session, limit):
        domain = score.company_domain
        existing = orepo.get_lead_by_domain(session, domain)
        if existing is not None:
            updated += 1
            continue
        engagement = repo.engagement_for(session, domain)
        dms = _sorted_contacts(repo.decision_makers_for(session, domain))
        lead = orepo.create_lead(
            session,
            company_domain=domain,
            primary_dm_id=dms[0].id if dms else None,
            stage="research_complete",
            service_interest=_derive_service(company, engagement),
            source="discovery",
            qualification_reason=(engagement.business_need if engagement else "")
            or f"Discovery grade {score.grade} (score {round(score.lead_score or 0)})",
            qualified_at=_utcnow(),
        )
        _log(session, lead=lead, actor=actor, type="lead_created",
             detail=f"Synced from Discovery — grade {score.grade}")
        created += 1
    session.commit()
    return OutreachSyncResult(created=created, updated=updated, total=created + updated)


# ----------------------------------------------------------------- templates
def _parse_vars(*texts: str) -> list[str]:
    seen: list[str] = []
    for t in texts:
        for m in _VAR_RE.findall(t or ""):
            if m not in seen:
                seen.append(m)
    return seen


def _template_out(tpl) -> OutreachTemplateOut:
    out = OutreachTemplateOut.model_validate(tpl)
    out.variables = _parse_vars(tpl.subject, tpl.body)
    return out


def list_templates(session: Session, *, active_only=False) -> list[OutreachTemplateOut]:
    return [_template_out(t) for t in orepo.list_templates(session, active_only=active_only)]


def create_template(session: Session, payload: OutreachTemplateIn, actor) -> OutreachTemplateOut:
    _require_manager(actor)
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="template name required")
    tpl = orepo.create_template(
        session, name=payload.name.strip(), category=payload.category.strip(),
        subject=payload.subject, body=payload.body, is_active=payload.is_active,
        created_by=getattr(actor, "id", None),
    )
    session.commit()
    return _template_out(tpl)


def update_template(session: Session, template_id: int, payload: OutreachTemplateIn, actor) -> OutreachTemplateOut:
    _require_manager(actor)
    tpl = orepo.get_template(session, template_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="template not found")
    tpl.name = payload.name.strip() or tpl.name
    tpl.category = payload.category.strip()
    tpl.subject = payload.subject
    tpl.body = payload.body
    tpl.is_active = payload.is_active
    session.commit()
    return _template_out(tpl)


def delete_template(session: Session, template_id: int, actor) -> None:
    _require_manager(actor)
    tpl = orepo.get_template(session, template_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="template not found")
    orepo.delete_template(session, tpl)
    session.commit()


# ----------------------------------------------------------------- messages
def _render(text: str, ctx: dict[str, str]) -> str:
    # Replace only known {{tokens}}; leave unknown ones intact for the author.
    return _VAR_RE.sub(lambda m: ctx.get(m.group(1), m.group(0)), text or "")


def _message_context(session: Session, lead, dm: DecisionMaker | None, actor) -> dict[str, str]:
    company = repo.get_company(session, lead.company_domain)
    engagement = repo.engagement_for(session, lead.company_domain)
    name = ""
    first = last = title = ""
    if dm:
        first = dm.first_name or ""
        last = dm.last_name or ""
        name = dm.full_name or " ".join(p for p in (first, last) if p)
        title = dm.current_title or dm.headline or ""
    return {
        "first_name": first,
        "last_name": last,
        "full_name": name,
        "title": title,
        "company": company.company_name if company else lead.company_domain,
        "company_domain": lead.company_domain,
        "sender_name": getattr(actor, "full_name", "") or getattr(actor, "email", ""),
        "service": lead.service_interest or "engineering",
        "pitch": engagement.pitch if engagement else "",
        "signal": engagement.business_need if engagement else "",
    }


def _message_out(session: Session, msg, user, dms_map: dict | None = None, users_map: dict | None = None, att_counts_map: dict | None = None) -> OutreachMessageOut:
    out = OutreachMessageOut.model_validate(msg)
    if msg.decision_maker_id:
        if dms_map is not None:
            dm = dms_map.get(msg.decision_maker_id)
        else:
            dm = repo.get_decision_maker(session, msg.decision_maker_id)
        if dm:
            out.recipient_name = (dm.full_name
                                  or " ".join(p for p in (dm.first_name, dm.last_name) if p))
    if msg.created_by:
        if users_map is not None:
            u = users_map.get(msg.created_by)
        else:
            u = repo.get_user(session, msg.created_by)
        out.created_by_email = u.email if u else ""
    if msg.approved_by:
        if users_map is not None:
            u = users_map.get(msg.approved_by)
        else:
            u = repo.get_user(session, msg.approved_by)
        out.approved_by_email = u.email if u else ""
    out.can_approve = _is_manager(user) and msg.status == "pending_approval"
    out.attachment_count = att_counts_map.get(msg.id, 0) if att_counts_map is not None else orepo.count_attachments(session, msg.id)
    return out


def list_messages(session: Session, lead_id: int, user) -> list[OutreachMessageOut]:
    if orepo.get_lead(session, lead_id) is None:
        raise HTTPException(status_code=404, detail="outreach lead not found")
    msgs = orepo.list_messages_for_lead(session, lead_id)
    if not msgs:
        return []
    # Batch-load related entities
    from sqlalchemy import func, select
    from master_db.models import User, DecisionMaker, EmailAttachment
    dm_ids = {m.decision_maker_id for m in msgs if m.decision_maker_id}
    user_ids = {m.created_by for m in msgs if m.created_by} | {m.approved_by for m in msgs if m.approved_by}
    msg_ids = {m.id for m in msgs}
    dms_map = {dm.id: dm for dm in session.scalars(select(DecisionMaker).where(DecisionMaker.id.in_(dm_ids)))} if dm_ids else {}
    users_map = {u.id: u for u in session.scalars(select(User).where(User.id.in_(user_ids)))} if user_ids else {}
    att_counts = session.execute(
        select(EmailAttachment.outreach_message_id, func.count(EmailAttachment.id))
        .where(EmailAttachment.outreach_message_id.in_(msg_ids))
        .group_by(EmailAttachment.outreach_message_id)
    ).all() if msg_ids else []
    att_counts_map = {msg_id: count for msg_id, count in att_counts}
    return [_message_out(session, m, user, dms_map, users_map, att_counts_map) for m in msgs]


def create_message(session: Session, lead_id: int, payload: OutreachMessageCreate, actor) -> OutreachMessageOut:
    lead = orepo.get_lead(session, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="outreach lead not found")
    dm_id = payload.decision_maker_id or lead.primary_dm_id
    dm = repo.get_decision_maker(session, dm_id) if dm_id else None
    subject, body = payload.subject, payload.body
    if payload.template_id:
        tpl = orepo.get_template(session, payload.template_id)
        if tpl is None:
            raise HTTPException(status_code=404, detail="template not found")
        ctx = _message_context(session, lead, dm, actor)
        subject = _render(tpl.subject, ctx)
        body = _render(tpl.body, ctx)
    if not (subject or "").strip() and not (body or "").strip():
        raise HTTPException(status_code=422, detail="provide a template or subject/body")
    msg = orepo.create_message(
        session, outreach_lead_id=lead.id, decision_maker_id=dm_id,
        template_id=payload.template_id, created_by=getattr(actor, "id", None),
        direction="outbound", status="draft",
        to_email=(dm.work_email if dm else "") or "",
        subject=subject or "", body=body or "",
    )
    _log(session, lead=lead, actor=actor, type="draft_created",
         detail=f"Draft: {subject or '(no subject)'}")
    session.commit()
    return _message_out(session, msg, actor)


def _editable(msg) -> bool:
    return msg.status in ("draft", "pending_approval")


def update_message(session: Session, message_id: int, payload: OutreachMessagePatch, actor) -> OutreachMessageOut:
    msg = orepo.get_message(session, message_id)
    if msg is None or msg.direction != "outbound":
        raise HTTPException(status_code=404, detail="message not found")
    if not _editable(msg):
        raise HTTPException(status_code=409, detail=f"cannot edit a {msg.status} message")
    if msg.created_by != getattr(actor, "id", None) and not _is_manager(actor):
        raise HTTPException(status_code=403, detail="only the author or a manager can edit this draft")
    if payload.subject is not None:
        msg.subject = payload.subject
    if payload.body is not None:
        msg.body = payload.body
    if payload.decision_maker_id is not None:
        msg.decision_maker_id = payload.decision_maker_id
        dm = repo.get_decision_maker(session, payload.decision_maker_id)
        msg.to_email = (dm.work_email if dm else "") or ""
    session.commit()
    return _message_out(session, msg, actor)


def submit_for_approval(session: Session, message_id: int, actor) -> OutreachMessageOut:
    msg = orepo.get_message(session, message_id)
    if msg is None or msg.direction != "outbound":
        raise HTTPException(status_code=404, detail="message not found")
    if msg.status != "draft":
        raise HTTPException(status_code=409, detail=f"cannot submit a {msg.status} message")
    if not (msg.to_email or "").strip():
        raise HTTPException(status_code=422, detail="no recipient email on this draft")
    msg.status = "pending_approval"
    lead = orepo.get_lead(session, msg.outreach_lead_id)
    _log(session, lead=lead, actor=actor, type="submitted_for_approval", detail=msg.subject)
    session.commit()
    return _message_out(session, msg, actor)


def approve_message(session: Session, message_id: int, actor) -> OutreachMessageOut:
    _require_manager(actor)
    msg = orepo.get_message(session, message_id)
    if msg is None or msg.direction != "outbound":
        raise HTTPException(status_code=404, detail="message not found")
    if msg.status != "pending_approval":
        raise HTTPException(status_code=409, detail=f"cannot approve a {msg.status} message")
    msg.status = "approved"
    msg.approved_by = getattr(actor, "id", None)
    msg.approved_at = _utcnow()
    lead = orepo.get_lead(session, msg.outreach_lead_id)
    _log(session, lead=lead, actor=actor, type="approved", detail=msg.subject)
    session.commit()
    return _message_out(session, msg, actor)


def send_message(session: Session, message_id: int, actor) -> OutreachMessageOut:
    """Send an approved message — via Gmail if the actor has a connected account, else mock."""
    _require_manager(actor)
    msg = orepo.get_message(session, message_id)
    if msg is None or msg.direction != "outbound":
        raise HTTPException(status_code=404, detail="message not found")
    if msg.status not in ("approved", "queued"):
        raise HTTPException(status_code=409, detail=f"cannot send a {msg.status} message")

    settings = get_settings()
    account = orepo.get_provider_account(session, user_id=getattr(actor, "id", None))

    if account and account.provider_type == "gmail" and account.connection_status == "connected":
        from backend.gmail_oauth import decrypt_tokens
        config = decrypt_tokens(
            account.config_json or "{}", settings.gmail_token_encryption_key or None
        )
        provider = get_provider_for_user("gmail", config)
        from_email = account.email_address or settings.outreach_from_email
        provider_name = "gmail"
    else:
        provider = get_provider(settings.outreach_mail_mode or "mock") or get_provider("mock")
        from_email = settings.outreach_from_email
        provider_name = settings.outreach_mail_mode or "mock"

    # Attach any stored attachments
    atts = []
    for a in orepo.list_attachments(session, message_id):
        if a.content:
            atts.append({"filename": a.filename, "content_type": a.content_type,
                         "content_b64": a.content})

    result = provider.send(
        to_email=msg.to_email, from_email=from_email,
        subject=msg.subject, body=msg.body,
        thread_id=msg.thread_id or "",
        attachments=atts or None,
    )
    lead = orepo.get_lead(session, msg.outreach_lead_id)
    if not result.ok:
        from backend.email_scheduler import EmailScheduler
        EmailScheduler.schedule_failure(msg)
        msg.failed_reason = result.error
        session.commit()
        raise HTTPException(status_code=502, detail=f"send failed: {result.error}")
    msg.status = "sent"
    msg.sent_at = _utcnow()
    msg.from_email = from_email
    msg.thread_id = result.thread_id
    msg.provider = provider_name
    msg.provider_message_id = result.provider_message_id
    msg.folder = "sent"
    _assign_to_conversation(session, msg, lead)
    if lead.stage in ("research_complete", "outreach_ready"):
        lead.stage = "contacted"
    _log(session, lead=lead, actor=actor, type="sent", detail=f"Sent: {msg.subject}")
    session.commit()
    return _message_out(session, msg, actor)


def simulate_reply(session: Session, message_id: int, actor, body: str = "") -> OutreachMessageOut:
    """Demo helper (mock-mail): record an inbound reply to a sent message so the
    Inbox + activity timeline + reply-rate analytics are exercisable end-to-end."""
    msg = orepo.get_message(session, message_id)
    if msg is None or msg.direction != "outbound":
        raise HTTPException(status_code=404, detail="message not found")
    if msg.status not in ("sent", "replied"):
        raise HTTPException(status_code=409, detail="can only reply to a sent message")
    lead = orepo.get_lead(session, msg.outreach_lead_id)
    reply_body = body or "Thanks for reaching out — this is interesting. Can we set up a call next week?"
    reply = orepo.create_message(
        session, outreach_lead_id=lead.id, decision_maker_id=msg.decision_maker_id,
        direction="inbound", status="replied",
        to_email=msg.from_email, from_email=msg.to_email,
        subject=f"Re: {msg.subject}",
        body=reply_body,
        thread_id=msg.thread_id,
        parent_message_id=msg.id,
        folder="inbox",
    )
    _assign_to_conversation(session, reply, lead)
    if lead.stage in ("research_complete", "outreach_ready", "contacted"):
        lead.stage = "replied"
    _log(session, lead=lead, actor=actor, type="reply_received",
         detail=f"Reply from {msg.to_email}")
    session.commit()
    return _message_out(session, reply, actor)


# ----------------------------------------------------------------- approvals + inbox
def list_approvals(session: Session, user) -> list[OutreachMessageOut]:
    rows = orepo.list_messages_by_status(session, "pending_approval")
    return [_message_out(session, m, user) for (m, _lead, _co) in rows]


def list_threads(session: Session, user) -> list[OutreachThreadOut]:
    rows = orepo.list_threaded_messages(session)
    threads: dict[str, OutreachThreadOut] = {}
    for msg, lead, company in rows:
        t = threads.get(msg.thread_id)
        if t is None:
            t = OutreachThreadOut(
                thread_id=msg.thread_id, outreach_lead_id=lead.id,
                company_name=company.company_name if company else lead.company_domain,
                company_domain=lead.company_domain, subject=msg.subject, messages=[],
            )
            threads[msg.thread_id] = t
        t.messages.append(_message_out(session, msg, user))
        t.message_count += 1
        t.last_at = msg.created_at
        if msg.direction == "inbound":
            t.has_reply = True
    # newest thread first
    return sorted(threads.values(), key=lambda x: x.last_at or datetime.min.replace(tzinfo=timezone.utc),
                  reverse=True)


# ----------------------------------------------------------------- activities
def add_note(session: Session, lead_id: int, text: str, actor) -> OutreachActivityOut:
    lead = orepo.get_lead(session, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="outreach lead not found")
    if not text.strip():
        raise HTTPException(status_code=422, detail="note text required")
    _log(session, lead=lead, actor=actor, type="note_added", detail=text.strip())
    session.commit()
    acts = orepo.list_activities(session, lead_id, limit=1)
    return OutreachActivityOut.model_validate(acts[0])


def list_activities(session: Session, lead_id: int) -> list[OutreachActivityOut]:
    if orepo.get_lead(session, lead_id) is None:
        raise HTTPException(status_code=404, detail="outreach lead not found")
    return [OutreachActivityOut.model_validate(a) for a in orepo.list_activities(session, lead_id)]


# ================================================================= tasks
def _task_out(session: Session, task, users_map: dict | None = None, companies_map: dict | None = None, dms_map: dict | None = None) -> OutreachTaskOut:
    out = OutreachTaskOut.model_validate(task)
    now = _utcnow()
    out.is_overdue = (
        task.due_at is not None
        and (_utc(task.due_at) or now) < now
        and task.status in ("pending", "in_progress")
    )
    if task.assigned_to:
        if users_map is not None:
            u = users_map.get(task.assigned_to)
        else:
            u = repo.get_user(session, task.assigned_to)
        out.assigned_to_email = u.email if u else ""
    if task.created_by:
        if users_map is not None:
            u = users_map.get(task.created_by)
        else:
            u = repo.get_user(session, task.created_by)
        out.created_by_email = u.email if u else ""
    if task.company_domain:
        if companies_map is not None:
            co = companies_map.get(task.company_domain)
        else:
            co = repo.get_company(session, task.company_domain)
        out.company_name = co.company_name if co else task.company_domain
    if task.decision_maker_id:
        if dms_map is not None:
            dm = dms_map.get(task.decision_maker_id)
        else:
            dm = repo.get_decision_maker(session, task.decision_maker_id)
        if dm:
            out.decision_maker_name = (
                dm.full_name or " ".join(p for p in (dm.first_name, dm.last_name) if p)
            )
    return out


def list_tasks(
    session: Session, actor,
    *,
    outreach_lead_id: int | None = None,
    company_domain: str | None = None,
    decision_maker_id: int | None = None,
    assigned_to: int | None = None,
    mine: bool = False,
    status: str | None = None,
    overdue_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> Page[OutreachTaskOut]:
    if mine:
        assigned_to = getattr(actor, "id", None)
    offset = (page - 1) * page_size
    rows, total = orepo.list_tasks(
        session,
        outreach_lead_id=outreach_lead_id,
        company_domain=company_domain,
        decision_maker_id=decision_maker_id,
        assigned_to=assigned_to,
        status=status,
        overdue_only=overdue_only,
        limit=page_size,
        offset=offset,
    )
    if not rows:
        return Page.build([], total, page, page_size)
    # Batch-load related entities
    from sqlalchemy import select
    from master_db.models import User, Company, DecisionMaker
    user_ids = {t.assigned_to for t in rows if t.assigned_to} | {t.created_by for t in rows if t.created_by}
    co_domains = {t.company_domain for t in rows if t.company_domain}
    dm_ids = {t.decision_maker_id for t in rows if t.decision_maker_id}
    users_map = {u.id: u for u in session.scalars(select(User).where(User.id.in_(user_ids)))} if user_ids else {}
    companies_map = {co.company_domain: co for co in session.scalars(select(Company).where(Company.company_domain.in_(co_domains)))} if co_domains else {}
    dms_map = {dm.id: dm for dm in session.scalars(select(DecisionMaker).where(DecisionMaker.id.in_(dm_ids)))} if dm_ids else {}
    return Page.build([_task_out(session, t, users_map, companies_map, dms_map) for t in rows], total, page, page_size)


def create_task(session: Session, payload: OutreachTaskIn, actor) -> OutreachTaskOut:
    if not payload.title.strip():
        raise HTTPException(status_code=422, detail="task title required")
    if payload.company_domain and not repo.get_company(session, payload.company_domain):
        raise HTTPException(status_code=404, detail="company not found")
    lead_id = payload.outreach_lead_id
    if lead_id is not None and orepo.get_lead(session, lead_id) is None:
        raise HTTPException(status_code=404, detail="outreach lead not found")
    task = orepo.create_task(
        session,
        title=payload.title.strip(),
        description=payload.description,
        company_domain=payload.company_domain,
        decision_maker_id=payload.decision_maker_id,
        outreach_lead_id=lead_id,
        assigned_to=payload.assigned_to,
        created_by=getattr(actor, "id", None),
        due_at=payload.due_at,
        priority=payload.priority,
        status="pending",
    )
    if lead_id is not None:
        lead = orepo.get_lead(session, lead_id)
        if lead:
            _log(session, lead=lead, actor=actor, type="task_created", detail=payload.title.strip())
    session.commit()
    return _task_out(session, task)


def get_task_detail(session: Session, task_id: int) -> OutreachTaskOut:
    task = orepo.get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return _task_out(session, task)


def patch_task(session: Session, task_id: int, payload: OutreachTaskPatch, actor) -> OutreachTaskOut:
    task = orepo.get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if payload.title is not None:
        if not payload.title.strip():
            raise HTTPException(status_code=422, detail="task title required")
        task.title = payload.title.strip()
    if payload.description is not None:
        task.description = payload.description
    if payload.assigned_to is not None:
        task.assigned_to = payload.assigned_to
    if payload.due_at is not None:
        task.due_at = payload.due_at
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.status is not None:
        task.status = payload.status
        if payload.status == "completed":
            task.completed_by = getattr(actor, "id", None)
            task.completed_at = _utcnow()
            if task.outreach_lead_id:
                lead = orepo.get_lead(session, task.outreach_lead_id)
                if lead:
                    _log(session, lead=lead, actor=actor, type="task_completed", detail=task.title)
            workflow_service.fire_event(
                session, "task_completed", "task", task.id,
                {"owner_id": task.assigned_to, "company_domain": task.company_domain,
                 "priority": task.priority, "title": task.title},
                actor=actor,
            )
        elif task.completed_at and payload.status != "completed":
            task.completed_by = None
            task.completed_at = None
    session.commit()
    return _task_out(session, task)


def delete_task(session: Session, task_id: int, actor) -> None:
    task = orepo.get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if task.created_by != getattr(actor, "id", None) and not _is_manager(actor):
        raise HTTPException(status_code=403, detail="only the creator or a manager can delete this task")
    session.delete(task)
    session.commit()


# ================================================================= meetings
def _meeting_out(session: Session, meeting, companies_map: dict | None = None, dms_map: dict | None = None, users_map: dict | None = None) -> OutreachMeetingOut:
    out = OutreachMeetingOut.model_validate(meeting)
    now = _utcnow()
    out.is_upcoming = (_utc(meeting.scheduled_at) or now) > now
    if meeting.company_domain:
        if companies_map is not None:
            co = companies_map.get(meeting.company_domain)
        else:
            co = repo.get_company(session, meeting.company_domain)
        out.company_name = co.company_name if co else meeting.company_domain
    if meeting.decision_maker_id:
        if dms_map is not None:
            dm = dms_map.get(meeting.decision_maker_id)
        else:
            dm = repo.get_decision_maker(session, meeting.decision_maker_id)
        if dm:
            out.decision_maker_name = (
                dm.full_name or " ".join(p for p in (dm.first_name, dm.last_name) if p)
            )
    if meeting.created_by:
        if users_map is not None:
            u = users_map.get(meeting.created_by)
        else:
            u = repo.get_user(session, meeting.created_by)
        out.created_by_email = u.email if u else ""
    return out


def list_meetings(
    session: Session,
    *,
    outreach_lead_id: int | None = None,
    company_domain: str | None = None,
    decision_maker_id: int | None = None,
    upcoming_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> Page[OutreachMeetingOut]:
    offset = (page - 1) * page_size
    rows, total = orepo.list_meetings(
        session,
        outreach_lead_id=outreach_lead_id,
        company_domain=company_domain,
        decision_maker_id=decision_maker_id,
        upcoming_only=upcoming_only,
        limit=page_size,
        offset=offset,
    )
    if not rows:
        return Page.build([], total, page, page_size)
    # Batch-load related entities
    from sqlalchemy import select
    from master_db.models import Company, DecisionMaker, User
    co_domains = {m.company_domain for m in rows if m.company_domain}
    dm_ids = {m.decision_maker_id for m in rows if m.decision_maker_id}
    user_ids = {m.created_by for m in rows if m.created_by}
    companies_map = {co.company_domain: co for co in session.scalars(select(Company).where(Company.company_domain.in_(co_domains)))} if co_domains else {}
    dms_map = {dm.id: dm for dm in session.scalars(select(DecisionMaker).where(DecisionMaker.id.in_(dm_ids)))} if dm_ids else {}
    users_map = {u.id: u for u in session.scalars(select(User).where(User.id.in_(user_ids)))} if user_ids else {}
    return Page.build([_meeting_out(session, m, companies_map, dms_map, users_map) for m in rows], total, page, page_size)


def create_meeting(session: Session, payload: OutreachMeetingIn, actor) -> OutreachMeetingOut:
    lead_id = payload.outreach_lead_id
    if lead_id is not None and orepo.get_lead(session, lead_id) is None:
        raise HTTPException(status_code=404, detail="outreach lead not found")
    company_domain = payload.company_domain
    if not company_domain and lead_id:
        lead = orepo.get_lead(session, lead_id)
        if lead:
            company_domain = lead.company_domain
    meeting = orepo.create_meeting(
        session,
        outreach_lead_id=lead_id,
        company_domain=company_domain,
        decision_maker_id=payload.decision_maker_id,
        meeting_type=payload.meeting_type,
        title=payload.title,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        participants=payload.participants,
        notes=payload.notes,
        outcome=payload.outcome,
        next_action=payload.next_action,
        created_by=getattr(actor, "id", None),
    )
    if lead_id is not None:
        lead = orepo.get_lead(session, lead_id)
        if lead:
            label = payload.title or payload.meeting_type.replace("_", " ").title()
            _log(session, lead=lead, actor=actor, type="meeting_scheduled", detail=label)
    session.commit()
    return _meeting_out(session, meeting)


def get_meeting_detail(session: Session, meeting_id: int) -> OutreachMeetingOut:
    meeting = orepo.get_meeting(session, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="meeting not found")
    return _meeting_out(session, meeting)


def patch_meeting(session: Session, meeting_id: int, payload: OutreachMeetingPatch, actor) -> OutreachMeetingOut:
    meeting = orepo.get_meeting(session, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="meeting not found")
    if payload.meeting_type is not None:
        meeting.meeting_type = payload.meeting_type
    if payload.title is not None:
        meeting.title = payload.title
    if payload.scheduled_at is not None:
        meeting.scheduled_at = payload.scheduled_at
    if payload.duration_minutes is not None:
        meeting.duration_minutes = payload.duration_minutes
    if payload.participants is not None:
        meeting.participants = payload.participants
    if payload.notes is not None:
        meeting.notes = payload.notes
    if payload.outcome is not None:
        old_outcome = meeting.outcome
        meeting.outcome = payload.outcome
        if payload.outcome and not old_outcome:
            if meeting.outreach_lead_id:
                lead = orepo.get_lead(session, meeting.outreach_lead_id)
                if lead:
                    _log(session, lead=lead, actor=actor, type="meeting_completed",
                         detail=f"Outcome: {payload.outcome}")
            workflow_service.fire_event(
                session, "meeting_completed", "meeting", meeting.id,
                {"company_domain": meeting.company_domain, "outcome": payload.outcome,
                 "title": meeting.title},
                actor=actor,
            )
    if payload.next_action is not None:
        meeting.next_action = payload.next_action
    session.commit()
    return _meeting_out(session, meeting)


def delete_meeting(session: Session, meeting_id: int, actor) -> None:
    meeting = orepo.get_meeting(session, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="meeting not found")
    if meeting.created_by != getattr(actor, "id", None) and not _is_manager(actor):
        raise HTTPException(status_code=403, detail="only the creator or a manager can delete this meeting")
    session.delete(meeting)
    session.commit()


# ================================================================= unified timeline
def _activity_to_event(act) -> UnifiedTimelineEvent:
    label_map = {
        "lead_created": "Lead created",
        "stage_changed": "Stage changed",
        "owner_changed": "Owner changed",
        "draft_created": "Draft created",
        "submitted_for_approval": "Submitted for approval",
        "approved": "Message approved",
        "sent": "Email sent",
        "reply_received": "Reply received",
        "note_added": "Note added",
        "task_created": "Task created",
        "task_completed": "Task completed",
        "meeting_scheduled": "Meeting scheduled",
        "meeting_completed": "Meeting completed",
        "call_logged": "Call logged",
    }
    return UnifiedTimelineEvent(
        event_id=f"activity-{act.id}",
        event_type="activity",
        type=act.type,
        label=label_map.get(act.type, act.type.replace("_", " ").title()),
        detail=act.detail or "",
        actor=act.actor_email or "",
        timestamp=act.created_at,
    )


def _meeting_to_event(meeting) -> UnifiedTimelineEvent:
    mtype = meeting.meeting_type.replace("_", " ").title()
    label = meeting.title or mtype
    detail_parts = []
    if meeting.outcome:
        detail_parts.append(f"Outcome: {meeting.outcome}")
    if meeting.next_action:
        detail_parts.append(f"Next: {meeting.next_action}")
    return UnifiedTimelineEvent(
        event_id=f"meeting-{meeting.id}",
        event_type="meeting",
        type=meeting.meeting_type,
        label=label,
        detail=" · ".join(detail_parts),
        actor="",
        timestamp=meeting.scheduled_at,
    )


def _task_to_event(task) -> UnifiedTimelineEvent:
    status_label = task.status.replace("_", " ").title()
    return UnifiedTimelineEvent(
        event_id=f"task-{task.id}",
        event_type="task",
        type=task.status,
        label=task.title,
        detail=f"Priority: {task.priority} · Status: {status_label}",
        actor="",
        timestamp=task.updated_at or task.created_at,
    )


def get_lead_timeline(session: Session, lead_id: int, limit: int = 50) -> list[UnifiedTimelineEvent]:
    lead = orepo.get_lead(session, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="outreach lead not found")
    activities = orepo.list_activities(session, lead_id, limit=limit)
    meetings, _ = orepo.list_meetings(session, outreach_lead_id=lead_id, limit=limit)
    tasks, _ = orepo.list_tasks(session, outreach_lead_id=lead_id, limit=limit)
    events: list[UnifiedTimelineEvent] = (
        [_activity_to_event(a) for a in activities]
        + [_meeting_to_event(m) for m in meetings]
        + [_task_to_event(t) for t in tasks]
    )
    events.sort(key=lambda e: e.timestamp or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return events[:limit]


# ================================================================= follow-up engine
def _reminder_priority(days_until: int, stage: str) -> str:
    if days_until < 0:
        return "urgent"
    if days_until == 0:
        return "high"
    if stage in ("replied", "interested"):
        return "high" if days_until <= 2 else "medium"
    return "medium" if days_until <= 7 else "low"


def get_follow_ups(session: Session, limit: int = 30) -> list[OutreachFollowUpItem]:
    rows = orepo.upcoming_follow_ups(session, limit=limit)
    now = _utcnow()
    result = []
    for lead, company in rows:
        due = _utc(lead.next_action_at)
        if due is None:
            continue
        delta = due - now
        days_until = int(delta.total_seconds() / 86400)
        is_overdue = due < now
        days_since: int | None = None
        last_act = _utc(lead.last_activity_at)
        if last_act:
            days_since = int((now - last_act).total_seconds() / 86400)
        result.append(OutreachFollowUpItem(
            lead_id=lead.id,
            company_name=company.company_name or lead.company_domain,
            company_domain=lead.company_domain,
            due_at=due,
            days_until=days_until,
            is_overdue=is_overdue,
            days_since_activity=days_since,
            reminder_priority=_reminder_priority(days_until, lead.stage),
            stage=lead.stage,
        ))
    return sorted(result, key=lambda x: (not x.is_overdue, x.days_until))


# ================================================================= dashboard
def get_dashboard(session: Session, actor) -> OutreachDashboardOut:
    tasks_today = orepo.tasks_due_today(session, limit=10)
    overdue = orepo.overdue_tasks(session, limit=10)
    follow_ups = get_follow_ups(session, limit=10)
    upcoming_mtgs = orepo.upcoming_meetings(session, limit=5)
    recent_acts = orepo.recent_activities(session, limit=10)
    open_count = orepo.open_task_count(session)
    mtg_week = orepo.meetings_this_week(session)
    overdue_fu_count = orepo.overdue_follow_up_count(session)
    return OutreachDashboardOut(
        tasks_due_today=[_task_out(session, t) for t in tasks_today],
        overdue_tasks=[_task_out(session, t) for t in overdue],
        upcoming_follow_ups=follow_ups,
        upcoming_meetings=[_meeting_out(session, m) for m in upcoming_mtgs],
        recent_activity=[OutreachActivityOut.model_validate(a) for a, *_ in recent_acts],
        open_tasks=open_count,
        total_meetings_this_week=mtg_week,
        overdue_follow_ups=overdue_fu_count,
    )


# ================================================================= contact history
def get_contact_history(session: Session, dm_id: int) -> ContactHistoryOut:
    dm = repo.get_decision_maker(session, dm_id)
    if dm is None:
        raise HTTPException(status_code=404, detail="decision maker not found")
    full_name = dm.full_name or " ".join(p for p in (dm.first_name, dm.last_name) if p)
    company_name = ""
    if dm.company_domain:
        co = repo.get_company(session, dm.company_domain)
        company_name = co.company_name if co else dm.company_domain

    # Messages with this DM
    from sqlalchemy import select
    from master_db.models import OutreachMessage
    msgs = list(session.scalars(
        select(OutreachMessage).where(OutreachMessage.decision_maker_id == dm_id)
    ))
    emails_sent = sum(1 for m in msgs if m.direction == "outbound" and m.status in ("sent", "replied"))
    emails_recv = sum(1 for m in msgs if m.direction == "inbound")

    # Meetings
    mtgs, _ = orepo.list_meetings(session, decision_maker_id=dm_id, limit=200)
    # Notes (outreach activities with note_added for leads in this dm's company)
    notes_count = 0
    lead = None
    if dm.company_domain:
        lead = orepo.get_lead_by_domain(session, dm.company_domain)
    if lead:
        acts = orepo.list_activities(session, lead.id, limit=200)
        notes_count = sum(1 for a in acts if a.type == "note_added")

    # Tasks
    tasks, _ = orepo.list_tasks(session, decision_maker_id=dm_id, limit=200)

    # Last contacted
    last_sent_at = max((m.sent_at for m in msgs if m.sent_at), default=None)

    # Build timeline
    timeline_events: list[UnifiedTimelineEvent] = []
    for m in msgs:
        ts = m.sent_at or m.created_at
        if ts:
            timeline_events.append(UnifiedTimelineEvent(
                event_id=f"msg-{m.id}",
                event_type="activity",
                type="sent" if m.direction == "outbound" else "reply_received",
                label="Email sent" if m.direction == "outbound" else "Reply received",
                detail=m.subject or "",
                actor=m.from_email or "",
                timestamp=ts,
            ))
    for mtg in mtgs:
        timeline_events.append(_meeting_to_event(mtg))
    for t in tasks:
        timeline_events.append(_task_to_event(t))
    timeline_events.sort(key=lambda e: e.timestamp or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    return ContactHistoryOut(
        decision_maker_id=dm_id,
        full_name=full_name,
        title=dm.current_title or dm.headline or "",
        company_domain=dm.company_domain or "",
        company_name=company_name,
        emails_sent=emails_sent,
        emails_received=emails_recv,
        meetings_count=len(mtgs),
        notes_count=notes_count,
        tasks_count=len(tasks),
        last_contacted_at=last_sent_at,
        timeline=timeline_events[:50],
    )


# ----------------------------------------------------------------- Phase 3: conversation helpers
def _assign_to_conversation(session, msg, lead) -> None:
    """Find or create a conversation for msg, link it, then refresh conversation stats."""
    conv = orepo.get_conversation_by_thread(session, msg.thread_id or "")
    if conv is None:
        conv = orepo.create_conversation(
            session,
            outreach_lead_id=getattr(lead, "id", None),
            company_domain=getattr(lead, "company_domain", None),
            decision_maker_id=msg.decision_maker_id,
            subject=msg.subject,
            thread_id=msg.thread_id or "",
            folder=orepo._derive_folder(msg),
            message_count=1,
            unread_count=1 if (msg.direction == "inbound" and not msg.is_read) else 0,
            last_message_at=msg.created_at or _utcnow(),
        )
    msg.conversation_id = conv.id
    orepo.update_conversation_stats(session, conv.id)


def _conv_out(session, conv, company=None) -> EmailConversationOut:
    co_name = ""
    if company:
        co_name = getattr(company, "company_name", "")
    elif conv.company_domain:
        from backend import repositories as _repo
        co = _repo.get_company(session, conv.company_domain)
        co_name = co.company_name if co else ""
    labels = orepo.get_conversation_labels(session, conv.id)
    msgs = orepo.get_conversation_messages(session, conv.id)
    preview = ""
    if msgs:
        latest = msgs[-1]
        preview = (latest.body or "")[:120]
    return EmailConversationOut(
        id=conv.id,
        outreach_lead_id=conv.outreach_lead_id,
        company_domain=conv.company_domain,
        decision_maker_id=conv.decision_maker_id,
        subject=conv.subject,
        thread_id=conv.thread_id,
        folder=conv.folder,
        message_count=conv.message_count,
        unread_count=conv.unread_count,
        last_message_at=conv.last_message_at,
        is_starred=conv.is_starred,
        is_archived=conv.is_archived,
        is_trashed=conv.is_trashed,
        is_pinned=conv.is_pinned,
        company_name=co_name,
        labels=[EmailLabelOut.model_validate(l) for l in labels],
        preview_text=preview,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


# ----------------------------------------------------------------- Phase 2: draft management
def delete_draft(session: Session, message_id: int, actor) -> None:
    msg = orepo.get_message(session, message_id)
    if msg is None or msg.direction != "outbound":
        raise HTTPException(status_code=404, detail="message not found")
    if msg.status not in ("draft", "pending_approval"):
        raise HTTPException(
            status_code=409, detail=f"cannot delete a {msg.status} message; only drafts can be deleted"
        )
    if msg.created_by != getattr(actor, "id", None) and not _is_manager(actor):
        raise HTTPException(status_code=403, detail="only the author or a manager can delete this draft")
    lead = orepo.get_lead(session, msg.outreach_lead_id)
    session.delete(msg)
    if lead:
        orepo.touch_lead(session, lead)
    session.commit()


def duplicate_draft(session: Session, message_id: int, actor) -> OutreachMessageOut:
    msg = orepo.get_message(session, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="message not found")
    new_subject = f"Copy of {msg.subject}" if msg.subject else ""
    new_msg = orepo.create_message(
        session,
        outreach_lead_id=msg.outreach_lead_id,
        decision_maker_id=msg.decision_maker_id,
        template_id=msg.template_id,
        created_by=getattr(actor, "id", None),
        direction="outbound",
        status="draft",
        to_email=msg.to_email,
        subject=new_subject,
        body=msg.body,
    )
    lead = orepo.get_lead(session, msg.outreach_lead_id)
    _log(session, lead=lead, actor=actor, type="draft_created",
         detail=f"Duplicated draft: {new_subject or '(no subject)'}")
    session.commit()
    return _message_out(session, new_msg, actor)


# ----------------------------------------------------------------- Phase 2: scheduling
def schedule_message(session: Session, message_id: int, payload: MessageScheduleIn,
                     actor) -> OutreachMessageOut:
    _require_manager(actor)
    msg = orepo.get_message(session, message_id)
    if msg is None or msg.direction != "outbound":
        raise HTTPException(status_code=404, detail="message not found")
    if msg.status != "approved":
        raise HTTPException(
            status_code=409,
            detail=f"only an approved message can be scheduled; current status: {msg.status}",
        )
    msg.scheduled_at = payload.scheduled_at
    msg.cancel_at = payload.cancel_at
    msg.status = "scheduled"
    lead = orepo.get_lead(session, msg.outreach_lead_id)
    _log(session, lead=lead, actor=actor, type="message_scheduled",
         detail=f"Scheduled for {payload.scheduled_at.isoformat()}")
    session.commit()
    return _message_out(session, msg, actor)


def cancel_message(session: Session, message_id: int, actor) -> OutreachMessageOut:
    _require_manager(actor)
    msg = orepo.get_message(session, message_id)
    if msg is None or msg.direction != "outbound":
        raise HTTPException(status_code=404, detail="message not found")
    if msg.status not in ("approved", "scheduled", "queued"):
        raise HTTPException(status_code=409, detail=f"cannot cancel a {msg.status} message")
    msg.status = "cancelled"
    msg.retry_at = None
    lead = orepo.get_lead(session, msg.outreach_lead_id)
    _log(session, lead=lead, actor=actor, type="message_cancelled",
         detail=f"Cancelled: {msg.subject or '(no subject)'}")
    session.commit()
    return _message_out(session, msg, actor)


# ----------------------------------------------------------------- Phase 2: attachments
def list_attachments(session: Session, message_id: int, actor) -> list[EmailAttachmentOut]:
    msg = orepo.get_message(session, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="message not found")
    return [EmailAttachmentOut.model_validate(a) for a in orepo.list_attachments(session, message_id)]


def add_attachment(session: Session, message_id: int, payload: EmailAttachmentIn,
                   actor) -> EmailAttachmentOut:
    import base64
    msg = orepo.get_message(session, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="message not found")
    if msg.status not in ("draft", "pending_approval", "approved"):
        raise HTTPException(status_code=409, detail=f"cannot attach to a {msg.status} message")
    try:
        content_bytes = base64.b64decode(payload.content_b64)
    except Exception:
        raise HTTPException(status_code=422, detail="content_b64 must be valid base64")
    att = orepo.create_attachment(
        session,
        outreach_message_id=message_id,
        filename=payload.filename,
        content_type=payload.content_type,
        size_bytes=len(content_bytes),
        status="uploaded",
        content=payload.content_b64,
    )
    session.commit()
    return EmailAttachmentOut.model_validate(att)


def get_attachment(session: Session, message_id: int, attachment_id: int,
                   actor) -> EmailAttachmentOut:
    msg = orepo.get_message(session, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="message not found")
    att = orepo.get_attachment(session, attachment_id)
    if att is None or att.outreach_message_id != message_id:
        raise HTTPException(status_code=404, detail="attachment not found")
    out = EmailAttachmentOut.model_validate(att)
    return out


def remove_attachment(session: Session, message_id: int, attachment_id: int, actor) -> None:
    msg = orepo.get_message(session, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="message not found")
    att = orepo.get_attachment(session, attachment_id)
    if att is None or att.outreach_message_id != message_id:
        raise HTTPException(status_code=404, detail="attachment not found")
    session.delete(att)
    session.commit()


# ----------------------------------------------------------------- Phase 2: provider config
def get_provider_config(session: Session, actor) -> EmailProviderAccountOut:
    cfg = orepo.get_provider_account(session, user_id=getattr(actor, "id", None))
    if cfg is None:
        return EmailProviderAccountOut(provider_type="mock", connection_status="connected")
    return EmailProviderAccountOut.model_validate(cfg)


def set_provider_config(session: Session, payload: EmailProviderAccountIn,
                        actor) -> EmailProviderAccountOut:
    _require_manager(actor)
    from config.enums import EMAIL_PROVIDER_TYPES
    from backend.email_providers.registry import get_provider
    # Validate provider type against the known list before any DB write.
    if payload.provider_type not in EMAIL_PROVIDER_TYPES:
        return EmailProviderAccountOut(
            provider_type=payload.provider_type,
            connection_status="error",
            error_message=f"Unknown provider type: {payload.provider_type!r}",
        )
    cfg = orepo.get_provider_account(session, user_id=getattr(actor, "id", None))
    if cfg is None:
        cfg = orepo.create_provider_account(
            session,
            user_id=getattr(actor, "id", None),
            provider_type=payload.provider_type,
            connection_status="pending",
            config_json=payload.config_json or "{}",
        )
    else:
        cfg.provider_type = payload.provider_type
        if payload.config_json is not None:
            cfg.config_json = payload.config_json
        cfg.connection_status = "pending"
        cfg.error_message = ""
    provider = get_provider(cfg.provider_type)
    if provider:
        try:
            valid = provider.validate_config(cfg.config_json or "{}")
            cfg.connection_status = "connected" if valid else "error"
        except Exception as exc:
            cfg.connection_status = "error"
            cfg.error_message = str(exc)[:500]
    else:
        cfg.connection_status = "error"
        cfg.error_message = f"Unknown provider type: {cfg.provider_type!r}"
    session.commit()
    return EmailProviderAccountOut.model_validate(cfg)


# ----------------------------------------------------------------- Phase 2: scheduler
def run_scheduler_tick(session: Session, actor) -> EmailSchedulerTickOut:
    _require_manager(actor)
    from backend.email_scheduler import EmailScheduler
    counts = EmailScheduler.tick(session)
    session.commit()
    return EmailSchedulerTickOut(
        timestamp=_utcnow(),
        scheduled_to_queued=counts.get("scheduled_to_queued", 0),
        cancelled_by_deadline=counts.get("cancelled_by_deadline", 0),
        gmail_synced=counts.get("gmail_synced", 0),
        gmail_tokens_refreshed=counts.get("gmail_tokens_refreshed", 0),
        sequences_advanced=counts.get("sequences_advanced", 0),
    )


# ----------------------------------------------------------------- Phase 3: conversations
def list_conversations(session: Session, actor, *, folder: str | None = None,
                       outreach_lead_id: int | None = None, company_domain: str | None = None,
                       decision_maker_id: int | None = None, label_id: int | None = None,
                       search: str | None = None, page: int = 1,
                       page_size: int = 50) -> Page:
    rows, total = orepo.list_conversations(
        session,
        folder=folder, outreach_lead_id=outreach_lead_id, company_domain=company_domain,
        decision_maker_id=decision_maker_id, label_id=label_id, search=search,
        limit=page_size, offset=(page - 1) * page_size,
    )
    items = [_conv_out(session, conv, co) for conv, co in rows]
    pages = max(1, -(-total // page_size))
    return Page(items=items, total=total, page=page, page_size=page_size, pages=pages)


def get_conversation(session: Session, conv_id: int, actor) -> EmailConversationOut:
    conv = orepo.get_conversation(session, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return _conv_out(session, conv)


def get_conversation_messages(session: Session, conv_id: int, actor) -> list[OutreachMessageOut]:
    conv = orepo.get_conversation(session, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return [_message_out(session, m, actor) for m in orepo.get_conversation_messages(session, conv_id)]


def get_conversation_timeline(session: Session, conv_id: int, actor) -> list[UnifiedTimelineEvent]:
    conv = orepo.get_conversation(session, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    if conv.outreach_lead_id:
        return get_lead_timeline(session, conv.outreach_lead_id)
    return []


def _set_conv_state(session: Session, conv_id: int, actor, **flags) -> EmailConversationOut:
    conv = orepo.get_conversation(session, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    for k, v in flags.items():
        setattr(conv, k, v)
    session.commit()
    return _conv_out(session, conv)


def archive_conversation(session: Session, conv_id: int, actor) -> EmailConversationOut:
    return _set_conv_state(session, conv_id, actor, is_archived=True, is_trashed=False)


def restore_conversation(session: Session, conv_id: int, actor) -> EmailConversationOut:
    return _set_conv_state(session, conv_id, actor, is_archived=False, is_trashed=False)


def trash_conversation(session: Session, conv_id: int, actor) -> EmailConversationOut:
    return _set_conv_state(session, conv_id, actor, is_trashed=True)


# ----------------------------------------------------------------- Phase 3: message state
def _set_msg_state(session: Session, message_id: int, actor, **flags) -> OutreachMessageOut:
    msg = orepo.get_message(session, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="message not found")
    for k, v in flags.items():
        setattr(msg, k, v)
    # Recompute folder cache
    msg.folder = orepo._derive_folder(msg)
    if msg.conversation_id:
        orepo.update_conversation_stats(session, msg.conversation_id)
    session.commit()
    return _message_out(session, msg, actor)


def mark_read(session: Session, message_id: int, actor) -> OutreachMessageOut:
    return _set_msg_state(session, message_id, actor, is_read=True)


def mark_unread(session: Session, message_id: int, actor) -> OutreachMessageOut:
    return _set_msg_state(session, message_id, actor, is_read=False)


def star_message(session: Session, message_id: int, actor) -> OutreachMessageOut:
    return _set_msg_state(session, message_id, actor, is_starred=True)


def unstar_message(session: Session, message_id: int, actor) -> OutreachMessageOut:
    return _set_msg_state(session, message_id, actor, is_starred=False)


def pin_message(session: Session, message_id: int, actor) -> OutreachMessageOut:
    return _set_msg_state(session, message_id, actor, is_pinned=True)


def unpin_message(session: Session, message_id: int, actor) -> OutreachMessageOut:
    return _set_msg_state(session, message_id, actor, is_pinned=False)


def archive_message(session: Session, message_id: int, actor) -> OutreachMessageOut:
    return _set_msg_state(session, message_id, actor, is_archived=True, is_trashed=False)


def restore_message(session: Session, message_id: int, actor) -> OutreachMessageOut:
    return _set_msg_state(session, message_id, actor, is_archived=False, is_trashed=False)


def trash_message(session: Session, message_id: int, actor) -> OutreachMessageOut:
    return _set_msg_state(session, message_id, actor, is_trashed=True)


# ----------------------------------------------------------------- Phase 3: thread actions
def reply_to_message(session: Session, message_id: int, payload: MessageReplyIn,
                     actor) -> OutreachMessageOut:
    msg = orepo.get_message(session, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="message not found")
    if msg.status not in ("sent", "delivered", "replied"):
        raise HTTPException(status_code=409, detail=f"cannot reply to a {msg.status} message")
    lead = orepo.get_lead(session, msg.outreach_lead_id)
    to_email = payload.to_email or msg.from_email or msg.to_email
    subject = payload.subject or f"Re: {msg.subject}"
    new_msg = orepo.create_message(
        session, outreach_lead_id=msg.outreach_lead_id, decision_maker_id=msg.decision_maker_id,
        direction="outbound", status="draft",
        to_email=to_email, subject=subject,
        body=payload.body, body_html=payload.body_html,
        thread_id=msg.thread_id or "",
        parent_message_id=msg.id,
        folder="drafts",
        created_by=getattr(actor, "id", None),
    )
    _assign_to_conversation(session, new_msg, lead)
    if lead:
        _log(session, lead=lead, actor=actor, type="draft_created",
             detail=f"Reply draft: {subject}")
    session.commit()
    return _message_out(session, new_msg, actor)


def forward_message(session: Session, message_id: int, payload: MessageForwardIn,
                    actor) -> OutreachMessageOut:
    msg = orepo.get_message(session, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="message not found")
    lead = orepo.get_lead(session, msg.outreach_lead_id)
    subject = payload.subject or f"Fwd: {msg.subject}"
    forward_body = payload.body or f"\n\n--- Forwarded message ---\n{msg.body}"
    new_msg = orepo.create_message(
        session, outreach_lead_id=msg.outreach_lead_id, decision_maker_id=None,
        direction="outbound", status="draft",
        to_email=payload.to_email, subject=subject,
        body=forward_body, body_html=payload.body_html,
        folder="drafts",
        created_by=getattr(actor, "id", None),
    )
    if lead:
        _log(session, lead=lead, actor=actor, type="draft_created",
             detail=f"Forward draft: {subject}")
    session.commit()
    return _message_out(session, new_msg, actor)


# ----------------------------------------------------------------- Phase 3: preview
def get_message_preview(session: Session, message_id: int, actor) -> MessagePreviewOut:
    from backend.email_sanitizer import html_to_plain, sanitize_html
    msg = orepo.get_message(session, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="message not found")
    body_html = getattr(msg, "body_html", "") or ""
    body_plain = getattr(msg, "body", "") or ""
    if body_html:
        safe_html = sanitize_html(body_html)
        if not body_plain:
            body_plain = html_to_plain(body_html)
    else:
        safe_html = ""
    atts = [EmailAttachmentOut.model_validate(a)
            for a in orepo.list_attachments(session, message_id)]
    return MessagePreviewOut(
        id=msg.id,
        subject=msg.subject or "",
        body_plain=body_plain,
        body_html_safe=safe_html,
        folder=getattr(msg, "folder", "inbox"),
        conversation_id=getattr(msg, "conversation_id", None),
        attachments=atts,
        is_read=getattr(msg, "is_read", False),
        is_starred=getattr(msg, "is_starred", False),
        is_important=getattr(msg, "is_important", False),
    )


# ----------------------------------------------------------------- Phase 3: search
def search_messages(session: Session, actor, *, q: str | None = None,
                    company_domain: str | None = None, decision_maker_id: int | None = None,
                    status: str | None = None, folder: str | None = None,
                    date_from=None, date_to=None,
                    page: int = 1, page_size: int = 50) -> Page:
    msgs, total = orepo.search_messages(
        session, q=q, company_domain=company_domain, decision_maker_id=decision_maker_id,
        status=status, folder=folder, date_from=date_from, date_to=date_to,
        limit=page_size, offset=(page - 1) * page_size,
    )
    items = [_message_out(session, m, actor) for m in msgs]
    pages = max(1, -(-total // page_size))
    return Page(items=items, total=total, page=page, page_size=page_size, pages=pages)


# ----------------------------------------------------------------- Phase 3: labels
def list_labels(session: Session, actor) -> list[EmailLabelOut]:
    return [EmailLabelOut.model_validate(l) for l in orepo.list_labels(session)]


def create_label(session: Session, payload: EmailLabelIn, actor) -> EmailLabelOut:
    _require_manager(actor)
    existing = orepo.get_label_by_name(session, payload.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"label '{payload.name}' already exists")
    lbl = orepo.create_label(session, name=payload.name, color=payload.color,
                              is_system=False, created_by=getattr(actor, "id", None))
    session.commit()
    return EmailLabelOut.model_validate(lbl)


def delete_label(session: Session, label_id: int, actor) -> None:
    _require_manager(actor)
    lbl = orepo.get_label(session, label_id)
    if lbl is None:
        raise HTTPException(status_code=404, detail="label not found")
    if lbl.is_system:
        raise HTTPException(status_code=409, detail="system labels cannot be deleted")
    session.delete(lbl)
    session.commit()


def apply_label(session: Session, conv_id: int, label_id: int, actor) -> EmailConversationOut:
    conv = orepo.get_conversation(session, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    if orepo.get_label(session, label_id) is None:
        raise HTTPException(status_code=404, detail="label not found")
    orepo.add_label_to_conversation(session, conv_id, label_id)
    session.commit()
    return _conv_out(session, conv)


def remove_label(session: Session, conv_id: int, label_id: int, actor) -> EmailConversationOut:
    conv = orepo.get_conversation(session, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    orepo.remove_label_from_conversation(session, conv_id, label_id)
    session.commit()
    return _conv_out(session, conv)


# ----------------------------------------------------------------- Phase 3: bulk ops
def bulk_message_action(session: Session, payload: BulkMessageIn, actor) -> BulkOperationOut:
    action = payload.action
    ids = payload.message_ids
    if not ids:
        return BulkOperationOut(affected=0, action=action)
    kw: dict = {}
    if action == "archive":
        kw = {"is_archived": True, "is_trashed": False}
    elif action == "restore":
        kw = {"is_archived": False, "is_trashed": False}
    elif action == "trash":
        kw = {"is_trashed": True}
    elif action == "mark_read":
        kw = {"is_read": True}
    elif action == "mark_unread":
        kw = {"is_read": False}
    else:
        raise HTTPException(status_code=422, detail=f"unknown bulk action: {action!r}")
    affected = orepo.bulk_update_messages(session, ids, **kw)
    session.commit()
    return BulkOperationOut(affected=affected, action=action)


def bulk_conversation_action(session: Session, payload: BulkConversationIn,
                             actor) -> BulkOperationOut:
    action = payload.action
    ids = payload.conversation_ids
    if not ids:
        return BulkOperationOut(affected=0, action=action)
    if action == "archive":
        affected = orepo.bulk_update_conversations(session, ids,
                                                   is_archived=True, is_trashed=False)
    elif action == "restore":
        affected = orepo.bulk_update_conversations(session, ids,
                                                   is_archived=False, is_trashed=False)
    elif action == "trash":
        affected = orepo.bulk_update_conversations(session, ids, is_trashed=True)
    elif action == "apply_label":
        if not payload.label_id:
            raise HTTPException(status_code=422, detail="label_id required for apply_label")
        if orepo.get_label(session, payload.label_id) is None:
            raise HTTPException(status_code=404, detail="label not found")
        for cid in ids:
            orepo.add_label_to_conversation(session, cid, payload.label_id)
        affected = len(ids)
    elif action == "remove_label":
        if not payload.label_id:
            raise HTTPException(status_code=422, detail="label_id required for remove_label")
        for cid in ids:
            orepo.remove_label_from_conversation(session, cid, payload.label_id)
        affected = len(ids)
    else:
        raise HTTPException(status_code=422, detail=f"unknown bulk action: {action!r}")
    session.commit()
    return BulkOperationOut(affected=affected, action=action)


# ----------------------------------------------------------------- analytics
def analytics(session: Session) -> OutreachAnalytics:
    stages = orepo.stage_counts(session)
    msgs = orepo.message_status_counts(session)
    total = sum(stages.values())
    won = stages.get("won", 0)
    lost = stages.get("lost", 0)
    open_leads = sum(stages.get(s, 0) for s in OUTREACH_OPEN_STAGES)
    sent = msgs.get("sent", 0)
    replied = msgs.get("replied", 0)
    funnel = [OutreachStageCount(stage=s, count=stages.get(s, 0)) for s in OUTREACH_STAGES]
    return OutreachAnalytics(
        total_leads=total,
        open_leads=open_leads,
        won=won,
        lost=lost,
        funnel=funnel,
        drafts=msgs.get("draft", 0),
        pending_approval=msgs.get("pending_approval", 0),
        sent=sent,
        replied=replied,
        reply_rate=round(replied / sent, 3) if sent else 0.0,
        win_rate=round(won / (won + lost), 3) if (won + lost) else 0.0,
    )


# ================================================================= Phase 4: Gmail OAuth & Sync

def gmail_get_auth_url(session: Session, actor) -> GmailAuthUrlOut:
    """Generate a Gmail OAuth authorization URL for the current user."""
    settings = get_settings()
    if not settings.gmail_client_id:
        raise HTTPException(
            status_code=503,
            detail="Gmail OAuth is not configured (GMAIL_CLIENT_ID missing)",
        )
    from backend.gmail_oauth import generate_state, get_auth_url

    state = generate_state()
    url = get_auth_url(
        client_id=settings.gmail_client_id,
        redirect_uri=settings.gmail_redirect_uri,
        state=state,
    )
    # Persist the state for CSRF verification at callback time
    orepo.upsert_provider_account(
        session,
        user_id=getattr(actor, "id", None),
        provider_type="gmail",
        connection_status="pending",
        oauth_state=state,
    )
    session.commit()
    return GmailAuthUrlOut(auth_url=url, state=state)


def gmail_handle_callback(
    session: Session, actor, *, code: str, state: str
) -> GmailConnectOut:
    """Exchange OAuth code for tokens; store (encrypted) in EmailProviderAccount."""
    settings = get_settings()
    account = orepo.get_provider_account(session, user_id=getattr(actor, "id", None))

    # CSRF state verification
    if account is None or account.oauth_state != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state — please reconnect")

    if not settings.gmail_client_id or not settings.gmail_client_secret:
        raise HTTPException(status_code=503, detail="Gmail credentials not configured")

    from backend.gmail_oauth import (
        encrypt_tokens,
        exchange_code,
        get_gmail_address,
        token_expiry,
    )
    import json as _json

    try:
        tokens = exchange_code(
            code=code,
            redirect_uri=settings.gmail_redirect_uri,
            client_id=settings.gmail_client_id,
            client_secret=settings.gmail_client_secret,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"OAuth code exchange failed: {exc}")

    tokens_json = _json.dumps(tokens)
    config_stored = encrypt_tokens(tokens_json, settings.gmail_token_encryption_key or None)
    email_addr = get_gmail_address(tokens_json)
    expiry = token_expiry(tokens_json)

    account.provider_type = "gmail"
    account.connection_status = "connected"
    account.config_json = config_stored
    account.email_address = email_addr
    account.oauth_state = ""   # consume the state
    account.sync_status = "idle"
    account.sync_error = ""
    account.token_expires_at = expiry
    session.commit()

    return GmailConnectOut(
        id=account.id,
        provider_type="gmail",
        connection_status="connected",
        email_address=email_addr,
        sync_status="idle",
        token_expires_at=expiry,
    )


def gmail_disconnect(session: Session, actor) -> EmailProviderAccountOut:
    """Revoke and delete Gmail OAuth tokens for the current user."""
    account = orepo.get_provider_account(session, user_id=getattr(actor, "id", None))
    if account is None or account.provider_type != "gmail":
        raise HTTPException(status_code=404, detail="No Gmail account connected")
    account.connection_status = "disconnected"
    account.config_json = "{}"
    account.email_address = ""
    account.oauth_state = ""
    account.sync_cursor = None
    account.sync_status = "idle"
    account.sync_error = ""
    account.token_expires_at = None
    session.commit()
    return EmailProviderAccountOut.model_validate(account)


def gmail_status(session: Session, actor) -> EmailProviderAccountOut:
    """Return the current Gmail connection status for the actor."""
    account = orepo.get_provider_account(session, user_id=getattr(actor, "id", None))
    if account is None:
        return EmailProviderAccountOut(provider_type="mock", connection_status="disconnected")
    return EmailProviderAccountOut.model_validate(account)


def gmail_sync(session: Session, actor, *, incremental: bool = True) -> GmailSyncResultOut:
    """Trigger a manual Gmail sync for the current user."""
    account = orepo.get_provider_account(session, user_id=getattr(actor, "id", None))
    if account is None or account.provider_type != "gmail":
        raise HTTPException(status_code=404, detail="No Gmail account connected")
    if account.connection_status != "connected":
        raise HTTPException(
            status_code=409,
            detail=f"Gmail account is {account.connection_status} — reconnect first",
        )
    from backend.gmail_sync import sync_user_gmail

    result = sync_user_gmail(session, account, incremental=incremental)
    session.commit()
    return GmailSyncResultOut(
        ingested=result.get("ingested", 0),
        skipped=result.get("skipped", 0),
        next_cursor=result.get("next_cursor", "") or "",
        error=result.get("error", "") or "",
    )


def gmail_refresh_token(session: Session, actor) -> GmailRefreshOut:
    """Manually refresh the Gmail access token for the current user."""
    settings = get_settings()
    account = orepo.get_provider_account(session, user_id=getattr(actor, "id", None))
    if account is None or account.provider_type != "gmail":
        raise HTTPException(status_code=404, detail="No Gmail account connected")

    from backend.gmail_oauth import (
        decrypt_tokens,
        encrypt_tokens,
        refresh_access_token,
        token_expiry,
    )
    import json as _json

    config = decrypt_tokens(
        account.config_json or "{}", settings.gmail_token_encryption_key or None
    )
    try:
        new_tokens = refresh_access_token(config)
    except Exception as exc:
        account.connection_status = "error"
        account.sync_error = f"Token refresh failed: {exc}"[:500]
        session.commit()
        return GmailRefreshOut(refreshed=False, error=str(exc)[:200])

    tokens_json = _json.dumps(new_tokens)
    account.config_json = encrypt_tokens(tokens_json, settings.gmail_token_encryption_key or None)
    expiry = token_expiry(tokens_json)
    account.token_expires_at = expiry
    account.sync_error = ""
    session.commit()
    return GmailRefreshOut(refreshed=True, token_expires_at=expiry)


# ================================================================= Phase 5: Outreach Intelligence

def get_contact_recommendations(session: Session, company_domain: str) -> list:
    """Get ranked contact recommendations for a company."""
    from backend import outreach_intelligence as oi
    from backend.schemas import ContactRecommendationOut

    recs = oi.recommend_contacts(session, company_domain, limit=3)
    return [ContactRecommendationOut(**rec.__dict__) for rec in recs]


def get_send_time_recommendation(session: Session, company_domain: str, decision_maker_id: int | None = None):
    """Recommend optimal send time for outreach."""
    from backend import outreach_intelligence as oi
    from backend.schemas import SendTimeRecommendationOut

    rec = oi.recommend_send_time(session, company_domain, decision_maker_id)
    return SendTimeRecommendationOut(**rec.__dict__)


def get_subject_recommendations(session: Session, company_domain: str, lead_id: int | None = None) -> list:
    """Recommend email subjects for a company."""
    from backend import outreach_intelligence as oi
    from backend.schemas import SubjectRecommendationOut

    lead = orepo.get_lead(session, lead_id) if lead_id else orepo.get_lead_by_domain(session, company_domain)
    recs = oi.recommend_subject(session, company_domain, lead)
    return [SubjectRecommendationOut(**rec.__dict__) for rec in recs]


def get_template_recommendations(session: Session, company_domain: str, lead_id: int | None = None) -> list:
    """Recommend email templates for a company."""
    from backend import outreach_intelligence as oi
    from backend.schemas import TemplateRecommendationOut

    lead = orepo.get_lead(session, lead_id) if lead_id else orepo.get_lead_by_domain(session, company_domain)
    recs = oi.recommend_template(session, company_domain, lead)
    return [TemplateRecommendationOut(**rec.__dict__) for rec in recs]


def get_success_probability(session: Session, company_domain: str, lead_id: int | None = None):
    """Estimate probability of conversion."""
    from backend import outreach_intelligence as oi
    from backend.schemas import SuccessProbabilityOut

    lead = orepo.get_lead(session, lead_id) if lead_id else orepo.get_lead_by_domain(session, company_domain)
    prob = oi.estimate_success_probability(session, company_domain, lead)
    return SuccessProbabilityOut(**prob.__dict__)


def get_outreach_priority(session: Session, company_domain: str, lead_id: int | None = None):
    """Classify outreach priority."""
    from backend import outreach_intelligence as oi
    from backend.schemas import OutreachPriorityOut

    lead = orepo.get_lead(session, lead_id) if lead_id else orepo.get_lead_by_domain(session, company_domain)
    priority = oi.classify_priority(session, company_domain, lead)
    return OutreachPriorityOut(**priority.__dict__)


def get_outreach_sequence(session: Session, company_domain: str, lead_id: int | None = None) -> list:
    """Get recommended outreach sequence."""
    from backend import outreach_intelligence as oi
    from backend.schemas import SequenceStepOut

    lead = orepo.get_lead(session, lead_id) if lead_id else orepo.get_lead_by_domain(session, company_domain)
    steps = oi.recommend_sequence(session, company_domain, lead)
    return [SequenceStepOut(**step.__dict__) for step in steps]


def get_campaign_intelligence(session: Session, company_domain: str, lead_id: int | None = None):
    """Get all outreach intelligence for a company."""
    from backend import outreach_intelligence as oi
    from backend.schemas import (
        CampaignIntelligenceOut, ContactRecommendationOut, SendTimeRecommendationOut,
        SubjectRecommendationOut, TemplateRecommendationOut, SuccessProbabilityOut,
        OutreachPriorityOut,
    )

    lead = orepo.get_lead(session, lead_id) if lead_id else orepo.get_lead_by_domain(session, company_domain)
    intel = oi.campaign_intelligence(session, company_domain, lead)

    return CampaignIntelligenceOut(
        best_contact=ContactRecommendationOut(**intel.best_contact.__dict__) if intel.best_contact else None,
        best_send_time=SendTimeRecommendationOut(**intel.best_send_time.__dict__) if intel.best_send_time else None,
        best_subjects=[SubjectRecommendationOut(**s.__dict__) for s in intel.best_subjects],
        best_template=TemplateRecommendationOut(**intel.best_template.__dict__) if intel.best_template else None,
        success_probability=SuccessProbabilityOut(**intel.success_probability.__dict__) if intel.success_probability else None,
        outreach_priority=OutreachPriorityOut(**intel.outreach_priority.__dict__) if intel.outreach_priority else None,
    )


def get_user_analytics(session: Session, user_id: int):
    """Get per-user outreach analytics."""
    from backend import outreach_intelligence as oi
    from backend.schemas import OutreachAnalyticsDetailOut

    analytics = oi.user_analytics(session, user_id)
    return OutreachAnalyticsDetailOut(**analytics.__dict__)


def get_company_analytics(session: Session, company_domain: str):
    """Get per-company outreach analytics."""
    from backend import outreach_intelligence as oi
    from backend.schemas import OutreachAnalyticsDetailOut

    analytics = oi.company_analytics(session, company_domain)
    return OutreachAnalyticsDetailOut(**analytics.__dict__)


def get_template_analytics(session: Session, template_id: int):
    """Get per-template outreach analytics."""
    from backend import outreach_intelligence as oi
    from backend.schemas import OutreachAnalyticsDetailOut

    analytics = oi.template_analytics(session, template_id)
    return OutreachAnalyticsDetailOut(**analytics.__dict__)
