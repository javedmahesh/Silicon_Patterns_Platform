"""Company intelligence (Phase 2.5) — deterministic, no LLM.

Assembles a per-company decision-intelligence bundle: buying-committee coverage,
department coverage, contact completeness, an engagement score, contact risk, a
department relationship heatmap, opportunity alignment, and a unified timeline.

Everything is derived from data the platform already owns and reuses the Phase 2
``dm_intelligence`` engine (influence/confidence/department/hierarchy + ranking).
It runs for ONE company per call with a handful of batched queries — no N+1.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import dm_intelligence as dmi
from backend import outreach_repo as orepo
from backend import repositories as repo
from backend.schemas import (
    BuyingCommitteeOut,
    CommitteeRoleOut,
    CompanyIntelligenceOut,
    ContactCompletenessOut,
    ContactRefOut,
    ContactRiskItemOut,
    ContactRiskOut,
    DepartmentCoverageOut,
    DeptCoverageRowOut,
    EngagementScoreOut,
    HeatmapRowOut,
    OppAlignmentOut,
    TimelineEventOut,
)
from config.enums import OUTREACH_STAGES

_VERIFIED_EMAIL = frozenset(("verified", "valid", "safe", "deliverable", "ok"))
_STALE_DAYS = 180


def _pct(n: int, d: int) -> int:
    return round(n / d * 100) if d else 0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _title(rc) -> str:
    return (rc.dm.current_title or rc.dm.headline or "").lower()


def _words(rc) -> set[str]:
    return set(re.findall(r"[a-z&]+", _title(rc)))


def _ref(rc) -> ContactRefOut:
    dm = rc.dm
    name = dm.full_name or " ".join(p for p in (dm.first_name, dm.last_name) if p) or "Decision maker"
    return ContactRefOut(
        decision_maker_id=dm.id, full_name=name,
        title=dm.current_title or dm.headline or "", department=rc.intel.department,
        influence_score=rc.intel.influence_score, confidence_score=rc.intel.confidence_score,
        confidence_level=rc.intel.confidence_level,
    )


# --------------------------------------------------------------------------- #
# 1. Buying committee — role matchers inferred from contact intelligence
# --------------------------------------------------------------------------- #
def _r0(rc) -> int:
    return dmi.exec_rank(rc.dm.current_title or rc.dm.headline or "")


_COMMITTEE: list[tuple[str, object]] = [
    ("CEO", lambda rc: _r0(rc) == 0 and ("ceo" in _words(rc) or "chief executive" in _title(rc) or "founder" in _title(rc))),
    ("CTO", lambda rc: "cto" in _words(rc) or "chief technology" in _title(rc)),
    ("VP Engineering", lambda rc: _r0(rc) <= 3 and rc.intel.department == "Engineering"),
    ("VP Silicon Engineering", lambda rc: _r0(rc) <= 3 and "silicon" in _title(rc)),
    ("Director ASIC", lambda rc: _r0(rc) <= 4 and rc.intel.department == "ASIC"),
    ("Director RTL", lambda rc: _r0(rc) <= 4 and rc.intel.department == "RTL"),
    ("Director Verification", lambda rc: _r0(rc) <= 4 and rc.intel.department == "Verification"),
    ("Director DFT", lambda rc: _r0(rc) <= 4 and rc.intel.department == "DFT"),
    ("Director Physical Design", lambda rc: _r0(rc) <= 4 and rc.intel.department == "Physical Design"),
    ("Recruiting", lambda rc: rc.intel.department_group == "Recruiting" or "recruit" in _title(rc) or "talent" in _title(rc)),
    ("Procurement", lambda rc: rc.intel.department == "Procurement"),
    ("Executive Sponsor", lambda rc: _r0(rc) <= 1),
]


def _buying_committee(ranked: list) -> BuyingCommitteeOut:
    roles: list[CommitteeRoleOut] = []
    present = 0
    for role, match in _COMMITTEE:
        # ranked is influence-sorted, so the first match is the strongest contact.
        hit = next((rc for rc in ranked if match(rc)), None)
        roles.append(CommitteeRoleOut(role=role, present=hit is not None,
                                      contact=_ref(hit) if hit else None))
        present += 1 if hit else 0
    total = len(_COMMITTEE)
    return BuyingCommitteeOut(roles=roles, present=present, total=total,
                              coverage_pct=_pct(present, total))


# --------------------------------------------------------------------------- #
# 2. Department coverage (canonical Phase-2 taxonomy; HR shown as HR/Recruiting)
# --------------------------------------------------------------------------- #
_DEPT_BUCKETS = tuple(d for d in dmi.DEPARTMENTS if d != "Unknown")
_DEPT_LABEL = {"HR": "HR / Recruiting"}


def _department_coverage(ranked: list) -> DepartmentCoverageOut:
    counts = Counter(rc.intel.department for rc in ranked)
    rows = [DeptCoverageRowOut(department=_DEPT_LABEL.get(d, d), count=counts.get(d, 0),
                               present=counts.get(d, 0) > 0)
            for d in _DEPT_BUCKETS]
    present = sum(1 for r in rows if r.present)
    total = len(_DEPT_BUCKETS)
    missing = [r.department for r in rows if not r.present]
    return DepartmentCoverageOut(rows=rows, present=present, total=total,
                                 coverage_pct=_pct(present, total), missing=missing)


# --------------------------------------------------------------------------- #
# 3. Contact completeness
# --------------------------------------------------------------------------- #
def _completeness(ranked: list) -> ContactCompletenessOut:
    n = len(ranked)
    if not n:
        return ContactCompletenessOut()
    ver_email = sum(1 for rc in ranked if (rc.dm.work_email or "").strip()
                    and (rc.dm.email_status or "").lower() in _VERIFIED_EMAIL)
    phone = sum(1 for rc in ranked if (rc.dm.work_phone or "").strip())
    linkedin = sum(1 for rc in ranked if (rc.dm.linkedin_url or "").strip())
    high = sum(1 for rc in ranked if rc.intel.confidence_level == "High")
    no_email = sum(1 for rc in ranked if not (rc.dm.work_email or "").strip())
    return ContactCompletenessOut(
        total_contacts=n,
        verified_email_pct=_pct(ver_email, n),
        phone_pct=_pct(phone, n),
        linkedin_pct=_pct(linkedin, n),
        high_confidence_pct=_pct(high, n),
        avg_influence=round(sum(rc.intel.influence_score for rc in ranked) / n),
        avg_confidence=round(sum(rc.intel.confidence_score for rc in ranked) / n),
        missing_email=no_email,
        missing_phone=n - phone,
        missing_linkedin=n - linkedin,
    )


# --------------------------------------------------------------------------- #
# 4. Engagement score (0–100) — documented weighting
# --------------------------------------------------------------------------- #
ENGAGEMENT_WEIGHTS = {
    "replies": 22, "meetings": 18, "outreach_sent": 18, "pipeline_stage": 16,
    "recent_activity": 10, "notes": 8, "leadership_activity": 8,
}
_MEETING_STAGES = ("meeting_scheduled", "proposal_sent", "won")


def _engagement(lead, msgs, acts, notes_count: int, leadership_total: int) -> EngagementScoreOut:
    factors: list[str] = []
    if lead is None:
        return EngagementScoreOut(score=0, label="Dormant", relationship="Cold",
                                  factors=["No outreach lead yet"])
    sent = sum(1 for m in msgs if m.direction == "outbound" and m.status in ("sent", "replied"))
    replies = sum(1 for m in msgs if m.direction == "inbound")
    pts = 0.0
    if replies:
        pts += min(ENGAGEMENT_WEIGHTS["replies"], replies * 11)
        factors.append(f"{replies} repl{'y' if replies == 1 else 'ies'}")
    if lead.stage in _MEETING_STAGES:
        pts += ENGAGEMENT_WEIGHTS["meetings"]
        factors.append("Meeting / proposal reached")
    elif lead.stage == "interested":
        pts += ENGAGEMENT_WEIGHTS["meetings"] / 2
    if sent:
        pts += min(ENGAGEMENT_WEIGHTS["outreach_sent"], sent * 6)
        factors.append(f"{sent} message(s) sent")
    # pipeline progression
    try:
        idx = OUTREACH_STAGES.index(lead.stage)
    except ValueError:
        idx = 0
    pts += round(idx / (len(OUTREACH_STAGES) - 1) * ENGAGEMENT_WEIGHTS["pipeline_stage"], 2)
    if notes_count:
        pts += min(ENGAGEMENT_WEIGHTS["notes"], notes_count * 2)
        factors.append(f"{notes_count} note(s)")
    if leadership_total:
        pts += min(ENGAGEMENT_WEIGHTS["leadership_activity"], leadership_total * 4)
        factors.append("Leadership activity")
    # recency
    last = lead.last_activity_at
    if last:
        ref = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
        days = (_now() - ref).days
        rec = 10 if days <= 14 else 7 if days <= 30 else 4 if days <= 90 else 2 if days <= 180 else 0
        pts += rec
        if days <= 30:
            factors.append("Recent activity")

    score = max(0, min(100, round(pts)))
    label = "Healthy" if score >= 65 else "Warm" if score >= 35 else "Cold" if score >= 12 else "Dormant"
    # relationship strength ladder (deterministic, from the same signals)
    if lead.stage in ("proposal_sent", "won"):
        rel = "Strategic"
    elif lead.stage in _MEETING_STAGES or (replies and lead.stage == "interested"):
        rel = "Active"
    elif replies:
        rel = "Engaged"
    elif sent or notes_count:
        rel = "Known"
    else:
        rel = "Cold"
    return EngagementScoreOut(score=score, label=label, relationship=rel, factors=factors)


# --------------------------------------------------------------------------- #
# 6. Contact risk
# --------------------------------------------------------------------------- #
def _contact_risk(ranked: list, ldr: list) -> ContactRiskOut:
    no_email = no_phone = no_li = low_conf = stale = 0
    items: list[ContactRiskItemOut] = []
    names = Counter()
    emails = Counter()
    for rc in ranked:
        dm = rc.dm
        nm = (dm.full_name or " ".join(p for p in (dm.first_name, dm.last_name) if p) or "").strip().lower()
        if nm:
            names[nm] += 1
        em = (dm.work_email or "").strip().lower()
        if em:
            emails[em] += 1
    dup_names = {k for k, v in names.items() if v > 1}
    dup_emails = {k for k, v in emails.items() if v > 1}

    for rc in ranked:
        dm = rc.dm
        risks: list[str] = []
        if not (dm.work_email or "").strip():
            risks.append("Missing email"); no_email += 1
        if not (dm.work_phone or "").strip():
            risks.append("Missing phone"); no_phone += 1
        if not (dm.linkedin_url or "").strip():
            risks.append("Missing LinkedIn"); no_li += 1
        if rc.intel.confidence_level == "Low":
            risks.append("Low confidence"); low_conf += 1
        ing = dm.ingested_at
        if ing:
            ref = ing if ing.tzinfo else ing.replace(tzinfo=timezone.utc)
            if (_now() - ref).days > _STALE_DAYS:
                risks.append("Stale profile"); stale += 1
        nm = (dm.full_name or " ".join(p for p in (dm.first_name, dm.last_name) if p) or "").strip().lower()
        em = (dm.work_email or "").strip().lower()
        if nm in dup_names or (em and em in dup_emails):
            risks.append("Possible duplicate")
        if risks:
            name = dm.full_name or " ".join(p for p in (dm.first_name, dm.last_name) if p) or "Decision maker"
            items.append(ContactRiskItemOut(decision_maker_id=dm.id, name=name, risks=risks))

    departures = sum(1 for s in ldr if s.movement_type == "executive_departure")
    dup_count = sum(v - 1 for v in names.values() if v > 1)
    # surface the highest-influence at-risk contacts first, capped
    items.sort(key=lambda it: -len(it.risks))
    return ContactRiskOut(
        missing_email=no_email, missing_phone=no_phone, missing_linkedin=no_li,
        low_confidence=low_conf, stale=stale, duplicates=dup_count,
        leadership_departures=departures, items=items[:12],
    )


# --------------------------------------------------------------------------- #
# 7. Relationship heatmap
# --------------------------------------------------------------------------- #
_HEATMAP_DEPTS = ("Executive", "Engineering", "Verification", "RTL", "DFT", "Sales", "Recruiting")


def _dept_members(by_dept: dict, dept: str) -> list:
    if dept == "Recruiting":
        return by_dept.get("HR", [])
    return by_dept.get(dept, [])


def _heatmap(by_dept: dict, engaged: bool) -> list[HeatmapRowOut]:
    rows: list[HeatmapRowOut] = []
    for dept in _HEATMAP_DEPTS:
        members = _dept_members(by_dept, dept)
        n = len(members)
        if n == 0:
            rows.append(HeatmapRowOut(department=dept, status="Missing", contacts=0,
                                      detail="No contacts"))
            continue
        avg_conf = sum(rc.intel.confidence_score for rc in members) / n
        high = any(rc.intel.confidence_level == "High" for rc in members)
        # quality tier from coverage + contactability, lifted one notch if the
        # company has live outreach engagement (replies).
        if (high and n >= 2) or (avg_conf >= 70 and engaged):
            status = "Strong"
        elif high or avg_conf >= 55 or (n >= 2 and engaged):
            status = "Moderate"
        else:
            status = "Weak"
        rows.append(HeatmapRowOut(department=dept, status=status, contacts=n,
                                  detail=f"{n} contact(s), avg confidence {round(avg_conf)}"))
    return rows


# --------------------------------------------------------------------------- #
# 8. Opportunity alignment
# --------------------------------------------------------------------------- #
_OPP_DEPT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Executive", ("leadership", "executive", "funding", "ipo", "acquisition", "merger", "ceo")),
    ("Business Development", ("partnership", "collaboration", "alliance", "ecosystem")),
    ("AI", ("ai", "machine learning", "ml", "neural", "inference")),
    ("Verification", ("verification", "validation")),
    ("DFT", ("dft", "test")),
    ("Physical Design", ("physical design", "tape out", "tapeout", "signoff")),
    ("ASIC", ("asic", "soc", "chip", "silicon", "vlsi")),
    ("Engineering", ("hiring", "expansion", "product", "technology", "engineering", "r&d", "design")),
)


def _opp_target_dept(opp) -> str:
    text = " ".join((getattr(opp, f, "") or "") for f in
                    ("opportunity_type", "opportunity_category", "article_title",
                     "technology_mentioned")).lower()
    for dept, kws in _OPP_DEPT_RULES:
        if any(k in text for k in kws):
            return dept
    return "Engineering"


def _opportunity_alignment(opps: list, ranked: list, by_dept: dict) -> list[OppAlignmentOut]:
    out: list[OppAlignmentOut] = []
    best_overall = ranked[0] if ranked else None
    for opp in opps:
        dept = _opp_target_dept(opp)
        pool = _dept_members(by_dept, dept) or (by_dept.get("Engineering", []))
        best = pool[0] if pool else best_overall  # pools are influence-sorted
        label = opp.article_title or (opp.opportunity_type or "").replace("_", " ").title() or "Opportunity"
        reason_parts = [f"{(opp.opportunity_type or 'signal').replace('_', ' ')} → {dept}"]
        if best is not None:
            who = best.dm.current_title or best.dm.headline or "top contact"
            reason_parts.append(f"{who} is the highest-influence {best.intel.department} contact "
                                f"(influence {best.intel.influence_score})")
        out.append(OppAlignmentOut(
            opportunity_id=opp.opportunity_id, label=label[:160],
            opportunity_type=opp.opportunity_type or "", best_department=dept,
            contact=_ref(best) if best is not None else None,
            reason="; ".join(reason_parts),
        ))
    return out


# --------------------------------------------------------------------------- #
# 5. Timeline
# --------------------------------------------------------------------------- #
def _parse_dt(s: str | datetime | None) -> datetime | None:
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    if not s:
        return None
    txt = str(s).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%Y"):
        try:
            return datetime.strptime(txt[:len(fmt) + 4], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00"))
    except ValueError:
        return None


def _timeline(company, dms, opps, ldr, demand, notes, lead, acts) -> list[TimelineEventOut]:
    ev: list[tuple[datetime | None, TimelineEventOut]] = []

    def add(at, kind, title, detail=""):
        dt = _parse_dt(at)
        iso = dt.date().isoformat() if dt else (str(at) if at else "")
        ev.append((dt, TimelineEventOut(at=iso, kind=kind, title=title, detail=detail)))

    add(company.discovery_date or company.created_at, "discovery", "Company discovered",
        company.company_name or company.company_domain)
    if dms:
        earliest = min((d.ingested_at for d in dms if d.ingested_at), default=None)
        add(earliest, "decision_makers", f"{len(dms)} decision makers imported")
    if demand is not None and (demand.total_engineering_jobs or 0) > 0:
        add(demand.newest_job_date or demand.ingested_at, "hiring",
            f"Hiring: {demand.total_engineering_jobs} engineering roles",
            demand.primary_focus or "")
    for s in ldr[:10]:
        add(s.effective_date or s.computed_at, "leadership",
            f"{(s.movement_type or '').replace('_', ' ').title()}: {s.to_title or s.person_name}",
            s.summary or "")
    for o in opps[:10]:
        add(o.published_date or o.ingested_at, "opportunity",
            o.article_title or (o.opportunity_type or "Opportunity").replace("_", " ").title(),
            o.opportunity_type or "")
    for a in acts:
        add(a.created_at, f"outreach_{a.type}", a.detail or a.type.replace("_", " ").title(),
            a.actor_email or "")
    for n in notes[:10]:
        add(n.created_at, "note", "Note", (n.body or "")[:160])

    # newest first; undated sink to the bottom
    ev.sort(key=lambda t: (t[0] or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    return [e for _dt, e in ev][:40]


# --------------------------------------------------------------------------- #
# Bundle
# --------------------------------------------------------------------------- #
def company_intelligence(session: Session, domain: str) -> CompanyIntelligenceOut:
    company = repo.get_company(session, domain)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    dms = repo.decision_makers_for(session, domain)
    ctx = dmi.context_for(session, domain)
    ranked = dmi.rank_contacts(dms, ctx)               # influence-sorted, intel attached
    by_dept: dict[str, list] = defaultdict(list)
    for rc in ranked:
        by_dept[rc.intel.department].append(rc)

    opps, _ = repo.list_opportunities(session, company_domain=domain, limit=50)
    ldr = repo.leadership_signals_for(session, domain)
    demand = repo.demand_for(session, domain)
    notes = repo.list_company_notes(session, domain)
    lead = orepo.get_lead_by_domain(session, domain)
    msgs = orepo.list_messages_for_lead(session, lead.id) if lead else []
    acts = orepo.list_activities(session, lead.id) if lead else []
    note_count = len(notes) + sum(1 for a in acts if a.type == "note_added")
    engaged = any(m.direction == "inbound" for m in msgs)

    return CompanyIntelligenceOut(
        company_domain=domain,
        company_name=company.company_name or domain,
        total_contacts=len(dms),
        buying_committee=_buying_committee(ranked),
        department_coverage=_department_coverage(ranked),
        contact_completeness=_completeness(ranked),
        engagement=_engagement(lead, msgs, acts, note_count, len(ldr)),
        contact_risk=_contact_risk(ranked, ldr),
        relationship_heatmap=_heatmap(by_dept, engaged),
        opportunity_alignment=_opportunity_alignment(opps, ranked, by_dept),
        timeline=_timeline(company, dms, opps, ldr, demand, notes, lead, acts),
    )
