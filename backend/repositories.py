"""Data-access layer: every SQLAlchemy query lives here (no HTTP, no Pydantic).

Functions take a Session and return ORM objects / row tuples + totals. Services
convert these to schemas.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.orm import Session

from master_db.models import (
    Company,
    CompanyNote,
    CompanyRollup,
    DecisionMaker,
    DecisionMakerContact,
    DecisionMakerNote,
    DemandSignal,
    EngagementRecommendation,
    Job,
    LeadAssignment,
    LeadAssignmentEvent,
    LeadReview,
    LeadReviewEvent,
    LeadScore,
    LeadershipSignal,
    NewsSource,
    Opportunity,
    OpportunityArticle,
    OpportunityReview,
    PipelineRun,
    ResolutionReviewQueue,
    ReviewAction,
    User,
    UserAuditEvent,
)

_COMPANY_SORTS = {
    "company_name": Company.company_name,
    "company_domain": Company.company_domain,
    "company_tier": Company.company_tier,
    "created_at": Company.created_at,
    "lead_score": LeadScore.lead_score,
}
COMPANY_SORT_FIELDS = tuple(_COMPANY_SORTS)


def _count(session: Session, stmt) -> int:
    return session.scalar(select(func.count()).select_from(stmt.subquery())) or 0


# ---------------------------------------------------------------- companies
def list_companies(
    session: Session, *, q=None, domain=None, tier=None, prospect_type=None,
    grade=None, sort="company_name", order="asc", limit=25, offset=0,
):
    filters = []
    if q:
        filters.append(Company.company_name.ilike(f"%{q}%"))
    if domain:
        filters.append(Company.company_domain.ilike(f"%{domain}%"))
    if tier:
        filters.append(Company.company_tier == tier)
    if prospect_type:
        filters.append(Company.prospect_type == prospect_type)
    if grade:
        filters.append(LeadScore.grade == grade)

    base = select(Company, LeadScore).outerjoin(
        LeadScore, LeadScore.company_domain == Company.company_domain
    )
    if filters:
        base = base.where(and_(*filters))

    total = _count(session, base)
    col = _COMPANY_SORTS.get(sort, Company.company_name)
    direction = col.desc() if order == "desc" else col.asc()
    rows = session.execute(base.order_by(direction).limit(limit).offset(offset)).all()
    return rows, total


def get_company(session: Session, domain: str) -> Company | None:
    return session.get(Company, domain)


# -------------------------------------------------- single-company bundles
def opportunities_for(session: Session, domain: str) -> list[Opportunity]:
    return list(session.scalars(
        select(Opportunity).where(Opportunity.company_domain == domain)
        .order_by(Opportunity.effective_opportunity_score.desc())
    ))


def jobs_for(session: Session, domain: str, limit: int = 200) -> list[Job]:
    return list(session.scalars(
        select(Job).where(Job.company_domain == domain)
        .order_by(Job.engineering_relevance_score.desc()).limit(limit)
    ))


def demand_for(session: Session, domain: str) -> DemandSignal | None:
    return session.get(DemandSignal, domain)


def rollup_for(session: Session, domain: str) -> CompanyRollup | None:
    return session.get(CompanyRollup, domain)


def decision_makers_for(session: Session, domain: str) -> list[DecisionMaker]:
    return list(session.scalars(
        select(DecisionMaker).where(DecisionMaker.company_domain == domain)
        # Rank by effective score: agent_score is authoritative once AI-screened,
        # match_score is the fallback (mirrors the scraper's agentScore ?? matchScore).
        .order_by(func.coalesce(DecisionMaker.agent_score, DecisionMaker.match_score).desc())
    ))


def lead_for(session: Session, domain: str) -> LeadScore | None:
    return session.get(LeadScore, domain)


def review_items_for(session: Session, domain: str) -> list[ResolutionReviewQueue]:
    return list(session.scalars(
        select(ResolutionReviewQueue).where(
            or_(ResolutionReviewQueue.suggested_domain == domain,
                ResolutionReviewQueue.resolved_domain == domain),
            ResolutionReviewQueue.status == "pending",
        )
    ))


# ------------------------------------------------------------------- leads
LEAD_SORTS = ("model", "human", "combined")

# Display ordering for the "human" sort: strategic first … disqualified last,
# unreviewed in the middle (a grouping, independent of any score effect).
_HUMAN_STATUS_RANK = {
    "strategic_account": 5, "approved": 4, "watchlist": 3,
    "needs_review": 2, "disqualified": 0,
}


def _human_rank_case():
    whens = [(LeadReview.review_status == k, literal(v)) for k, v in _HUMAN_STATUS_RANK.items()]
    return case(*whens, else_=literal(1))   # unreviewed sits above 'disqualified'


def list_leads(session: Session, *, grade=None, tier=None, prospect_type=None,
               sort="model", limit=25, offset=0):
    """Ranked leads. Left-joins the human review so each row carries the model
    score AND the human status, and supports three orderings (P-task viii §5):
    ``model`` (the model's priority_rank — default), ``human`` (group by the
    human-status tier, then model score), ``combined`` (the adjusted score —
    model score plus any enabled human-review effect)."""
    filters = []
    if grade:
        filters.append(LeadScore.grade == grade)
    if tier:
        filters.append(Company.company_tier == tier)
    if prospect_type:
        filters.append(Company.prospect_type == prospect_type)

    base = (
        select(LeadScore, Company, LeadReview)
        .join(Company, Company.company_domain == LeadScore.company_domain)
        .outerjoin(LeadReview, LeadReview.company_domain == LeadScore.company_domain)
    )
    if filters:
        base = base.where(and_(*filters))
    total = _count(session, base)

    # adjusted_score falls back to the model lead_score when not yet computed (NULL).
    adjusted = func.coalesce(LeadScore.adjusted_score, LeadScore.lead_score)
    if sort == "combined":
        order = (adjusted.desc(), LeadScore.priority_rank.asc())
    elif sort == "human":
        order = (_human_rank_case().desc(), LeadScore.lead_score.desc())
    else:  # "model" (default) — the model's own ranking, untouched by human review
        order = (LeadScore.priority_rank.asc(),)
    rows = session.execute(base.order_by(*order).limit(limit).offset(offset)).all()
    return rows, total


# ----------------------------------------------------------- opportunities
_COMPANY_NEWS_TYPES = ("EXECUTIVE_HIRE", "LEADERSHIP_CHANGE", "ROLE_CHANGE", "COMPANY_NEWS")


_OPPORTUNITY_SORTS = {
    # newest / oldest by publication date (ingested_at breaks ties / covers blank dates)
    "newest": (Opportunity.published_date.desc(), Opportunity.ingested_at.desc()),
    "oldest": (Opportunity.published_date.asc(), Opportunity.ingested_at.asc()),
    "score": (Opportunity.effective_opportunity_score.desc(),),
}
OPPORTUNITY_SORT_FIELDS = tuple(_OPPORTUNITY_SORTS)


def list_opportunities(session: Session, *, opportunity_type=None, company_domain=None,
                       date_from=None, date_to=None, annual_lists_only=False,
                       company_news_only=False, lifecycle_status=None,
                       hide_archived=False, sort=None, limit=25, offset=0):
    filters = []
    if annual_lists_only:
        filters.append(Opportunity.opportunity_type == "ANNUAL_LIST")
    if company_news_only:
        filters.append(Opportunity.opportunity_type.in_(_COMPANY_NEWS_TYPES))
    if opportunity_type:
        filters.append(Opportunity.opportunity_type == opportunity_type)
    if company_domain:
        filters.append(Opportunity.company_domain == company_domain)
    if lifecycle_status:
        filters.append(Opportunity.lifecycle_status == lifecycle_status)
    if hide_archived:
        # Backward-compatible opt-in: drop analyst-hidden events (archived / not-relevant).
        filters.append(Opportunity.lifecycle_status != "ARCHIVED")
        filters.append(Opportunity.is_relevant.is_(True))
    if date_from:
        filters.append(Opportunity.published_date >= date_from)
    if date_to:
        filters.append(Opportunity.published_date <= date_to)

    base = select(Opportunity)
    if filters:
        base = base.where(and_(*filters))
    total = _count(session, base)
    order = _OPPORTUNITY_SORTS.get(sort or "score", _OPPORTUNITY_SORTS["score"])
    rows = list(session.scalars(
        base.order_by(*order).limit(limit).offset(offset)
    ))
    return rows, total


# ---------------------------------------------------- opportunity detail / news
def get_opportunity(session: Session, opportunity_id: str) -> Opportunity | None:
    return session.get(Opportunity, opportunity_id)


def opportunity_sources(session: Session, opportunity_id: str) -> list[OpportunityArticle]:
    return list(session.scalars(
        select(OpportunityArticle)
        .where(OpportunityArticle.opportunity_id == opportunity_id)
        .order_by(OpportunityArticle.published_at.desc(), OpportunityArticle.id.desc())
    ))


def opportunity_reviews(session: Session, opportunity_id: str) -> list[OpportunityReview]:
    return list(session.scalars(
        select(OpportunityReview)
        .where(OpportunityReview.opportunity_id == opportunity_id)
        .order_by(OpportunityReview.created_at.desc(), OpportunityReview.id.desc())
    ))


def related_opportunities(session: Session, opp: Opportunity) -> list[Opportunity]:
    """Other opportunities in the same related group (fallback: same company, other
    events), newest-scored first, excluding *opp* itself."""
    if opp.related_group_id:
        stmt = select(Opportunity).where(
            Opportunity.related_group_id == opp.related_group_id,
            Opportunity.opportunity_id != opp.opportunity_id,
        )
    else:
        stmt = select(Opportunity).where(
            Opportunity.company_domain == opp.company_domain,
            Opportunity.opportunity_id != opp.opportunity_id,
        )
    return list(session.scalars(
        stmt.order_by(Opportunity.effective_opportunity_score.desc()).limit(25)
    ))


def company_opportunity_timeline(session: Session, company_domain: str,
                                 limit: int = 100) -> list[Opportunity]:
    """Chronological company event timeline (newest first) for the detail panel."""
    return list(session.scalars(
        select(Opportunity)
        .where(Opportunity.company_domain == company_domain)
        .order_by(Opportunity.published_date.desc(), Opportunity.ingested_at.desc())
        .limit(limit)
    ))


def list_news_sources(session: Session) -> list[NewsSource]:
    return list(session.scalars(select(NewsSource).order_by(NewsSource.name)))


def add_opportunity_review(session: Session, opportunity_id: str, *, action: str,
                           actor_email: str, detail: str = "",
                           before: dict | None = None, after: dict | None = None) -> OpportunityReview:
    review = OpportunityReview(
        opportunity_id=opportunity_id, action=action, actor_email=actor_email or "",
        detail=detail or "", before_snapshot=before or {}, after_snapshot=after or {},
    )
    session.add(review)
    session.flush()
    return review


# --------------------------------------------------------- demand signals
def list_demand_signals(session: Session, *, min_demand_score=None, technology_focus=None, limit=25, offset=0):
    filters = []
    if min_demand_score is not None:
        filters.append(DemandSignal.demand_score >= min_demand_score)
    if technology_focus:
        filters.append(or_(
            DemandSignal.technologies_detected.ilike(f"%{technology_focus}%"),
            DemandSignal.primary_focus.ilike(f"%{technology_focus}%"),
        ))
    base = select(DemandSignal)
    if filters:
        base = base.where(and_(*filters))
    total = _count(session, base)
    rows = list(session.scalars(
        base.order_by(DemandSignal.demand_score.desc()).limit(limit).offset(offset)
    ))
    return rows, total


# ------------------------------------------------- leadership signals (P-task 8)
def _ldr_recency_order():
    """Most recent first; undated rows (event_age_days < 0) sort last."""
    return (case((LeadershipSignal.event_age_days < 0, 1), else_=0), LeadershipSignal.event_age_days.asc())


def leadership_signals_for(session: Session, domain: str) -> list[LeadershipSignal]:
    return list(session.scalars(
        select(LeadershipSignal).where(LeadershipSignal.company_domain == domain)
        .order_by(*_ldr_recency_order())
    ))


def leadership_for_dm(session: Session, dm_id: int) -> list[LeadershipSignal]:
    """Leadership-movement signals attributed to a specific decision maker."""
    return list(session.scalars(
        select(LeadershipSignal).where(LeadershipSignal.decision_maker_id == dm_id)
        .order_by(*_ldr_recency_order())
    ))


def engagement_for(session: Session, domain: str) -> EngagementRecommendation | None:
    return session.get(EngagementRecommendation, domain)


def list_leadership_signals(session: Session, *, company_domain=None, movement_type=None,
                            seniority_band=None, source=None, limit=25, offset=0):
    filters = []
    if company_domain:
        filters.append(LeadershipSignal.company_domain == company_domain)
    if movement_type:
        filters.append(LeadershipSignal.movement_type == movement_type)
    if seniority_band:
        filters.append(LeadershipSignal.seniority_band == seniority_band)
    if source:
        filters.append(LeadershipSignal.source == source)
    base = select(LeadershipSignal)
    if filters:
        base = base.where(and_(*filters))
    total = _count(session, base)
    rows = list(session.scalars(
        base.order_by(*_ldr_recency_order()).limit(limit).offset(offset)
    ))
    return rows, total


# --------------------------------------------------------- decision makers
# Senior-leadership detection — used by the `senior` filter + the per-company count.
# Abbreviations must match as whole tokens, never as raw substrings: a naive
# "%cto%" matches "semiCONDUCTOrs" and "%cro%" matches "miCROchip", which would
# flag ordinary engineers at chip companies as executives. We flatten separators
# to spaces and pad the title, then require a leading+trailing space around each
# abbreviation (and a leading space before each full word).
_SENIOR_ABBREV = ("ceo", "cto", "coo", "cfo", "cmo", "cio", "ciso", "cpo", "cro",
                  "cdo", "cso", "cxo", "vp", "svp", "evp", "avp")
_SENIOR_WORDS = ("chief", "founder", "president", "director", "head of")
_SENIOR_SENIORITY = ("c_level", "c-level", "executive", "owner", "partner", "founder", "chief")
_TITLE_SEPARATORS = (",", "/", "|", "(", ")", "-", "&", ".", ":", ";")


def _norm_title():
    """Lower-cased title with separators flattened to spaces and padded with a
    leading/trailing space, so token patterns can match on word boundaries."""
    expr = func.lower(func.coalesce(DecisionMaker.current_title, ""))
    for ch in _TITLE_SEPARATORS:
        expr = func.replace(expr, ch, " ")
    return literal(" ").concat(expr).concat(literal(" "))


def _senior_clause():
    title = _norm_title()
    return or_(
        func.lower(func.coalesce(DecisionMaker.seniority, "")).in_(_SENIOR_SENIORITY),
        *[title.like(f"% {a} %") for a in _SENIOR_ABBREV],   # both word boundaries
        *[title.like(f"% {w}%") for w in _SENIOR_WORDS],     # leading boundary
    )


def list_decision_makers(session: Session, *, company_domain=None, seniority=None,
                         senior=False, limit=25, offset=0):
    filters = []
    if company_domain:
        filters.append(DecisionMaker.company_domain == company_domain)
    if seniority:
        filters.append(DecisionMaker.seniority == seniority)
    if senior:
        filters.append(_senior_clause())
    base = select(DecisionMaker)
    if filters:
        base = base.where(and_(*filters))
    total = _count(session, base)
    rows = list(session.scalars(
        base.order_by(func.coalesce(DecisionMaker.agent_score, DecisionMaker.match_score).desc())
        .limit(limit).offset(offset)
    ))
    return rows, total


def decision_maker_companies(session: Session):
    """(company_domain, company_name, count) for resolved decision makers, plus the
    count of still-unresolved contacts. Powers the company-first directory view."""
    rows = session.execute(
        select(DecisionMaker.company_domain, Company.company_name, func.count().label("n"),
               func.sum(case((_senior_clause(), 1), else_=0)).label("senior"))
        .join(Company, Company.company_domain == DecisionMaker.company_domain)
        .where(DecisionMaker.company_domain.is_not(None))
        .group_by(DecisionMaker.company_domain, Company.company_name)
        .order_by(func.count().desc(), Company.company_name)
    ).all()
    unresolved = session.scalar(
        select(func.count()).select_from(DecisionMaker).where(DecisionMaker.company_domain.is_(None))
    ) or 0
    return rows, unresolved


def get_decision_maker(session: Session, dm_id: int) -> DecisionMaker | None:
    return session.get(DecisionMaker, dm_id)


def get_dm_contact(session: Session, dm_id: int) -> DecisionMakerContact | None:
    return session.scalar(
        select(DecisionMakerContact).where(DecisionMakerContact.decision_maker_id == dm_id)
    )


def upsert_dm_contact(session: Session, *, dm_id: int, added_by: int | None, added_by_email: str,
                      work_email: str, work_phone: str, notes: str) -> DecisionMakerContact:
    contact = get_dm_contact(session, dm_id)
    if contact is None:
        contact = DecisionMakerContact(decision_maker_id=dm_id)
        session.add(contact)
    contact.work_email = work_email
    contact.work_phone = work_phone
    contact.notes = notes
    contact.added_by = added_by
    contact.added_by_email = added_by_email
    session.commit()
    return contact


# ------------------------------------------------------ decision-maker notes
def list_dm_notes(session: Session, dm_id: int, *, viewer_id: int | None) -> list[DecisionMakerNote]:
    """Shared notes (admin/manager/team — visible to all) plus the viewer's own
    PERSONAL notes. Other users' personal notes are never returned. Ordered by
    tier (admin → manager → team → personal), then most-recent first.
    """
    visible = or_(
        DecisionMakerNote.note_type.in_(("admin", "manager", "team")),
        and_(DecisionMakerNote.note_type == "personal",
             DecisionMakerNote.created_by == viewer_id),
    )
    tier = case(
        (DecisionMakerNote.note_type == "admin", 0),
        (DecisionMakerNote.note_type == "manager", 1),
        (DecisionMakerNote.note_type == "team", 2),
        else_=3,
    )
    stmt = (
        select(DecisionMakerNote)
        .where(DecisionMakerNote.decision_maker_id == dm_id, visible)
        .order_by(tier, DecisionMakerNote.created_at.desc())
    )
    return list(session.scalars(stmt))


def roles_for_users(session: Session, user_ids: list[int | None]) -> dict[int, str]:
    """Map ``{user_id: role}`` for the given ids — used to show a note author's role
    without an N+1 (one query for the whole notes list)."""
    ids = [i for i in dict.fromkeys(user_ids) if i is not None]
    if not ids:
        return {}
    rows = session.execute(select(User.id, User.role).where(User.id.in_(ids))).all()
    return {uid: role for uid, role in rows}


def get_dm_note(session: Session, note_id: int) -> DecisionMakerNote | None:
    return session.get(DecisionMakerNote, note_id)


def create_dm_note(session: Session, *, dm_id: int, note_type: str, created_by: int | None,
                   author_email: str, content: str) -> DecisionMakerNote:
    note = DecisionMakerNote(
        decision_maker_id=dm_id, note_type=note_type, created_by=created_by,
        author_email=author_email, content=content,
    )
    session.add(note)
    session.commit()
    return note


def update_dm_note(session: Session, note: DecisionMakerNote, *, content: str) -> DecisionMakerNote:
    note.content = content
    session.commit()
    return note


def delete_dm_note(session: Session, note: DecisionMakerNote) -> None:
    session.delete(note)
    session.commit()


# ----------------------------------------------------------- analytics
def table_counts(session: Session) -> dict[str, int]:
    def n(model) -> int:
        return session.scalar(select(func.count()).select_from(model)) or 0

    return {
        "companies": n(Company),
        "opportunities": n(Opportunity),
        "jobs": n(Job),
        "demand_signals": n(DemandSignal),
        "decision_makers": n(DecisionMaker),
        "leads": n(LeadScore),
    }


def grade_distribution(session: Session) -> dict[str, int]:
    return {
        g: c for g, c in session.execute(
            select(LeadScore.grade, func.count()).group_by(LeadScore.grade)
        ).all()
    }


def top_leads(session: Session, limit: int = 10):
    return session.execute(
        select(LeadScore, Company).join(Company, Company.company_domain == LeadScore.company_domain)
        .order_by(LeadScore.priority_rank.asc()).limit(limit)
    ).all()


# ----------------------------------------------------------- review queue
def list_review(session: Session, *, status=None, source_engine=None, match_type=None, limit=25, offset=0):
    filters = []
    if status:
        filters.append(ResolutionReviewQueue.status == status)
    if source_engine:
        filters.append(ResolutionReviewQueue.source_engine == source_engine)
    if match_type:
        filters.append(ResolutionReviewQueue.match_type == match_type)
    base = select(ResolutionReviewQueue)
    if filters:
        base = base.where(and_(*filters))
    total = _count(session, base)
    rows = list(session.scalars(
        base.order_by(ResolutionReviewQueue.id.desc()).limit(limit).offset(offset)
    ))
    return rows, total


def get_review(session: Session, review_id: int) -> ResolutionReviewQueue | None:
    return session.get(ResolutionReviewQueue, review_id)


def list_review_actions(session: Session, review_id: int) -> list[ReviewAction]:
    return list(session.scalars(
        select(ReviewAction).where(ReviewAction.review_id == review_id)
        .order_by(ReviewAction.id.asc())
    ))


# ------------------------------------------------------- pipeline + coverage
PIPELINE_COMPONENTS = ("industry", "blog", "news", "annual_list", "company_news", "career", "linkedin", "scoring", "leadership", "engagement")


def recent_pipeline_runs(session: Session, limit: int = 20) -> list[PipelineRun]:
    return list(session.scalars(
        select(PipelineRun).order_by(PipelineRun.run_id.desc()).limit(limit)
    ))


def pipeline_health(session: Session) -> list[dict]:
    """Per-component freshness from pipeline_runs (last status / success / duration)."""
    out: list[dict] = []
    for c in PIPELINE_COMPONENTS:
        last = session.scalar(
            select(PipelineRun).where(PipelineRun.component == c).order_by(PipelineRun.run_id.desc())
        )
        last_ok = session.scalar(
            select(PipelineRun).where(PipelineRun.component == c, PipelineRun.status == "success")
            .order_by(PipelineRun.run_id.desc())
        )
        failed = session.scalar(
            select(func.count()).select_from(PipelineRun)
            .where(PipelineRun.component == c, PipelineRun.status == "failed")
        ) or 0
        out.append({
            "component": c,
            "last_status": last.status if last else "never",
            "last_run": last.started_at if last else None,
            "last_success": (last_ok.finished_at or last_ok.started_at) if last_ok else None,
            "last_duration_ms": last.duration_ms if last else 0,
            "failed_runs": int(failed),
        })
    return out


def coverage(session: Session) -> dict:
    """Engine-coverage matrix: how many companies carry each signal, and the
    distribution of how many of the 3 enrichment signals (opportunity / demand /
    decision-makers) each company has — which surfaces the cross-engine overlap gap."""
    domains = set(session.scalars(select(Company.company_domain)))
    opp = set(session.scalars(select(Opportunity.company_domain).distinct()))
    demand = set(session.scalars(select(DemandSignal.company_domain).distinct()))
    dm = set(session.scalars(select(DecisionMaker.company_domain).distinct())) - {None}
    scored = set(session.scalars(select(LeadScore.company_domain)))

    distribution = {0: 0, 1: 0, 2: 0, 3: 0}
    for d in domains:
        distribution[(d in opp) + (d in demand) + (d in dm)] += 1

    return {
        "total_companies": len(domains),
        "with_opportunities": len(domains & opp),
        "with_demand": len(domains & demand),
        "with_decision_makers": len(domains & dm),
        "with_lead_score": len(domains & scored),
        "with_all_three": distribution[3],
        "signal_distribution": {str(k): v for k, v in distribution.items()},
    }


# A run still marked "running" past this is treated as dead (crashed mid-run), not
# in-progress — otherwise an interrupted run would pin the freshness signal forever.
_RUNNING_STALE_SECONDS = 90 * 60


def last_scored_at(session: Session) -> datetime | None:
    """Newest ``lead_scores.scored_at`` — advances on every (re-)score, including a
    direct ``python -m lead_scoring.run``. Folded into the analytics cache version so
    a re-score invalidates cached dashboards even outside the orchestrator pipeline."""
    return session.scalar(select(func.max(LeadScore.scored_at)))


def last_successful_refresh(session: Session) -> datetime | None:
    """When the last full pipeline completed = newest successful ``scoring`` run.

    Scoring is the final stage, so its last success marks the last clean refresh.
    Drives both the freshness badge and the analytics response-cache version.
    """
    row = session.scalar(
        select(PipelineRun)
        .where(PipelineRun.component == "scoring", PipelineRun.status == "success")
        .order_by(PipelineRun.run_id.desc())
    )
    return (row.finished_at or row.started_at) if row else None


# ------------------------------------------------------------------- users
def get_user_by_email(session: Session, email: str) -> User | None:
    if not email:
        return None
    return session.scalar(select(User).where(User.email == email.lower().strip()))


def get_user_by_google_sub(session: Session, google_sub: str) -> User | None:
    if not google_sub:
        return None
    return session.scalar(select(User).where(User.google_sub == google_sub))


def get_user_by_microsoft_oid(session: Session, microsoft_oid: str) -> User | None:
    if not microsoft_oid:
        return None
    return session.scalar(select(User).where(User.microsoft_oid == microsoft_oid))


def get_user(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def create_user(session: Session, *, email: str, full_name: str = "", picture: str = "",
                role: str = "member", status: str = "active", google_sub: str | None = None,
                microsoft_oid: str | None = None) -> User:
    user = User(email=email.lower().strip(), full_name=full_name or "", picture=picture or "",
                role=role, status=status, is_active=(status == "active"), login_count=0,
                google_sub=google_sub or None, microsoft_oid=microsoft_oid or None)
    session.add(user)
    session.flush()
    return user


def set_user_microsoft_oid(session: Session, user: User, microsoft_oid: str) -> User:
    """Backfill a user's Microsoft object id the first time they sign in via
    Microsoft with an account that predates this column (e.g. one created by the
    dev bypass, or during a prior auth mechanism)."""
    user.microsoft_oid = microsoft_oid
    session.flush()
    return user


def touch_login(session: Session, user: User, *, full_name: str | None = None,
                picture: str | None = None, role: str | None = None) -> User:
    """Record a successful authenticated login: bump count + last_login, refresh profile."""
    user.last_login_at = datetime.now(timezone.utc)
    user.login_count = (user.login_count or 0) + 1
    if full_name:
        user.full_name = full_name
    if picture:
        user.picture = picture
    if role:
        user.role = role
    session.flush()
    return user


def list_users(
    session: Session, *, status: str | None = None, q: str | None = None,
    limit: int = 50, offset: int = 0,
) -> tuple[list[User], int]:
    stmt = select(User)
    if status:
        stmt = stmt.where(User.status == status)
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(User.email).like(like), func.lower(User.full_name).like(like)))
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(session.scalars(stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)))
    return rows, total


def count_pending_users(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(User).where(User.status == "pending")
    ) or 0


def list_active_users(session: Session) -> list[User]:
    """Active, enabled users — the recipients for scheduled-run notifications.
    Excludes pending/disabled/rejected/deleted (soft-deleted rows also have their
    email scrubbed to a @deleted.invalid placeholder, doubly excluded)."""
    return list(session.scalars(
        select(User)
        .where(User.status == "active", User.is_active.is_(True))
        .order_by(User.email)
    ))


def count_active_admins(session: Session, *, exclude_id: int | None = None) -> int:
    """Admin-tier (admin OR super_admin) active users — "is there still someone who
    can administer the platform," not the literal string 'admin'."""
    stmt = select(func.count()).select_from(User).where(
        User.role.in_(("admin", "super_admin")), User.status == "active"
    )
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    return session.scalar(stmt) or 0


def count_active_super_admins(session: Session, *, exclude_id: int | None = None) -> int:
    stmt = select(func.count()).select_from(User).where(
        User.role == "super_admin", User.status == "active"
    )
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    return session.scalar(stmt) or 0


class LastPrivilegedUserError(Exception):
    """A role/status/deletion change would leave zero active admins, or zero active
    super_admins. See lock_active_privileged_users for the concurrency rationale."""


def is_active_privileged(user: User) -> bool:
    """True if *user* currently counts toward the active-admin-tier invariant."""
    return user.role in ("admin", "super_admin") and user.status == "active"


def role_change_exposure(user: User, new_role: str) -> tuple[bool, bool]:
    """(leaves_admin_tier, leaves_super_admin) for a user.role -> new_role change --
    which of the two active-privileged-user invariants this specific transition
    could violate. Both False when the change cannot affect either (already
    inactive, staying in/out of tier, etc.) -- callers use this to skip the lock
    entirely for a transition that can never be unsafe."""
    if user.status != "active":
        return False, False
    leaves_admin_tier = user.role in ("admin", "super_admin") and new_role not in ("admin", "super_admin")
    leaves_super_admin = user.role == "super_admin" and new_role != "super_admin"
    return leaves_admin_tier, leaves_super_admin


def lock_active_privileged_users(session: Session) -> list[User]:
    """F1 fix: row-lock every currently-active admin-tier user (admin OR
    super_admin), in a deterministic id-ascending order, inside the CALLER's own
    transaction, and return the locked rows.

    Concurrency rationale (PostgreSQL READ COMMITTED): two concurrent transactions
    each demoting/disabling/deleting a *different* active admin-tier user must not
    both independently observe "another admin-tier user is still active" and both
    commit -- that plain count-then-mutate race is F1. Locking the whole cohort in
    ONE statement (not a loop of per-row locks) means a second transaction wanting
    to touch any row in this same set blocks on THIS statement until the first
    transaction commits or rolls back; Postgres then gives the unblocked SELECT ...
    FOR UPDATE a fresh snapshot that reflects the just-committed change (a locked
    row that was concurrently UPDATEd is always re-fetched at its latest committed
    version, never the pre-lock snapshot) -- so the invariant is always evaluated
    against current, not stale, state. The row set is always the same query (no
    per-caller variation), so every invariant-breaking mutation path that calls this
    acquires a compatible lock set; ORDER BY id keeps lock acquisition deterministic
    across callers.

    SQLite (dev/test) does not support FOR UPDATE, so this is a plain SELECT there --
    the invariant check runs against an in-memory Python snapshot with no row lock
    behind it, so the F1 race IS reproducible on SQLite (verified directly by
    tests/test_privileged_user_concurrency.py's threaded smoke test). That is
    expected: this function's concurrency guarantee is PostgreSQL-specific, and only
    the dedicated live-Postgres test proves it. Callers must evaluate the invariant
    against the RETURNED rows (not a separately-run count) and must do so, and
    commit, before releasing this lock.

    populate_existing=True is required, not optional: the caller's session has
    almost always already loaded one of this cohort's rows earlier in the same
    transaction (the acting admin's own User row, loaded by the auth dependency
    before the route handler ever runs; or, in this module's own callers, the
    mutation target via _get_target). SQLAlchemy's identity map hands back that
    SAME Python object for a repeat load of the same primary key and does NOT
    overwrite its attributes from a later query's result, even when that later
    query is this lock-protected, just-unblocked, freshly-committed read. Without
    populate_existing, a second transaction that blocked behind the first's FOR
    UPDATE -- and then correctly re-fetched the first transaction's committed
    change at the SQL level -- would still see the FIRST transaction's actor (or
    any other pre-loaded cohort member) as stale in-memory data, silently
    defeating the lock. Confirmed empirically: without this, two concurrent
    mutual demotions (each using the other as actor) both committed on real
    Postgres despite FOR UPDATE genuinely blocking at the database level.
    """
    stmt = (
        select(User)
        .where(User.role.in_(("admin", "super_admin")), User.status == "active")
        .order_by(User.id)
        .execution_options(populate_existing=True)
    )
    if session.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    return list(session.scalars(stmt))


def check_keeps_an_admin(cohort: list[User], user: User) -> None:
    """Raise LastPrivilegedUserError if excluding *user* from *cohort* (the just-
    locked active admin-tier rows from lock_active_privileged_users) would leave
    zero active admin-tier users."""
    if sum(1 for u in cohort if u.id != user.id) == 0:
        raise LastPrivilegedUserError("cannot remove the last active admin")


def check_keeps_a_super_admin(cohort: list[User], user: User) -> None:
    """Raise LastPrivilegedUserError if excluding *user* from *cohort* would leave
    zero active super_admins. A no-op when *user* isn't a super_admin."""
    if user.role == "super_admin" and sum(1 for u in cohort if u.role == "super_admin" and u.id != user.id) == 0:
        raise LastPrivilegedUserError("cannot remove the last active super_admin")


def set_user_state(session: Session, user: User, *, role: str | None = None,
                   status: str | None = None) -> User:
    """Apply a role and/or status change, keeping is_active consistent with status."""
    if role is not None:
        user.role = role
    if status is not None:
        user.status = status
        user.is_active = (status == "active")
        if status == "deleted":
            user.deleted_at = datetime.now(timezone.utc)
    session.flush()
    return user


def add_user_audit(session: Session, *, action: str, target: User | None, actor,
                   detail: str = "") -> UserAuditEvent:
    ev = UserAuditEvent(
        target_user_id=getattr(target, "id", None),
        target_email=getattr(target, "email", "") or "",
        actor_user_id=getattr(actor, "id", None),
        actor_email=getattr(actor, "email", "") or "",
        action=action, detail=detail,
    )
    session.add(ev)
    return ev


def list_user_audit(session: Session, *, limit: int = 100,
                    target_user_id: int | None = None) -> list[UserAuditEvent]:
    stmt = select(UserAuditEvent)
    if target_user_id is not None:
        stmt = stmt.where(UserAuditEvent.target_user_id == target_user_id)
    return list(session.scalars(stmt.order_by(UserAuditEvent.created_at.desc()).limit(limit)))


def bootstrap_super_admin_used(session: Session) -> bool:
    """Has the one-time initial administrator bootstrap ever fired? Not used to gate
    it anymore — services.login_with_microsoft's bootstrap path is naturally
    idempotent (it only fires when no User row exists yet for that email at all) —
    kept as a simple historical/reporting signal."""
    return session.scalar(
        select(func.count()).select_from(UserAuditEvent)
        .where(UserAuditEvent.action == "super_admin_bootstrap")
    ) > 0


def touch_last_seen(session: Session, user: User, *, throttle_seconds: int = 300) -> None:
    """Stamp last_seen_at, throttled so it's not a write on every request."""
    now = datetime.now(timezone.utc)
    last = user.last_seen_at
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    if last is None or (now - last).total_seconds() >= throttle_seconds:
        user.last_seen_at = now
        session.commit()


def users_by_id(session: Session, ids: list[int]) -> dict[int, User]:
    if not ids:
        return {}
    return {u.id: u for u in session.scalars(select(User).where(User.id.in_(ids)))}


# -------------------------------------------------------------- assignments
def get_assignment(session: Session, assignment_id: int) -> LeadAssignment | None:
    return session.get(LeadAssignment, assignment_id)


def find_assignment(session: Session, company_domain: str, user_id: int) -> LeadAssignment | None:
    return session.scalar(
        select(LeadAssignment).where(
            LeadAssignment.company_domain == company_domain, LeadAssignment.user_id == user_id
        )
    )


def create_or_update_assignment(
    session: Session, *, company_domain: str, user_id: int, assigned_by: int | None,
    status: str = "assigned", note: str = "",
) -> tuple[LeadAssignment, bool]:
    existing = find_assignment(session, company_domain, user_id)
    if existing is not None:
        if status:
            existing.status = status
        if note:
            existing.note = note
        session.flush()
        return existing, False
    assignment = LeadAssignment(
        company_domain=company_domain, user_id=user_id, assigned_by=assigned_by,
        status=status or "assigned", note=note or "",
    )
    session.add(assignment)
    session.flush()
    return assignment, True


def delete_assignment(session: Session, assignment: LeadAssignment) -> None:
    session.delete(assignment)
    session.flush()


def list_assignments(session: Session, *, user_id: int | None = None, status: str | None = None):
    stmt = (
        select(LeadAssignment, Company, LeadScore, User)
        .join(Company, Company.company_domain == LeadAssignment.company_domain)
        .outerjoin(LeadScore, LeadScore.company_domain == LeadAssignment.company_domain)
        .join(User, User.id == LeadAssignment.user_id)
    )
    if user_id is not None:
        stmt = stmt.where(LeadAssignment.user_id == user_id)
    if status:
        stmt = stmt.where(LeadAssignment.status == status)
    return session.execute(stmt.order_by(LeadAssignment.updated_at.desc())).all()


def log_assignment_event(
    session: Session, *, company_domain: str, actor_user_id: int | None, action: str,
    assignment_id: int | None = None, from_value: str = "", to_value: str = "", detail: str = "",
) -> LeadAssignmentEvent:
    event = LeadAssignmentEvent(
        company_domain=company_domain, actor_user_id=actor_user_id, action=action,
        assignment_id=assignment_id, from_value=from_value, to_value=to_value, detail=detail,
    )
    session.add(event)
    session.flush()
    return event


def assignment_events_for(session: Session, company_domain: str) -> list[LeadAssignmentEvent]:
    return list(session.scalars(
        select(LeadAssignmentEvent)
        .where(LeadAssignmentEvent.company_domain == company_domain)
        .order_by(LeadAssignmentEvent.created_at.desc())
    ))


def workload(session: Session):
    """(rows of (user_id, email, full_name, role, status, count), unassigned_high_grade)."""
    rows = session.execute(
        select(LeadAssignment.user_id, User.email, User.full_name, User.role,
               LeadAssignment.status, func.count())
        .join(User, User.id == LeadAssignment.user_id)
        .group_by(LeadAssignment.user_id, User.email, User.full_name, User.role, LeadAssignment.status)
    ).all()
    assigned = select(LeadAssignment.company_domain.distinct())
    unassigned_high = session.scalar(
        select(func.count()).select_from(LeadScore)
        .where(LeadScore.grade.in_(("A+", "A", "B")), LeadScore.company_domain.not_in(assigned))
    ) or 0
    return rows, unassigned_high


# ------------------------------------------------------------- company notes
def list_company_notes(session: Session, company_domain: str) -> list[CompanyNote]:
    return list(session.scalars(
        select(CompanyNote).where(CompanyNote.company_domain == company_domain)
        .order_by(CompanyNote.created_at.desc())
    ))


def add_company_note(
    session: Session, *, company_domain: str, author_user_id: int | None, author_email: str, body: str
) -> CompanyNote:
    note = CompanyNote(
        company_domain=company_domain, author_user_id=author_user_id,
        author_email=author_email, body=body,
    )
    session.add(note)
    session.commit()
    return note


def lead_score_for(session: Session, company_domain: str) -> LeadScore | None:
    return session.get(LeadScore, company_domain)


# ----------------------------------------------- human lead review (P-task viii)
def lead_review_for(session: Session, company_domain: str) -> LeadReview | None:
    return session.get(LeadReview, company_domain)


def upsert_lead_review(session: Session, *, company_domain: str, review_status: str,
                       human_notes: str, reviewed_by: int | None, reviewed_by_email: str,
                       reviewed_at=None, expires_at=None) -> LeadReview:
    review = session.get(LeadReview, company_domain)
    if review is None:
        review = LeadReview(company_domain=company_domain)
        session.add(review)
    review.review_status = review_status
    review.human_notes = human_notes
    review.reviewed_by = reviewed_by
    review.reviewed_by_email = reviewed_by_email
    review.reviewed_at = reviewed_at
    review.expires_at = expires_at
    session.flush()
    return review


def log_lead_review_event(session: Session, *, company_domain: str, actor_user_id: int | None,
                          actor_email: str, from_status: str, to_status: str, notes: str,
                          model_grade: str, model_score: float,
                          adjusted_grade: str = "", adjusted_score: float = 0.0) -> LeadReviewEvent:
    event = LeadReviewEvent(
        company_domain=company_domain, actor_user_id=actor_user_id, actor_email=actor_email,
        from_status=from_status, to_status=to_status, notes=notes,
        model_grade=model_grade, model_score=model_score,
        adjusted_grade=adjusted_grade, adjusted_score=adjusted_score,
    )
    session.add(event)
    session.flush()
    return event


def set_lead_score_adjustment(session: Session, company_domain: str, adjusted_score: float | None,
                              adjusted_grade: str, adjustment: dict | None) -> LeadScore | None:
    """Persist a single company's adjusted score/grade + rationale (the model
    lead_score/grade are left untouched). Used for the immediate one-company
    recompute on review submit."""
    ls = session.get(LeadScore, company_domain)
    if ls is None:
        return None
    ls.adjusted_score = adjusted_score
    ls.adjusted_grade = adjusted_grade
    rationale = dict(ls.rationale or {})
    if adjustment:
        rationale["adjustment"] = adjustment
    else:
        rationale.pop("adjustment", None)
    ls.rationale = rationale
    session.flush()
    return ls


def lead_review_events_for(session: Session, company_domain: str) -> list[LeadReviewEvent]:
    return list(session.scalars(
        select(LeadReviewEvent).where(LeadReviewEvent.company_domain == company_domain)
        .order_by(LeadReviewEvent.created_at.desc(), LeadReviewEvent.id.desc())
    ))


def reviewed_leads(session: Session):
    """Every human-reviewed company with its model score and override count.
    Rows of ``(LeadReview, Company, LeadScore | None, override_count)`` — the
    raw material the service turns into the review reports (§7)."""
    counts = (
        select(LeadReviewEvent.company_domain.label("dom"), func.count().label("n"))
        .group_by(LeadReviewEvent.company_domain)
    ).subquery()
    stmt = (
        select(LeadReview, Company, LeadScore, func.coalesce(counts.c.n, 0))
        .join(Company, Company.company_domain == LeadReview.company_domain)
        .outerjoin(LeadScore, LeadScore.company_domain == LeadReview.company_domain)
        .outerjoin(counts, counts.c.dom == LeadReview.company_domain)
    )
    return session.execute(stmt).all()


def review_status_distribution(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(LeadReview.review_status, func.count()).group_by(LeadReview.review_status)
    ).all()
    return {status: n for status, n in rows}


def pipeline_status(session: Session) -> dict:
    """Freshness: last full-pipeline completion (= last successful `scoring` run) +
    whether the latest run failed / is genuinely in progress."""
    latest = session.scalar(select(PipelineRun).order_by(PipelineRun.run_id.desc()))
    running_rows = list(session.scalars(select(PipelineRun).where(PipelineRun.status == "running")))
    now = datetime.now(timezone.utc)

    def _age_seconds(dt) -> float:
        if dt is None:
            return float("inf")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).total_seconds()

    in_progress = any(_age_seconds(r.started_at) < _RUNNING_STALE_SECONDS for r in running_rows)
    return {
        "last_successful_refresh": last_successful_refresh(session),
        "latest_run_status": latest.status if latest else "none",
        "latest_run_component": latest.component if latest else None,
        "in_progress": in_progress,
    }
