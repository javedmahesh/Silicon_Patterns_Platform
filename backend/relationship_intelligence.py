"""Relationship intelligence (Phase 3) — deterministic, no LLM.

Per-contact relationship strength + next-best-contact / next-best-action /
follow-up / risk, company-level opportunity intelligence + a relationship graph,
and cross-company smart alerts. Reuses Phase 2 ``dm_intelligence`` (influence /
confidence / department / ranking) and Phase 2.5 ``company_intelligence`` helpers.
One company per call (or a bounded global scan) with batched queries — no N+1.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import company_intelligence as ci
from backend import dm_intelligence as dmi
from backend import outreach_repo as orepo
from backend import repositories as repo
from backend.schemas import (
    AlertOut,
    CompanyRelationshipsOut,
    ContactRefOut,
    FollowUpOut,
    GraphEdgeOut,
    GraphNodeOut,
    NextActionOut,
    NextBestContactOut,
    OppIntelOut,
    RelationshipGraphOut,
)
from master_db.models import Company, DecisionMaker, LeadershipSignal, Opportunity

_MEETING_STAGES = ("meeting_scheduled", "proposal_sent", "won")
_CLOSED_STAGES = ("proposal_sent", "won")
_CADENCE = {"Cold": 0, "Known": 3, "Engaged": 2, "Active": 5, "Strategic": 7}
_STALE_DAYS = 180
_DEPARTURE = "executive_departure"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _reachable(dm) -> bool:
    return bool((dm.work_email or "").strip())


# --------------------------------------------------------------------------- #
# 1. Relationship strength (per contact)
# --------------------------------------------------------------------------- #
def _relationship(rc, dm_msgs: list, lead, now: datetime):
    sent = sum(1 for m in dm_msgs if m.direction == "outbound" and m.status in ("sent", "replied"))
    replies = sum(1 for m in dm_msgs if m.direction == "inbound")
    freq = len(dm_msgs)
    last = max((_aware(m.sent_at or m.created_at) for m in dm_msgs if (m.sent_at or m.created_at)),
               default=None)
    stage = lead.stage if lead else ""

    pts = 0.0
    pts += min(30, replies * 15)
    if stage in _MEETING_STAGES and (sent or replies):
        pts += 20
    pts += min(20, sent * 7)
    if last:
        d = (now - last).days
        pts += 15 if d <= 14 else 10 if d <= 30 else 5 if d <= 90 else 0
    pts += min(15, freq * 5)
    score = max(0, min(100, round(pts)))

    if stage in _CLOSED_STAGES and (sent or replies):
        status = "Strategic"
    elif (stage in _MEETING_STAGES and (sent or replies)) or (replies and last and (now - last).days <= 30):
        status = "Active"
    elif replies:
        status = "Engaged"
    elif sent or freq:
        status = "Known"
    else:
        status = "Cold"
    return status, score, sent, replies, last


# --------------------------------------------------------------------------- #
# 5. Follow-up engine (per contact)
# --------------------------------------------------------------------------- #
def _follow_up(status: str, last: datetime | None, influence: int, now: datetime) -> FollowUpOut:
    if last is None:
        return FollowUpOut(next_followup_at=now, days_since_last_contact=None, overdue=False,
                           reminder_priority="medium" if influence >= 60 else "low",
                           reason="No outreach yet — send an introduction")
    days = (now - last).days
    cad = _CADENCE.get(status, 3)
    nxt = last + timedelta(days=cad)
    overdue = now > nxt
    pr = "high" if overdue and influence >= 60 else "medium" if (overdue or influence >= 60) else "low"
    if not cad:
        reason = "Reach out now"
    elif overdue:
        reason = f"Overdue by {max(0, days - cad)} day(s)"
    else:
        reason = f"Next follow-up in {max(0, cad - days)} day(s)"
    return FollowUpOut(next_followup_at=nxt, days_since_last_contact=days, overdue=overdue,
                       reminder_priority=pr, reason=reason)


# --------------------------------------------------------------------------- #
# 3. Next best action (per contact)
# --------------------------------------------------------------------------- #
def _next_action(rc, status, sent, replies, follow_up: FollowUpOut, ctx, departed: bool) -> NextActionOut:
    inf = rc.intel.influence_score
    hot = ctx.lead_score >= 70 or ctx.opportunity_score >= 60
    if departed:
        return NextActionOut(action="Contact Alternate Decision Maker",
                             reason="This contact appears to have left or changed roles",
                             priority="high")
    if status == "Cold":
        if _reachable(rc.dm):
            return NextActionOut(action="Send Introduction",
                                 reason=("Reachable high-influence contact, no prior outreach"
                                         if inf >= 55 else "No prior outreach yet"),
                                 priority="high" if inf >= 60 else "medium")
        if ctx.engineering_jobs:
            return NextActionOut(action="Monitor Hiring",
                                 reason="No contact details yet; company is actively hiring",
                                 priority="low")
        return NextActionOut(action="Monitor Leadership",
                             reason="No contact details yet; watch for leadership moves",
                             priority="low")
    if status == "Known" or (sent and not replies):
        return NextActionOut(action="Follow Up",
                             reason=("Sent with no reply and follow-up overdue" if follow_up.overdue
                                     else "Awaiting a reply"),
                             priority="high" if (follow_up.overdue and inf >= 60) else "medium")
    if status == "Engaged":
        return NextActionOut(action="Schedule Meeting",
                             reason="Contact replied — move the conversation to a meeting",
                             priority="high")
    if status in ("Active", "Strategic"):
        if follow_up.overdue:
            return NextActionOut(action="Escalate",
                                 reason="Late-stage and going quiet — escalate to close",
                                 priority="high")
        return NextActionOut(action="Wait", reason="Engaged in late stage; awaiting next step",
                             priority="low")
    if hot and ctx.engineering_jobs:
        return NextActionOut(action="Monitor Hiring", reason="Company hiring momentum", priority="low")
    return NextActionOut(action="Wait", reason="No action needed right now", priority="low")


# --------------------------------------------------------------------------- #
# 2. Next best contact priority
# --------------------------------------------------------------------------- #
def _priority(rc, status, follow_up: FollowUpOut, ctx) -> tuple[str, int, list[str]]:
    inf = rc.intel.influence_score
    conf = rc.intel.confidence_score
    reasons: list[str] = []
    score = inf + 0.3 * conf
    if status in ("Cold", "Known"):
        score += 10
        reasons.append("Untapped relationship")
    if follow_up.overdue:
        score += 15
        reasons.append("Follow-up overdue")
    if ctx.lead_score >= 70 or ctx.opportunity_score >= 60:
        score += 8
        reasons.append("Hot company signals")
    if rc.dm.id in ctx.leadership_dm_ids:
        score += 6
        reasons.append("Recent leadership activity")
    if ctx.engineering_jobs:
        score += 4
    if inf >= 60:
        reasons.append(f"High influence ({inf})")
    if rc.intel.confidence_level == "High":
        reasons.append("Verified contact")
    score = round(score)

    reachable = _reachable(rc.dm)
    if reachable and score >= 85:
        pr = "Contact Now"
    elif reachable and score >= 62:
        pr = "Contact This Week"
    elif score >= 42:
        pr = "Monitor"
    else:
        pr = "Low Priority"
    if not reachable:
        reasons.append("No email on file")
    return pr, score, reasons


# --------------------------------------------------------------------------- #
# 6. Contact risk (per contact, with severity)
# --------------------------------------------------------------------------- #
_RISK_SEVERITY = {  # flag -> severity rank
    "Left company": 3, "Missing email": 3, "Low confidence": 2, "Stale profile": 2,
    "Inactive relationship": 2, "Missing phone": 1, "Missing LinkedIn": 1, "Possible duplicate": 1,
}


def _risk(rc, departed: bool, status: str, last: datetime | None, dup: bool, now: datetime):
    dm = rc.dm
    flags: list[str] = []
    if departed:
        flags.append("Left company")
    if not _reachable(dm):
        flags.append("Missing email")
    if not (dm.work_phone or "").strip():
        flags.append("Missing phone")
    if not (dm.linkedin_url or "").strip():
        flags.append("Missing LinkedIn")
    if rc.intel.confidence_level == "Low":
        flags.append("Low confidence")
    if dm.ingested_at and (now - _aware(dm.ingested_at)).days > _STALE_DAYS:
        flags.append("Stale profile")
    if dup:
        flags.append("Possible duplicate")
    if status in ("Known", "Engaged") and last and (now - last).days > 30:
        flags.append("Inactive relationship")
    rank = max((_RISK_SEVERITY.get(f, 1) for f in flags), default=0)
    sev = {3: "high", 2: "medium", 1: "low", 0: ""}[rank]
    return sev, flags


# --------------------------------------------------------------------------- #
# Per-contact bundle
# --------------------------------------------------------------------------- #
def _contact_bundle(rc, dm_msgs, lead, ctx, departed, dup, now):
    status, score, sent, replies, last = _relationship(rc, dm_msgs, lead, now)
    follow_up = _follow_up(status, last, rc.intel.influence_score, now)
    action = _next_action(rc, status, sent, replies, follow_up, ctx, departed)
    priority, pscore, reasons = _priority(rc, status, follow_up, ctx)
    sev, flags = _risk(rc, departed, status, last, dup, now)
    return {
        "status": status, "score": score, "follow_up": follow_up, "action": action,
        "priority": priority, "pscore": pscore, "reasons": reasons,
        "risk_severity": sev, "risk_flags": flags,
    }


def contact_relationship(session: Session, dm: DecisionMaker) -> dict:
    """Relationship bundle for ONE decision maker (used by the DM detail endpoint)."""
    ctx = dmi.context_for(session, dm.company_domain)
    rc = dmi.rank_contacts([dm], ctx)[0]
    lead = orepo.get_lead_by_domain(session, dm.company_domain) if dm.company_domain else None
    msgs = [m for m in (orepo.list_messages_for_lead(session, lead.id) if lead else [])
            if m.decision_maker_id == dm.id]
    departed = any(s.movement_type == _DEPARTURE for s in repo.leadership_for_dm(session, dm.id))
    return _contact_bundle(rc, msgs, lead, ctx, departed, False, _now())


def bundles_for(session: Session, domain: str) -> dict[int, dict]:
    """Per-contact relationship bundles keyed by decision_maker id (for Outreach).
    One pass over the company's contacts + a single outreach-messages load."""
    dms = repo.decision_makers_for(session, domain)
    if not dms:
        return {}
    ctx = dmi.context_for(session, domain)
    ranked = dmi.rank_contacts(dms, ctx)
    lead = orepo.get_lead_by_domain(session, domain)
    msgs = orepo.list_messages_for_lead(session, lead.id) if lead else []
    ldr = repo.leadership_signals_for(session, domain)
    msgs_by_dm: dict[int, list] = defaultdict(list)
    for m in msgs:
        if m.decision_maker_id:
            msgs_by_dm[m.decision_maker_id].append(m)
    departed_ids = {s.decision_maker_id for s in ldr if s.movement_type == _DEPARTURE and s.decision_maker_id}
    now = _now()
    return {rc.dm.id: _contact_bundle(rc, msgs_by_dm.get(rc.dm.id, []), lead, ctx,
                                      rc.dm.id in departed_ids, False, now)
            for rc in ranked}


def _ref(rc) -> ContactRefOut:
    dm = rc.dm
    name = dm.full_name or " ".join(p for p in (dm.first_name, dm.last_name) if p) or "Decision maker"
    return ContactRefOut(decision_maker_id=dm.id, full_name=name,
                         title=dm.current_title or dm.headline or "", department=rc.intel.department,
                         influence_score=rc.intel.influence_score, confidence_score=rc.intel.confidence_score,
                         confidence_level=rc.intel.confidence_level)


# --------------------------------------------------------------------------- #
# Company relationships bundle (next best contacts, opp intel, alerts, graph)
# --------------------------------------------------------------------------- #
def company_relationships(session: Session, domain: str) -> CompanyRelationshipsOut:
    company = repo.get_company(session, domain)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    now = _now()
    dms = repo.decision_makers_for(session, domain)
    ctx = dmi.context_for(session, domain)
    ranked = dmi.rank_contacts(dms, ctx)
    lead = orepo.get_lead_by_domain(session, domain)
    msgs = orepo.list_messages_for_lead(session, lead.id) if lead else []
    ldr = repo.leadership_signals_for(session, domain)
    opps, _ = repo.list_opportunities(session, company_domain=domain, limit=50)
    demand = repo.demand_for(session, domain)

    msgs_by_dm: dict[int, list] = defaultdict(list)
    for m in msgs:
        if m.decision_maker_id:
            msgs_by_dm[m.decision_maker_id].append(m)
    departed_ids = {s.decision_maker_id for s in ldr if s.movement_type == _DEPARTURE and s.decision_maker_id}
    # duplicate detection (name/email)
    seen_name: dict[str, int] = defaultdict(int)
    seen_email: dict[str, int] = defaultdict(int)
    for rc in ranked:
        nm = (rc.dm.full_name or " ".join(p for p in (rc.dm.first_name, rc.dm.last_name) if p) or "").strip().lower()
        em = (rc.dm.work_email or "").strip().lower()
        if nm:
            seen_name[nm] += 1
        if em:
            seen_email[em] += 1

    by_dept: dict[str, list] = defaultdict(list)
    bundles: dict[int, dict] = {}
    nbc: list[NextBestContactOut] = []
    for rc in ranked:
        by_dept[rc.intel.department].append(rc)
        nm = (rc.dm.full_name or " ".join(p for p in (rc.dm.first_name, rc.dm.last_name) if p) or "").strip().lower()
        em = (rc.dm.work_email or "").strip().lower()
        dup = seen_name.get(nm, 0) > 1 or (bool(em) and seen_email.get(em, 0) > 1)
        b = _contact_bundle(rc, msgs_by_dm.get(rc.dm.id, []), lead, ctx, rc.dm.id in departed_ids, dup, now)
        bundles[rc.dm.id] = b
        nbc.append(NextBestContactOut(
            contact=_ref(rc), priority=b["priority"], score=b["pscore"], reasons=b["reasons"],
            relationship_status=b["status"], relationship_score=b["score"],
            next_action=b["action"], follow_up=b["follow_up"], risk_severity=b["risk_severity"],
            risk_flags=b["risk_flags"],
        ))

    nbc.sort(key=lambda x: -x.score)
    _ORDER = {"Contact Now": 0, "Contact This Week": 1, "Monitor": 2, "Low Priority": 3}
    follow_ups = sorted([c for c in nbc if c.follow_up and c.follow_up.overdue],
                        key=lambda x: (_ORDER.get(x.priority, 9), -x.score))

    opp_intel = _opportunity_intelligence(opps, ranked, by_dept, bundles)
    alerts = _company_alerts(company, ranked, ldr, opps, demand, lead, msgs_by_dm, bundles, now)
    graph = _graph(company, ranked, by_dept, ldr, opps, msgs_by_dm, lead)

    return CompanyRelationshipsOut(
        company_domain=domain, company_name=company.company_name or domain,
        next_best_contacts=nbc[:15], follow_ups=follow_ups[:10],
        opportunity_intelligence=opp_intel, alerts=alerts, graph=graph,
    )


# --------------------------------------------------------------------------- #
# 7. Opportunity intelligence
# --------------------------------------------------------------------------- #
def _opportunity_intelligence(opps, ranked, by_dept, bundles) -> list[OppIntelOut]:
    out: list[OppIntelOut] = []
    fallback = by_dept.get("Engineering", []) or ranked
    for opp in opps:
        dept = ci._opp_target_dept(opp)
        pool = by_dept.get(dept) or fallback
        best = pool[0] if pool else None
        backups = [_ref(rc) for rc in pool[1:3]] if pool else []
        b = bundles.get(best.dm.id) if best else None
        label = opp.article_title or (opp.opportunity_type or "Opportunity").replace("_", " ").title()
        reason = f"{(opp.opportunity_type or 'signal').replace('_', ' ')} → {dept}"
        if best:
            reason += (f"; {best.dm.current_title or 'top contact'} "
                       f"(influence {best.intel.influence_score}, {b['status'] if b else 'Cold'})")
        out.append(OppIntelOut(
            opportunity_id=opp.opportunity_id, label=label[:160],
            opportunity_type=opp.opportunity_type or "", best_department=dept,
            best=_ref(best) if best else None, backups=backups,
            relationship_status=(b["status"] if b else ""),
            suggested_action=(b["action"] if b else None), reason=reason,
        ))
    return out


# --------------------------------------------------------------------------- #
# 4. Smart alerts (company-scoped)
# --------------------------------------------------------------------------- #
_MOVE_ALERT = {
    "new_executive_hire": ("executive_joined", "high", "Executive joined"),
    "executive_departure": ("executive_departed", "high", "Executive departed"),
    "promotion": ("promotion", "medium", "Promotion"),
    "role_change": ("leadership_change", "medium", "Leadership change"),
    "executive_reshuffle": ("leadership_change", "medium", "Leadership change"),
    "board_appointment": ("leadership_change", "medium", "Board appointment"),
    "founder_change": ("leadership_change", "high", "Founder change"),
}


def _company_alerts(company, ranked, ldr, opps, demand, lead, msgs_by_dm, bundles, now) -> list[AlertOut]:
    name = company.company_name or company.company_domain
    out: list[AlertOut] = []

    def mk(t, sev, title, detail, at="", dm_id=None):
        out.append(AlertOut(type=t, severity=sev, company_domain=company.company_domain,
                            company_name=name, title=title, detail=detail, at=str(at or ""),
                            decision_maker_id=dm_id))

    for s in ldr[:8]:
        t, sev, title = _MOVE_ALERT.get(s.movement_type, ("leadership_change", "medium", "Leadership change"))
        mk(t, sev, f"{title}: {s.to_title or s.person_name}", s.summary or "",
           s.effective_date or s.computed_at, s.decision_maker_id)
    if demand is not None and ((demand.hiring_trend or "").lower() == "up" or (demand.total_engineering_jobs or 0) >= 10):
        mk("hiring_spike", "medium", f"Hiring spike: {demand.total_engineering_jobs} engineering roles",
           demand.primary_focus or "", demand.newest_job_date or demand.ingested_at)
    for o in opps[:5]:
        mk("new_opportunity", "info",
           o.article_title or (o.opportunity_type or "Opportunity").replace("_", " ").title(),
           o.opportunity_type or "", o.published_date or o.ingested_at)
    # relationship becoming stale
    for rc in ranked:
        b = bundles.get(rc.dm.id)
        if b and b["status"] in ("Engaged", "Active") and b["follow_up"] and b["follow_up"].overdue:
            nm = rc.dm.full_name or " ".join(p for p in (rc.dm.first_name, rc.dm.last_name) if p)
            mk("relationship_stale", "medium", f"Relationship going stale: {nm}",
               b["follow_up"].reason, "", rc.dm.id)
    # buying committee completed
    if ci._buying_committee(ranked).coverage_pct == 100:
        mk("buying_committee_complete", "info", "Buying committee complete",
           "All committee roles have a mapped contact")
    # high-value contact added (recent + high influence)
    for rc in ranked[:10]:
        if rc.intel.influence_score >= 70 and rc.dm.ingested_at and (now - _aware(rc.dm.ingested_at)).days <= 30:
            nm = rc.dm.full_name or " ".join(p for p in (rc.dm.first_name, rc.dm.last_name) if p)
            mk("high_value_contact_added", "info", f"High-value contact added: {nm}",
               f"{rc.dm.current_title or ''} · influence {rc.intel.influence_score}", rc.dm.ingested_at, rc.dm.id)
    return out[:25]


# --------------------------------------------------------------------------- #
# 8. Relationship graph (bounded, deterministic)
# --------------------------------------------------------------------------- #
def _graph(company, ranked, by_dept, ldr, opps, msgs_by_dm, lead) -> RelationshipGraphOut:
    nodes: list[GraphNodeOut] = []
    edges: list[GraphEdgeOut] = []
    cid = f"co:{company.company_domain}"
    nodes.append(GraphNodeOut(id=cid, kind="company", label=company.company_name or company.company_domain))

    committee_ids = {r.contact.decision_maker_id for r in ci._buying_committee(ranked).roles
                     if r.present and r.contact}
    top = ranked[:20]
    depts = {rc.intel.department for rc in top}
    for dept in sorted(depts):
        did = f"dept:{dept}"
        nodes.append(GraphNodeOut(id=did, kind="department", label=dept))
        edges.append(GraphEdgeOut(source=cid, target=did, kind="department"))

    if lead is not None:
        oid = "outreach"
        nodes.append(GraphNodeOut(id=oid, kind="outreach", label="Outreach", detail=lead.stage))
        edges.append(GraphEdgeOut(source=cid, target=oid, kind="outreach"))

    # department leads for hierarchy edges (highest exec_rank per dept)
    dept_lead: dict[str, object] = {}
    for dept, members in by_dept.items():
        dept_lead[dept] = min(members, key=lambda rc: (rc.intel.hierarchy_rank, -rc.intel.influence_score))

    for rc in top:
        nid = f"dm:{rc.dm.id}"
        nm = rc.dm.full_name or " ".join(p for p in (rc.dm.first_name, rc.dm.last_name) if p) or "Decision maker"
        nodes.append(GraphNodeOut(id=nid, kind="contact", label=nm,
                                  detail=rc.dm.current_title or "", dm_id=rc.dm.id,
                                  score=rc.intel.influence_score))
        edges.append(GraphEdgeOut(source=f"dept:{rc.intel.department}", target=nid, kind="department"))
        if rc.dm.id in committee_ids:
            edges.append(GraphEdgeOut(source=cid, target=nid, kind="committee"))
        lead_rc = dept_lead.get(rc.intel.department)
        if lead_rc is not None and lead_rc.dm.id != rc.dm.id:
            edges.append(GraphEdgeOut(source=f"dm:{lead_rc.dm.id}", target=nid, kind="hierarchy"))
        if lead is not None and rc.dm.id in msgs_by_dm:
            edges.append(GraphEdgeOut(source="outreach", target=nid, kind="outreach"))

    for s in ldr[:5]:
        lid = f"ldr:{s.signal_id}"
        nodes.append(GraphNodeOut(id=lid, kind="leadership",
                                  label=(s.movement_type or "").replace("_", " ").title(),
                                  detail=s.to_title or s.person_name))
        if s.decision_maker_id and f"dm:{s.decision_maker_id}" in {n.id for n in nodes}:
            edges.append(GraphEdgeOut(source=f"dm:{s.decision_maker_id}", target=lid, kind="leadership"))
        else:
            edges.append(GraphEdgeOut(source=cid, target=lid, kind="leadership"))

    for o in opps[:5]:
        opid = f"opp:{o.opportunity_id}"
        dept = ci._opp_target_dept(o)
        nodes.append(GraphNodeOut(id=opid, kind="opportunity",
                                  label=(o.article_title or o.opportunity_type or "Opportunity")[:48],
                                  detail=o.opportunity_type or ""))
        target = f"dept:{dept}" if dept in depts else cid
        edges.append(GraphEdgeOut(source=opid, target=target, kind="alignment"))

    return RelationshipGraphOut(nodes=nodes, edges=edges)


# --------------------------------------------------------------------------- #
# Global smart alerts (Dashboard) — bounded cross-company scan
# --------------------------------------------------------------------------- #
def smart_alerts(session: Session, limit: int = 25) -> list[AlertOut]:
    out: list[AlertOut] = []
    names = {c.company_domain: c.company_name for c in session.scalars(select(Company))}

    sigs = list(session.scalars(
        select(LeadershipSignal).order_by(LeadershipSignal.computed_at.desc()).limit(40)))
    for s in sigs:
        t, sev, title = _MOVE_ALERT.get(s.movement_type, ("leadership_change", "medium", "Leadership change"))
        out.append(AlertOut(type=t, severity=sev, company_domain=s.company_domain or "",
                            company_name=names.get(s.company_domain, s.company_name or ""),
                            title=f"{title}: {s.to_title or s.person_name}", detail=s.summary or "",
                            at=str(s.effective_date or s.computed_at or ""),
                            decision_maker_id=s.decision_maker_id))

    opps = list(session.scalars(
        select(Opportunity).order_by(Opportunity.ingested_at.desc()).limit(25)))
    for o in opps:
        out.append(AlertOut(type="new_opportunity", severity="info", company_domain=o.company_domain,
                            company_name=names.get(o.company_domain, o.company_name or ""),
                            title=o.article_title or (o.opportunity_type or "Opportunity").replace("_", " ").title(),
                            detail=o.opportunity_type or "", at=str(o.published_date or o.ingested_at or "")))

    # high-value contacts added recently — batch contexts to avoid N+1
    recent_dms = list(session.scalars(
        select(DecisionMaker).order_by(DecisionMaker.ingested_at.desc()).limit(60)))
    ctxs = dmi.build_company_contexts(session, [d.company_domain for d in recent_dms])
    now = _now()
    for d in recent_dms:
        ctx = ctxs.get(d.company_domain) or dmi.CompanyContext(domain=d.company_domain or "")
        intel = dmi.compute(d, ctx)
        if intel.influence_score >= 75 and d.ingested_at and (now - _aware(d.ingested_at)).days <= 30:
            nm = d.full_name or " ".join(p for p in (d.first_name, d.last_name) if p)
            out.append(AlertOut(type="high_value_contact_added", severity="info",
                                company_domain=d.company_domain or "",
                                company_name=names.get(d.company_domain, d.resolved_company_name or ""),
                                title=f"High-value contact added: {nm}",
                                detail=f"{d.current_title or ''} · influence {intel.influence_score}",
                                at=str(d.ingested_at or ""), decision_maker_id=d.id))

    sev_rank = {"high": 0, "medium": 1, "info": 2}
    out.sort(key=lambda a: (sev_rank.get(a.severity, 3), a.at), reverse=False)
    return out[:limit]
