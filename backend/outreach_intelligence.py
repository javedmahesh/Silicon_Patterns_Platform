"""Phase 5: Outreach Intelligence — 12 deterministic recommendation engines.

Extends Phase 2/2.5/3 intelligence (dm_intelligence, company_intelligence, relationship_intelligence)
with outreach-specific scoring: best contacts, send times, subjects, templates, success probability,
priority, sequences, and analytics. No LLM. All recommendations explainable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import dm_intelligence as dmi
from backend import repositories as repo
from backend import outreach_repo as orepo
from master_db.models import LeadershipSignal, OutreachLead, OutreachMessage

from backend.timeutil import utcnow as _utcnow


# ========================================================================
# 1. Best Contact Recommendation
# ========================================================================
@dataclass
class ContactRecommendation:
    decision_maker_id: int
    full_name: str
    title: str
    email: str
    influence_score: int
    confidence_score: int
    confidence_level: str
    relationship_strength: int  # 0–100
    company_engagement: str  # "Strong" | "Moderate" | "Weak"
    recommendation_reason: list[str] = field(default_factory=list)


def recommend_contacts(session: Session, company_domain: str, limit: int = 3) -> list[ContactRecommendation]:
    """Rank contacts by influence + confidence + relationship + company engagement."""
    dms = repo.decision_makers_for(session, company_domain)
    if not dms:
        return []

    ctx = dmi.context_for(session, company_domain)
    lead = orepo.get_lead_by_domain(session, company_domain)
    now = _utcnow()

    # All messages for this company's contacts in one query — this used to be one
    # query per decision maker, so a company with 40 contacts issued 40 round trips.
    contactable = [dm for dm in dms if (dm.work_email or "").strip()]
    msgs_by_dm: dict[int, list[OutreachMessage]] = {}
    if contactable:
        for m in session.scalars(select(OutreachMessage).where(
            OutreachMessage.decision_maker_id.in_([dm.id for dm in contactable])
        )):
            msgs_by_dm.setdefault(m.decision_maker_id, []).append(m)

    scored = []
    for dm in contactable:
        intel = dmi.compute(dm, ctx)
        msgs = msgs_by_dm.get(dm.id, [])

        # Relationship strength
        rel_pts = 0.0
        rel_factors = []
        replies = sum(1 for m in msgs if m.direction == "inbound")
        rel_pts += min(30, replies * 15)
        if replies:
            rel_factors.append(f"{replies} reply/replies received")

        if lead and lead.stage in ("meeting_scheduled", "proposal_sent", "won"):
            rel_pts += 20
            rel_factors.append("In advanced pipeline stage")

        sent = sum(1 for m in msgs if m.direction == "outbound" and m.status in ("sent", "replied"))
        rel_pts += min(20, sent * 7)
        if sent:
            rel_factors.append(f"{sent} outbound message(s)")

        last = max(
            (_utc(m.sent_at or m.created_at) for m in msgs if (m.sent_at or m.created_at)),
            default=None
        )
        if last:
            d = (now - last).days
            rel_pts += 15 if d <= 14 else 10 if d <= 30 else 5 if d <= 90 else 0
            if d <= 14:
                rel_factors.append("Recent contact")

        rel_score = max(0, min(100, round(rel_pts)))

        # Company engagement
        co_eng = "Weak"
        if ctx.lead_score >= 75:
            co_eng = "Strong"
        elif ctx.lead_score >= 50:
            co_eng = "Moderate"

        # Overall ranking score
        rank_score = (intel.influence_score * 0.4 + intel.confidence_score * 0.25 +
                      rel_score * 0.25 + (1.0 if co_eng == "Strong" else 0.5 if co_eng == "Moderate" else 0.0) * 10)

        reasons = intel.influence_factors + intel.confidence_factors + rel_factors

        scored.append((
            rank_score,
            ContactRecommendation(
                decision_maker_id=dm.id,
                full_name=dm.full_name or f"{dm.first_name or ''} {dm.last_name or ''}".strip(),
                title=dm.current_title or dm.headline or "",
                email=dm.work_email or "",
                influence_score=intel.influence_score,
                confidence_score=intel.confidence_score,
                confidence_level=intel.confidence_level,
                relationship_strength=rel_score,
                company_engagement=co_eng,
                recommendation_reason=reasons[:5],
            )
        ))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [rec for _, rec in scored[:limit]]


# ========================================================================
# 2. Best Send Time Recommendation
# ========================================================================
@dataclass
class SendTimeRecommendation:
    recommended_time: datetime
    timezone_offset: str
    factors: list[str] = field(default_factory=list)
    rationale: str = ""


def recommend_send_time(session: Session, company_domain: str, decision_maker_id: int | None = None) -> SendTimeRecommendation:
    """Recommend send time based on timezone, company location, business hours, reply history."""
    dm = None
    if decision_maker_id:
        dm = repo.get_decision_maker(session, decision_maker_id)

    co = repo.get_company(session, company_domain)
    now = _utcnow()

    factors = []
    hour_offset = 0

    # Default: next business day 9 AM in recipient timezone
    next_send = now + timedelta(days=1)
    next_send = next_send.replace(hour=9, minute=0, second=0, microsecond=0)

    # Adjust for timezone if available
    if co and co.country:
        if "US" in co.country or "United States" in co.country:
            hour_offset = -5  # EST
            factors.append("US business hours (9 AM EST)")
        elif "UK" in co.country or "United Kingdom" in co.country:
            hour_offset = 0
            factors.append("UK business hours (9 AM GMT)")
        elif "EU" in co.country or "Europe" in co.country:
            hour_offset = 1
            factors.append("EU business hours (9 AM CET)")

    # Check if recipient has replied before (prefer their reply times)
    if dm:
        msgs = list(session.scalars(
            select(OutreachMessage).where(OutreachMessage.decision_maker_id == dm.id)
        ))
        reply_times = [m.created_at for m in msgs if m.direction == "inbound" and m.created_at]
        if reply_times:
            reply_hours = [_utc(t).hour for t in reply_times]
            avg_reply_hour = int(sum(reply_hours) / len(reply_hours))
            if avg_reply_hour:
                next_send = next_send.replace(hour=avg_reply_hour)
                factors.append(f"Recipient typically active at {avg_reply_hour}:00")

    # Avoid weekends
    while next_send.weekday() >= 5:
        next_send += timedelta(days=1)

    factors.append("Weekday business hours")

    tz_str = f"UTC{hour_offset:+d}" if hour_offset else "UTC"
    rationale = " · ".join(factors)

    return SendTimeRecommendation(
        recommended_time=next_send,
        timezone_offset=tz_str,
        factors=factors,
        rationale=rationale,
    )


# ========================================================================
# 3. Best Subject Recommendation
# ========================================================================
@dataclass
class SubjectRecommendation:
    subject: str
    reason: str
    confidence: str  # "high" | "medium" | "low"


def recommend_subject(session: Session, company_domain: str, lead: OutreachLead | None = None) -> list[SubjectRecommendation]:
    """Recommend email subjects based on opportunity, department, leadership activity, hiring."""
    co = repo.get_company(session, company_domain)
    if not co:
        return []

    opps, _ = repo.list_opportunities(session, company_domain=company_domain, limit=3)
    engagement = repo.engagement_for(session, company_domain)

    recommendations = []

    # Leadership activity hook
    leadership_sigs = list(session.scalars(
        select(LeadershipSignal).where(LeadershipSignal.company_domain == company_domain)
    ))
    if leadership_sigs:
        recent = [s for s in leadership_sigs if s.created_at and (_utcnow() - _utc(s.created_at)).days <= 30]
        if recent:
            sig = recent[0]
            if sig.movement_type == "promotion":
                recommendations.append(SubjectRecommendation(
                    subject=f"Congrats on your promotion at {co.company_name}",
                    reason="Recent promotion detected",
                    confidence="high",
                ))
            elif sig.movement_type == "new_hire":
                recommendations.append(SubjectRecommendation(
                    subject=f"Welcome to {co.company_name}",
                    reason="New executive hire detected",
                    confidence="high",
                ))

    # Opportunity hook
    if opps:
        opp = opps[0]
        if opp.opportunity_type:
            type_words = opp.opportunity_type.replace("_", " ").title()
            recommendations.append(SubjectRecommendation(
                subject=f"Opportunity: {type_words} at {co.company_name}",
                reason=f"Strong {opp.opportunity_type} signal",
                confidence="high",
            ))

    if engagement and engagement.offering:
        off = engagement.offering.lower()
        if "staff" in off or "engineer" in off:
            recommendations.append(SubjectRecommendation(
                subject=f"Engineering talent at {co.company_name}",
                reason="Staffing/engineering offering match",
                confidence="high",
            ))

    # Generic fallback
    if not recommendations:
        recommendations.append(SubjectRecommendation(
            subject=f"Quick chat about {co.company_name}",
            reason="Generic outreach",
            confidence="low",
        ))

    return recommendations[:3]


# ========================================================================
# 4. Best Email Template Recommendation
# ========================================================================
@dataclass
class TemplateRecommendation:
    template_id: int
    name: str
    category: str
    reason: str
    match_score: float  # 0–1


def recommend_template(session: Session, company_domain: str, lead: OutreachLead | None = None) -> list[TemplateRecommendation]:
    """Recommend templates based on stage, opportunity, department coverage."""
    templates = orepo.list_templates(session, active_only=True)
    if not templates:
        return []

    stage = lead.stage if lead else "research_complete"

    scored = []
    for tpl in templates:
        score = 0.0
        reasons = []

        cat = (tpl.category or "").lower()

        if stage == "research_complete" and "intro" in cat:
            score += 0.8
            reasons.append("Stage: research_complete → cold introduction")
        elif stage == "contacted" and "follow" in cat:
            score += 0.8
            reasons.append("Stage: contacted → follow-up")
        elif stage == "replied" and ("meeting" in cat or "proposal" in cat):
            score += 0.8
            reasons.append("Stage: replied → meeting/proposal")
        elif stage in ("interested", "meeting_scheduled") and "proposal" in cat:
            score += 0.8
            reasons.append("Stage: interested → proposal")

        # Hiring/staffing match
        if "hiring" in cat or "recruitment" in cat:
            score += 0.3
            reasons.append("Hiring/recruitment template")

        # Leadership angle
        if "leadership" in cat or "executive" in cat:
            score += 0.2
            reasons.append("Executive/leadership template")

        reason_str = " · ".join(reasons) if reasons else "Generic match"
        scored.append((score, TemplateRecommendation(
            template_id=tpl.id,
            name=tpl.name,
            category=tpl.category or "",
            reason=reason_str,
            match_score=score,
        )))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [rec for _, rec in scored[:3]]


# ========================================================================
# 5. Success Probability
# ========================================================================
@dataclass
class SuccessProbability:
    probability: int  # 0–100
    confidence_level: str  # "High" | "Medium" | "Low"
    factors: list[str] = field(default_factory=list)


def estimate_success_probability(session: Session, company_domain: str, lead: OutreachLead | None = None) -> SuccessProbability:
    """Estimate probability (0–100) of conversion based on scoring, engagement, signals."""
    score = repo.lead_score_for(session, company_domain)
    if not score:
        return SuccessProbability(probability=20, confidence_level="Low", factors=["No lead score"])

    pts = 0.0
    factors = []

    # Lead score (normalized 0–100 → 0–40 points)
    lead_score_norm = min(100.0, score.lead_score or 0.0) / 100.0 * 40.0
    pts += lead_score_norm
    factors.append(f"Lead score: {score.grade or 'Unknown'} ({score.lead_score or 0:.0f})")

    # Company engagement (from relationship_intelligence)
    msgs = list(session.scalars(
        select(OutreachMessage).where(
            OutreachMessage.outreach_lead_id == lead.id if lead else False
        )
    ))
    replies = sum(1 for m in msgs if m.direction == "inbound")
    if replies:
        pts += min(25, replies * 12)
        factors.append(f"Replies received: {replies}")

    # Meetings
    if lead:
        mtgs, _ = orepo.list_meetings(session, outreach_lead_id=lead.id, limit=5)
        if mtgs:
            pts += 20
            factors.append(f"Meetings scheduled: {len(mtgs)}")

    # Stage progress
    if lead:
        stage_pts = {
            "research_complete": 5,
            "outreach_ready": 10,
            "contacted": 15,
            "replied": 25,
            "interested": 30,
            "meeting_scheduled": 35,
            "proposal_sent": 40,
            "won": 100,
            "lost": 0,
        }
        stage_score = stage_pts.get(lead.stage, 0)
        pts += stage_score
        factors.append(f"Pipeline stage: {lead.stage}")

    # Opportunity alignment
    opps, _ = repo.list_opportunities(session, company_domain=company_domain, limit=3)
    if opps:
        best_opp = max(opps, key=lambda o: o.effective_opportunity_score or 0)
        if best_opp.effective_opportunity_score:
            opp_norm = min(100, best_opp.effective_opportunity_score) / 100.0 * 10.0
            pts += opp_norm
            factors.append(f"Opportunity signal: {best_opp.opportunity_type or 'Unknown'}")

    probability = max(0, min(100, int(round(pts))))

    # Confidence in the estimate
    confidence_level = "High" if len(factors) >= 3 else "Medium" if len(factors) >= 2 else "Low"

    return SuccessProbability(
        probability=probability,
        confidence_level=confidence_level,
        factors=factors,
    )


# ========================================================================
# 6. Outreach Priority
# ========================================================================
@dataclass
class OutreachPriority:
    priority: str  # "Critical" | "High" | "Medium" | "Low"
    score: int  # 0–100
    factors: list[str] = field(default_factory=list)


def classify_priority(session: Session, company_domain: str, lead: OutreachLead | None = None) -> OutreachPriority:
    """Auto-classify priority based on lead score, company tier, leadership activity, hiring."""
    score_row = repo.lead_score_for(session, company_domain)
    co = repo.get_company(session, company_domain)

    pts = 0.0
    factors = []

    # Lead score
    if score_row and score_row.lead_score:
        grade = score_row.grade or ""
        if grade in ("A+", "A"):
            pts += 40
            factors.append(f"Grade {grade}")
        elif grade == "B":
            pts += 20
            factors.append(f"Grade {grade}")
        else:
            pts += 5

    # Company tier
    if co:
        if co.company_tier == "INCUMBENT":
            pts += 25
            factors.append("Incumbent tier")
        elif co.company_tier == "ESTABLISHED":
            pts += 15
            factors.append("Established tier")
        elif co.company_tier == "SCALEUP":
            pts += 10
            factors.append("Scaleup tier")

    # Leadership activity
    sigs = list(session.scalars(
        select(LeadershipSignal).where(LeadershipSignal.company_domain == company_domain)
    ))
    if sigs:
        recent = [s for s in sigs if s.created_at and (_utcnow() - _utc(s.created_at)).days <= 30]
        if recent:
            pts += 15
            factors.append("Recent leadership activity")

    # Hiring signals (simplified — no DemandSignal import to avoid circular)
    engagement = repo.engagement_for(session, company_domain)
    if engagement and "staff" in (engagement.offering or "").lower():
        pts += 10
        factors.append("Active hiring need")

    # Stage progress
    if lead and lead.stage not in ("research_complete", "outreach_ready"):
        pts += 10
        factors.append(f"Stage: {lead.stage}")

    priority_pts = max(0, min(100, int(round(pts))))

    if priority_pts >= 75:
        priority = "Critical"
    elif priority_pts >= 50:
        priority = "High"
    elif priority_pts >= 25:
        priority = "Medium"
    else:
        priority = "Low"

    return OutreachPriority(
        priority=priority,
        score=priority_pts,
        factors=factors,
    )


# ========================================================================
# 7. Recommended Outreach Sequence
# ========================================================================
@dataclass
class SequenceStep:
    order: int
    action: str
    description: str
    rationale: str


def recommend_sequence(session: Session, company_domain: str, lead: OutreachLead | None = None) -> list[SequenceStep]:
    """Generate deterministic outreach sequence based on stage."""
    stage = lead.stage if lead else "research_complete"

    sequences = {
        "research_complete": [
            SequenceStep(1, "Initial Contact", "Send cold intro email to primary contact", "Start with most reachable contact"),
            SequenceStep(2, "Follow-up", "Follow up 5 days later if no reply", "Gentle nudge within attention window"),
            SequenceStep(3, "Meeting Request", "Propose 15-min call or meeting", "Move to higher-bandwidth conversation"),
            SequenceStep(4, "Executive Escalation", "Loop in director+ if no response", "Increase executive visibility"),
        ],
        "outreach_ready": [
            SequenceStep(1, "Primary Contact Intro", "Send personalized intro to primary", "Fresh start with best contact"),
            SequenceStep(2, "Meeting Request", "Propose meeting within 48 hours", "Capitalize on engagement"),
        ],
        "contacted": [
            SequenceStep(1, "Follow-up", "Send follow-up if no reply in 3 days", "Maintain momentum"),
            SequenceStep(2, "Meeting Request", "Escalate to meeting request", "Move to higher engagement"),
        ],
        "replied": [
            SequenceStep(1, "Meeting Request", "Propose specific times/dates", "Convert reply to meeting"),
            SequenceStep(2, "Meeting Confirmation", "Confirm meeting details", "Ensure attendance"),
        ],
        "interested": [
            SequenceStep(1, "Proposal", "Send proposal or pitch deck", "Provide concrete offering"),
            SequenceStep(2, "Follow-up Call", "Schedule call to discuss proposal", "Address objections"),
        ],
        "meeting_scheduled": [
            SequenceStep(1, "Pre-Meeting Prep", "Send agenda and background", "Maximize meeting value"),
            SequenceStep(2, "Post-Meeting", "Send summary and next steps", "Confirm agreements"),
        ],
        "proposal_sent": [
            SequenceStep(1, "Follow-up", "Check in 1 week after proposal", "Keep momentum"),
            SequenceStep(2, "Negotiation", "Address pricing/terms if raised", "Move toward close"),
        ],
    }

    return sequences.get(stage, sequences["research_complete"])


# ========================================================================
# 8. Analytics
# ========================================================================
@dataclass
class OutreachAnalyticsDetail:
    emails_sent: int = 0
    replies: int = 0
    meetings: int = 0
    reply_rate: float = 0.0
    meeting_rate: float = 0.0
    conversion_rate: float = 0.0


def user_analytics(session: Session, user_id: int) -> OutreachAnalyticsDetail:
    """Per-user email/reply/meeting rates."""
    leads, _ = orepo.list_leads(session, owner_id=user_id, limit=10000)
    lead_ids = [lead.id for lead, _, _ in leads]

    msgs = list(session.scalars(
        select(OutreachMessage).where(OutreachMessage.outreach_lead_id.in_(lead_ids))
    )) if lead_ids else []

    sent = sum(1 for m in msgs if m.direction == "outbound" and m.status in ("sent", "replied"))
    replies = sum(1 for m in msgs if m.direction == "inbound")

    mtgs, _ = orepo.list_meetings(session, limit=10000)
    mtg_count = len(mtgs)

    reply_rate = (replies / sent) if sent else 0.0
    meeting_rate = (mtg_count / sent) if sent else 0.0
    conversion_rate = (sum(1 for l, _, _ in leads if l.stage in ("won",)) / len(leads)) if leads else 0.0

    return OutreachAnalyticsDetail(
        emails_sent=sent,
        replies=replies,
        meetings=mtg_count,
        reply_rate=round(reply_rate, 3),
        meeting_rate=round(meeting_rate, 3),
        conversion_rate=round(conversion_rate, 3),
    )


def company_analytics(session: Session, company_domain: str) -> OutreachAnalyticsDetail:
    """Per-company outreach activity and trend."""
    lead = orepo.get_lead_by_domain(session, company_domain)
    if not lead:
        return OutreachAnalyticsDetail()

    msgs = list(session.scalars(
        select(OutreachMessage).where(OutreachMessage.outreach_lead_id == lead.id)
    ))

    sent = sum(1 for m in msgs if m.direction == "outbound" and m.status in ("sent", "replied"))
    replies = sum(1 for m in msgs if m.direction == "inbound")

    mtgs, _ = orepo.list_meetings(session, outreach_lead_id=lead.id, limit=100)

    reply_rate = (replies / sent) if sent else 0.0
    meeting_rate = (len(mtgs) / sent) if sent else 0.0

    return OutreachAnalyticsDetail(
        emails_sent=sent,
        replies=replies,
        meetings=len(mtgs),
        reply_rate=round(reply_rate, 3),
        meeting_rate=round(meeting_rate, 3),
        conversion_rate=0.0,
    )


def template_analytics(session: Session, template_id: int) -> OutreachAnalyticsDetail:
    """Per-template usage and performance."""
    msgs = list(session.scalars(
        select(OutreachMessage).where(OutreachMessage.template_id == template_id)
    ))

    sent = sum(1 for m in msgs if m.direction == "outbound" and m.status in ("sent", "replied"))
    replies = sum(1 for m in msgs if m.direction == "inbound" and m.parent_message_id is not None)

    reply_rate = (replies / sent) if sent else 0.0

    return OutreachAnalyticsDetail(
        emails_sent=sent,
        replies=replies,
        reply_rate=round(reply_rate, 3),
    )


# ========================================================================
# 9. Campaign Intelligence (composite of 1–7)
# ========================================================================
@dataclass
class CampaignIntelligence:
    best_contact: ContactRecommendation | None = None
    best_send_time: SendTimeRecommendation | None = None
    best_subjects: list[SubjectRecommendation] = field(default_factory=list)
    best_template: TemplateRecommendation | None = None
    success_probability: SuccessProbability | None = None
    outreach_priority: OutreachPriority | None = None


def campaign_intelligence(session: Session, company_domain: str, lead: OutreachLead | None = None) -> CampaignIntelligence:
    """All outreach intelligence for a company in one call."""
    contacts = recommend_contacts(session, company_domain, limit=1)
    send_time = recommend_send_time(session, company_domain, contacts[0].decision_maker_id if contacts else None)
    subjects = recommend_subject(session, company_domain, lead)
    templates = recommend_template(session, company_domain, lead)
    success = estimate_success_probability(session, company_domain, lead)
    priority = classify_priority(session, company_domain, lead)

    return CampaignIntelligence(
        best_contact=contacts[0] if contacts else None,
        best_send_time=send_time,
        best_subjects=subjects,
        best_template=templates[0] if templates else None,
        success_probability=success,
        outreach_priority=priority,
    )


def _utc(dt: datetime | None) -> datetime | None:
    """Ensure datetime is UTC-aware."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
