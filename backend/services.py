"""Service layer: business logic between routers and repositories.

Assembles the unified company profile, builds analytics, and maps ORM objects to
Pydantic schemas. Routers call only this module; this module calls only
repositories.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend import dm_intelligence as dmi
from backend import relationship_intelligence as reli
from backend import repositories as repo
from backend import security
from backend import workflow_service
from backend.config import Settings
from backend.dependencies import Pagination
from config.enums import ASSIGNMENT_STATUSES, LEAD_REVIEW_STATUSES, USER_ROLES, USER_STATUSES
from lead_scoring.config import ScoringConfig
from lead_scoring.human_review import adjusted_score, disagreement
from backend.schemas import (
    AnalyticsCoverage,
    AnalyticsSummary,
    AuthResult,
    CompanyProfile,
    CompanySummary,
    CompanyOut,
    ContactIn,
    ContactOut,
    CompanyContactsOut,
    ContactGroupOut,
    DecisionMakerCompanies,
    DecisionMakerCompany,
    DecisionMakerDetailOut,
    HierarchyLevelOut,
    RankedContactOut,
    DecisionMakerNoteIn,
    DecisionMakerNoteOut,
    DecisionMakerNoteUpdate,
    DecisionMakerOut,
    DemandSignalOut,
    EngagementOut,
    JobOut,
    LeadOut,
    LeadReviewIn,
    LeadReviewOut,
    LeadReviewEventOut,
    LeadScoreOut,
    LeadershipSignalOut,
    OpportunityOut,
    Page,
    PipelineComponentHealth,
    PipelineRunOut,
    PipelineStatusOut,
    ReviewAdjustmentStats,
    ReviewReportRow,
    ReviewReports,
    ReviewStatusOut,
    UserAuditOut,
    UserOut,
    UserPatch,
    AssignmentCreate,
    AssignmentPatch,
    AssignmentOut,
    AssignmentEventOut,
    WorkloadEntry,
    WorkloadOut,
    CompanyNoteIn,
    CompanyNoteOut,
    ActivityItem,
)


def _company_summary(company, lead) -> CompanySummary:
    summary = CompanySummary.model_validate(company)
    if lead is not None:
        summary.lead_score = lead.lead_score
        summary.grade = lead.grade
    return summary


def _lead_out(lead, company, review=None) -> LeadOut:
    human_status = review.review_status if review is not None else None
    # adjusted_* fall back to the model values when no adjustment was computed.
    adj = lead.adjusted_score if lead.adjusted_score is not None else lead.lead_score
    adj_grade = lead.adjusted_grade or lead.grade
    return LeadOut(
        company_domain=lead.company_domain,
        company_name=getattr(company, "company_name", ""),
        company_tier=getattr(company, "company_tier", ""),
        prospect_type=getattr(company, "prospect_type", ""),
        compliance_flag=getattr(company, "compliance_flag", ""),
        lead_score=lead.lead_score, grade=lead.grade, priority_rank=lead.priority_rank,
        opportunity_subscore=lead.opportunity_subscore, demand_subscore=lead.demand_subscore,
        readiness_subscore=lead.readiness_subscore, dm_subscore=lead.dm_subscore,
        coverage=lead.coverage, confidence=lead.confidence,
        human_status=human_status,
        adjusted_score=adj, adjusted_grade=adj_grade, combined_priority=adj,
    )


def list_companies(session: Session, *, pagination: Pagination, q, domain, tier,
                   prospect_type, grade, sort, order) -> Page[CompanySummary]:
    rows, total = repo.list_companies(
        session, q=q, domain=domain, tier=tier, prospect_type=prospect_type, grade=grade,
        sort=sort, order=order, limit=pagination.limit, offset=pagination.offset,
    )
    items = [_company_summary(c, l) for c, l in rows]
    return Page.build(items, total, pagination.page, pagination.page_size)


def get_company_profile(session: Session, domain: str) -> CompanyProfile:
    company = repo.get_company(session, domain)
    if company is None:
        raise HTTPException(status_code=404, detail=f"company '{domain}' not found")

    opportunities = repo.opportunities_for(session, domain)
    jobs = repo.jobs_for(session, domain)
    demand = repo.demand_for(session, domain)
    dms = repo.decision_makers_for(session, domain)
    ldr = repo.leadership_signals_for(session, domain)
    eng = repo.engagement_for(session, domain)
    lead = repo.lead_for(session, domain)
    review_items = repo.review_items_for(session, domain)
    human_review = repo.lead_review_for(session, domain)
    review_history = repo.lead_review_events_for(session, domain)

    review = ReviewStatusOut(
        is_stub=company.is_stub,
        validation_status=company.validation_status,
        pending_review_items=len(review_items),
        match_types=sorted({i.match_type for i in review_items}),
    )
    counts = {
        "opportunities": len(opportunities),
        "jobs": len(jobs),
        "decision_makers": len(dms),
        "demand_signal": 1 if demand is not None else 0,
        "leadership_signals": len(ldr),
        "review_events": len(review_history),
    }
    return CompanyProfile(
        company=CompanyOut.model_validate(company),
        lead_score=LeadScoreOut.model_validate(lead) if lead is not None else None,
        review_status=review,
        counts=counts,
        opportunities=[OpportunityOut.model_validate(o) for o in opportunities],
        jobs=[JobOut.model_validate(j) for j in jobs],
        demand_signal=DemandSignalOut.model_validate(demand) if demand is not None else None,
        decision_makers=_dm_outs_for_company(session, company.company_domain, dms),
        leadership_signals=[LeadershipSignalOut.model_validate(x) for x in ldr],
        engagement=EngagementOut.model_validate(eng) if eng is not None else None,
        lead_review=LeadReviewOut.model_validate(human_review) if human_review is not None else None,
        lead_review_history=[LeadReviewEventOut.model_validate(e) for e in review_history],
        review_feedback_enabled=review_scoring_config().review_feedback_enabled,
    )


def list_leads(session: Session, *, pagination: Pagination, grade, tier, prospect_type,
               sort="model") -> Page[LeadOut]:
    rows, total = repo.list_leads(
        session, grade=grade, tier=tier, prospect_type=prospect_type, sort=sort,
        limit=pagination.limit, offset=pagination.offset,
    )
    items = [_lead_out(lead, company, review) for lead, company, review in rows]
    return Page.build(items, total, pagination.page, pagination.page_size)


def list_opportunities(session: Session, *, pagination: Pagination, opportunity_type,
                       company_domain, date_from, date_to, annual_lists_only=False,
                       company_news_only=False, lifecycle_status=None,
                       hide_archived=False, sort=None) -> Page[OpportunityOut]:
    rows, total = repo.list_opportunities(
        session, opportunity_type=opportunity_type, company_domain=company_domain,
        date_from=date_from, date_to=date_to, annual_lists_only=annual_lists_only,
        company_news_only=company_news_only, lifecycle_status=lifecycle_status,
        hide_archived=hide_archived, sort=sort, limit=pagination.limit, offset=pagination.offset,
    )
    items = [OpportunityOut.model_validate(o) for o in rows]
    return Page.build(items, total, pagination.page, pagination.page_size)


def list_demand_signals(session: Session, *, pagination: Pagination,
                        min_demand_score, technology_focus) -> Page[DemandSignalOut]:
    rows, total = repo.list_demand_signals(
        session, min_demand_score=min_demand_score, technology_focus=technology_focus,
        limit=pagination.limit, offset=pagination.offset,
    )
    items = [DemandSignalOut.model_validate(d) for d in rows]
    return Page.build(items, total, pagination.page, pagination.page_size)


def list_leadership_signals(session: Session, *, pagination: Pagination, company_domain,
                            movement_type, seniority_band, source) -> Page[LeadershipSignalOut]:
    rows, total = repo.list_leadership_signals(
        session, company_domain=company_domain, movement_type=movement_type,
        seniority_band=seniority_band, source=source, limit=pagination.limit, offset=pagination.offset,
    )
    items = [LeadershipSignalOut.model_validate(x) for x in rows]
    return Page.build(items, total, pagination.page, pagination.page_size)


# ---------------------------------------------- decision-maker intelligence (Phase 2)
def _apply_intel(out: DecisionMakerOut, intel: dmi.DmIntel) -> DecisionMakerOut:
    """Attach the computed decision-intelligence fields to a DecisionMakerOut/Detail."""
    out.department_class = intel.department
    out.department_group = intel.department_group
    out.exec_level = intel.exec_level
    out.influence_score = intel.influence_score
    out.confidence_score = intel.confidence_score
    out.confidence_level = intel.confidence_level
    return out


def _dm_out(dm, ctx: dmi.CompanyContext) -> DecisionMakerOut:
    return _apply_intel(DecisionMakerOut.model_validate(dm), dmi.compute(dm, ctx))


def _dm_outs_for_company(session: Session, domain, dms) -> list[DecisionMakerOut]:
    """DecisionMakerOut list for a single company (one shared context — no N+1)."""
    ctx = dmi.context_for(session, domain)
    return [_dm_out(d, ctx) for d in dms]


def _dm_leadership(session: Session, dm) -> list[LeadershipSignalOut]:
    """Leadership signals for this person, then recent company-level signals (deduped)."""
    sigs = list(repo.leadership_for_dm(session, dm.id))
    seen = {s.signal_id for s in sigs}
    if dm.company_domain:
        for s in repo.leadership_signals_for(session, dm.company_domain):
            if s.signal_id not in seen:
                sigs.append(s)
                seen.add(s.signal_id)
    return [LeadershipSignalOut.model_validate(s) for s in sigs[:8]]


def list_decision_makers(session: Session, *, pagination: Pagination,
                        company_domain, seniority, senior=False) -> Page[DecisionMakerOut]:
    rows, total = repo.list_decision_makers(
        session, company_domain=company_domain, seniority=seniority, senior=senior,
        limit=pagination.limit, offset=pagination.offset,
    )
    # Batch the company contexts for the whole page (avoids per-row N+1).
    ctxs = dmi.build_company_contexts(session, [d.company_domain for d in rows])
    items = [_dm_out(d, ctxs.get(d.company_domain) or dmi.CompanyContext(domain=d.company_domain or ""))
             for d in rows]
    return Page.build(items, total, pagination.page, pagination.page_size)


def company_contacts(session: Session, domain: str) -> CompanyContactsOut:
    """Decision-intelligence view of a company's contacts: ranked recommendations
    (primary/secondary/alternate + reasons), the auto-grouped Company Contact Map,
    and the inferred organisation hierarchy. One shared company context (no N+1)."""
    company = repo.get_company(session, domain)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    dms = repo.decision_makers_for(session, domain)
    ctx = dmi.context_for(session, domain)
    ranked = dmi.rank_contacts(dms, ctx)
    outs: dict[int, RankedContactOut] = {}
    for rc in ranked:
        contact = _apply_intel(DecisionMakerOut.model_validate(rc.dm), rc.intel)
        outs[rc.dm.id] = RankedContactOut(rank=rc.rank, ranking_score=rc.ranking_score,
                                          reasons=rc.reasons, contact=contact)
    recommended = [outs[rc.dm.id] for rc in ranked[:3] if rc.rank]
    group_map: dict[str, list[RankedContactOut]] = {}
    for rc in ranked:
        group_map.setdefault(rc.intel.department_group, []).append(outs[rc.dm.id])
    groups = [ContactGroupOut(group=g, contacts=group_map[g])
              for g in dmi.CONTACT_GROUPS if group_map.get(g)]
    level_map: dict[int, list[RankedContactOut]] = {}
    for rc in ranked:
        level_map.setdefault(rc.intel.hierarchy_rank, []).append(outs[rc.dm.id])
    hierarchy = [HierarchyLevelOut(rank=r, level=dmi.rank_label(r), contacts=level_map[r])
                 for r in sorted(level_map)]
    return CompanyContactsOut(company_domain=domain, company_name=company.company_name or domain,
                              total=len(dms), recommended=recommended, groups=groups, hierarchy=hierarchy)


def decision_maker_companies(session: Session) -> DecisionMakerCompanies:
    rows, unresolved = repo.decision_maker_companies(session)
    return DecisionMakerCompanies(
        companies=[
            DecisionMakerCompany(company_domain=d, company_name=name or d, total=n, senior=int(senior or 0))
            for d, name, n, senior in rows
        ],
        unresolved=unresolved,
    )


def _dm_source_contact(dm) -> tuple[str, str]:
    """The engine-sourced (Apify) work email/phone for a decision maker.

    Reads the structured columns first; profile_data is a defensive fallback for rows
    ingested before those columns existed. These are the ORIGINAL values — never
    overwritten by an analyst save (that goes to decision_maker_contacts).
    """
    pd = dm.profile_data or {}
    email = (dm.work_email or pd.get("email") or "").strip()
    phone = (dm.work_phone or pd.get("phone") or "").strip()
    return email, phone


def _enrich_contact(dm, contact) -> ContactOut | None:
    """Build a ContactOut that merges the saved analyst row (if any) over the engine
    source, flags per-field overrides, and always carries the original source values.

    Effective value = saved value if present, else the engine value (so we surface
    Apify data without manual entry). ``email_overridden`` is True only when an analyst
    saved a value that differs from the engine's original.
    """
    src_email, src_phone = _dm_source_contact(dm)
    if contact is None:
        if not (src_email or src_phone):
            return None
        return ContactOut(
            id=0, decision_maker_id=dm.id, work_email=src_email, work_phone=src_phone,
            from_source=True, source_work_email=src_email, source_work_phone=src_phone,
        )
    saved_email = (contact.work_email or "").strip()
    saved_phone = (contact.work_phone or "").strip()
    out = ContactOut.model_validate(contact)
    out.work_email = saved_email or src_email      # fall back to source when blank
    out.work_phone = saved_phone or src_phone
    out.source_work_email = src_email
    out.source_work_phone = src_phone
    out.email_overridden = bool(saved_email and src_email and saved_email != src_email)
    out.phone_overridden = bool(saved_phone and src_phone and saved_phone != src_phone)
    # from_source: the effective value is still purely the engine's (no real override)
    out.from_source = not (out.email_overridden or out.phone_overridden or
                           (saved_email and not src_email) or (saved_phone and not src_phone))
    return out


def get_dm_contact(session: Session, dm_id: int) -> ContactOut | None:
    dm = repo.get_decision_maker(session, dm_id)
    if dm is None:
        raise HTTPException(status_code=404, detail="decision maker not found")
    return _enrich_contact(dm, repo.get_dm_contact(session, dm_id))


def put_dm_contact(session: Session, dm_id: int, payload: ContactIn, actor) -> ContactOut:
    dm = repo.get_decision_maker(session, dm_id)
    if dm is None:
        raise HTTPException(status_code=404, detail="decision maker not found")
    contact = repo.upsert_dm_contact(
        session, dm_id=dm_id, added_by=actor.id, added_by_email=actor.email,
        work_email=(payload.work_email or "").strip(),
        work_phone=(payload.work_phone or "").strip(),
        notes=(payload.notes or "").strip(),
    )
    return _enrich_contact(dm, contact)


def get_decision_maker_detail(session: Session, dm_id: int) -> DecisionMakerDetailOut:
    """Full enrichment view for one decision maker (lazy-loaded by the profile
    panel). The heavier fields (summary, skills, languages, followers, …) plus the
    Phase 2 decision intelligence (influence/confidence/department/hierarchy +
    integrated leadership signals) live here, NOT on the list payload."""
    dm = repo.get_decision_maker(session, dm_id)
    if dm is None:
        raise HTTPException(status_code=404, detail="decision maker not found")
    ctx = dmi.context_for(session, dm.company_domain)
    intel = dmi.compute(dm, ctx)
    out = _apply_intel(DecisionMakerDetailOut.model_validate(dm), intel)
    out.influence_raw = intel.influence_raw
    out.hierarchy_rank = intel.hierarchy_rank
    out.engineering_relevance = intel.engineering_relevance
    out.influence_factors = intel.influence_factors
    out.confidence_factors = intel.confidence_factors
    out.leadership_signals = _dm_leadership(session, dm)
    # Phase 3 relationship intelligence (per contact).
    rel = reli.contact_relationship(session, dm)
    out.relationship_status = rel["status"]
    out.relationship_score = rel["score"]
    out.next_action = rel["action"]
    out.follow_up = rel["follow_up"]
    out.risk_severity = rel["risk_severity"]
    out.risk_flags = rel["risk_flags"]
    return out


# ----------------------------------------------- decision-maker notes (4 tiers)
def _is_admin(user) -> bool:
    return getattr(user, "role", None) == "admin"


def _is_manager(user) -> bool:
    return getattr(user, "role", None) in ("admin", "manager")


def _is_author(note, user) -> bool:
    return note.created_by is not None and note.created_by == getattr(user, "id", None)


def _can_create_note(note_type: str, user) -> bool:
    """admin → admins only; manager → admin/manager; team & personal → any user."""
    if note_type == "admin":
        return _is_admin(user)
    if note_type == "manager":
        return _is_manager(user)
    return True


def _note_role_required(note_type: str) -> str:
    return "admin" if note_type == "admin" else "admin or manager"


def _can_edit_note(note, user) -> bool:
    """The author may always edit/delete their own. Otherwise: admin notes →
    admin-tier; manager/team notes → manager-tier; personal notes → nobody else."""
    if _is_author(note, user):
        return True
    if note.note_type == "admin":
        return _is_admin(user)
    if note.note_type in ("manager", "team"):
        return _is_manager(user)
    return False  # another user's personal note


def _note_out(note, user, *, role_by_id: dict[int, str] | None = None) -> DecisionMakerNoteOut:
    out = DecisionMakerNoteOut.model_validate(note)
    out.can_edit = _can_edit_note(note, user)
    if role_by_id is not None:
        out.author_role = role_by_id.get(note.created_by, "")
    elif _is_author(note, user):
        out.author_role = getattr(user, "role", "") or ""
    return out


def list_dm_notes(session: Session, dm_id: int, viewer) -> list[DecisionMakerNoteOut]:
    """Shared notes (admin/manager/team) + the viewer's own personal notes, ordered
    admin → manager → team → personal."""
    if repo.get_decision_maker(session, dm_id) is None:
        raise HTTPException(status_code=404, detail="decision maker not found")
    notes = repo.list_dm_notes(session, dm_id, viewer_id=getattr(viewer, "id", None))
    roles = repo.roles_for_users(session, [n.created_by for n in notes])
    return [_note_out(n, viewer, role_by_id=roles) for n in notes]


def create_dm_note(session: Session, dm_id: int, payload: DecisionMakerNoteIn, actor) -> DecisionMakerNoteOut:
    if repo.get_decision_maker(session, dm_id) is None:
        raise HTTPException(status_code=404, detail="decision maker not found")
    if not _can_create_note(payload.note_type, actor):
        raise HTTPException(status_code=403,
                            detail=f"{payload.note_type} notes require the {_note_role_required(payload.note_type)} role")
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="note content cannot be empty")
    note = repo.create_dm_note(
        session, dm_id=dm_id, note_type=payload.note_type,
        created_by=getattr(actor, "id", None), author_email=getattr(actor, "email", ""),
        content=content,
    )
    return _note_out(note, actor)


def _load_editable_note(session: Session, dm_id: int, note_id: int, actor):
    note = repo.get_dm_note(session, note_id)
    if note is None or note.decision_maker_id != dm_id:
        raise HTTPException(status_code=404, detail="note not found")
    if not _can_edit_note(note, actor):
        # Don't reveal another user's personal note exists — 404, not 403.
        if note.note_type == "personal":
            raise HTTPException(status_code=404, detail="note not found")
        raise HTTPException(status_code=403,
                            detail=f"{note.note_type} notes require the {_note_role_required(note.note_type)} role")
    return note


def update_dm_note(session: Session, dm_id: int, note_id: int,
                   payload: DecisionMakerNoteUpdate, actor) -> DecisionMakerNoteOut:
    note = _load_editable_note(session, dm_id, note_id, actor)
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="note content cannot be empty")
    note = repo.update_dm_note(session, note, content=content)
    return _note_out(note, actor)


def delete_dm_note(session: Session, dm_id: int, note_id: int, actor) -> None:
    note = _load_editable_note(session, dm_id, note_id, actor)
    repo.delete_dm_note(session, note)


def analytics_summary(session: Session) -> AnalyticsSummary:
    counts = repo.table_counts(session)
    grades = repo.grade_distribution(session)
    top = [_lead_out(lead, company) for lead, company in repo.top_leads(session, 10)]
    return AnalyticsSummary(
        total_companies=counts["companies"],
        total_opportunities=counts["opportunities"],
        total_jobs=counts["jobs"],
        total_demand_signals=counts["demand_signals"],
        total_decision_makers=counts["decision_makers"],
        total_leads=counts["leads"],
        grade_distribution=grades,
        top_companies=top,
    )


def analytics_coverage(session: Session) -> AnalyticsCoverage:
    return AnalyticsCoverage(**repo.coverage(session))


def pipeline_runs(session: Session, limit: int) -> list[PipelineRunOut]:
    return [PipelineRunOut.model_validate(r) for r in repo.recent_pipeline_runs(session, limit)]


def pipeline_health(session: Session) -> list[PipelineComponentHealth]:
    return [PipelineComponentHealth(**h) for h in repo.pipeline_health(session)]


def pipeline_status(session: Session) -> PipelineStatusOut:
    return PipelineStatusOut(**repo.pipeline_status(session))


# ------------------------------------------------------------------- auth
def _lifecycle_error(code: str, message: str, *, status_code: int = 403) -> HTTPException:
    """A structured `detail` (`{code, message}`) instead of a bare string, so the
    frontend can switch on `code` (stable) rather than parse `message` (prose, can
    reword). `ApiError.detail` in the frontend client already carries this through
    untouched; existing tests that substring-match `detail["message"]` keep working."""
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def login_with_microsoft(session: Session, id_token: str, settings: Settings) -> AuthResult:
    """Verify a Microsoft Entra ID token (security.verify_microsoft_id_token) and, if
    the mapped account is active, mint the app's session JWT.

    First sign-in for an unseen email creates a PENDING account (mirroring the old
    register_user) unless the email matches SP_BOOTSTRAP_ADMIN_EMAIL (one-time initial
    super_admin handoff — active immediately, no password/change-password step needed
    since there's no password) or SP_ADMIN_EMAILS (active admin immediately). Once that
    User row exists, later sign-ins never touch its role again — a deliberate later
    demotion by another admin can't be silently reversed just by signing in again.

    An existing account is gated on status exactly like the prior password mechanism:
    pending/rejected/deleted/disabled all deny with the same structured errors the
    frontend already renders; only active grants a token."""
    try:
        claims = security.verify_microsoft_id_token(id_token, settings)
    except Exception:
        raise _lifecycle_error("invalid_microsoft_token", "Could not verify Microsoft sign-in.", status_code=401)

    email = (claims.get("email") or claims.get("preferred_username") or "").lower().strip()
    oid = str(claims.get("oid") or claims.get("sub") or "").strip()
    name = str(claims.get("name") or "").strip()
    if not email:
        raise _lifecycle_error("invalid_microsoft_token", "Microsoft account has no email claim.", status_code=401)

    domain = settings.allowed_email_domain.lower().strip()
    if domain and not email.endswith("@" + domain):
        raise _lifecycle_error("forbidden_domain", f"only @{domain} accounts may sign in")

    user = repo.get_user_by_microsoft_oid(session, oid) if oid else None
    if user is None:
        user = repo.get_user_by_email(session, email)

    if user is None:
        is_bootstrap = bool(email == (settings.bootstrap_admin_email or "").strip().lower())
        is_admin_email = email in settings.admin_emails
        role = "super_admin" if is_bootstrap else ("admin" if is_admin_email else "member")
        account_status = "active" if (is_bootstrap or is_admin_email) else "pending"
        try:
            user = repo.create_user(
                session, email=email, full_name=name, role=role, status=account_status,
                microsoft_oid=oid or None,
            )
            repo.add_user_audit(
                session, action="super_admin_bootstrap" if is_bootstrap else "registered",
                target=user, actor=user,
                detail="initial administrator bootstrap via SP_BOOTSTRAP_ADMIN_EMAIL" if is_bootstrap
                else "first Microsoft sign-in",
            )
            session.commit()
        except IntegrityError:
            session.rollback()  # a concurrent first sign-in for the same email won the race
            user = repo.get_user_by_email(session, email)
    elif oid and not user.microsoft_oid:
        repo.set_user_microsoft_oid(session, user, oid)
        session.commit()

    if user.status == "pending":
        raise _lifecycle_error("account_pending", "Your account is pending admin approval.")
    if user.status == "rejected":
        repo.add_user_audit(session, action="denied", target=user, actor=user,
                            detail="rejected account attempted Microsoft sign-in")
        session.commit()
        raise _lifecycle_error("account_rejected", "Your access request was declined.")
    if user.status == "deleted":
        raise _lifecycle_error("account_deleted", "This account no longer exists.")
    if user.status == "disabled" or not user.is_active:
        repo.add_user_audit(session, action="denied", target=user, actor=user,
                            detail="disabled account attempted Microsoft sign-in")
        session.commit()
        raise _lifecycle_error("account_disabled", "This account has been disabled.")

    repo.touch_login(session, user, full_name=name or None)
    repo.add_user_audit(session, action="login", target=user, actor=user)
    session.commit()
    return AuthResult(token=security.issue_app_token(user, settings), user=UserOut.model_validate(user))


def refresh_session(session: Session, user: User, settings: Settings) -> AuthResult:
    """Session refresh: re-validates the account is still active and mints a fresh app
    JWT with a new expiry. The caller already authenticated via get_current_user, which
    re-reads the User row on every call — so a disabled/deleted account is rejected there
    before this ever runs."""
    repo.add_user_audit(session, action="session_refreshed", target=user, actor=user)
    session.commit()
    return AuthResult(token=security.issue_app_token(user, settings), user=UserOut.model_validate(user))


def logout(session: Session, user: User) -> dict:
    """App JWTs are stateless (no server-side session store), so logout is audit-only —
    the client discards its token. Matches the existing Bearer-token design; a
    server-side blacklist would need a shared store (Redis) to work across instances,
    which isn't part of this platform's infra."""
    repo.add_user_audit(session, action="logout", target=user, actor=user)
    session.commit()
    return {"status": "ok"}


# =============================================================== admin: users
def list_users(
    session: Session, *, status: str | None = None, q: str | None = None,
    limit: int = 50, offset: int = 0,
) -> Page:
    if status is not None and status not in USER_STATUSES:
        raise HTTPException(status_code=422, detail=f"invalid status; use {', '.join(USER_STATUSES)}")
    rows, total = repo.list_users(session, status=status, q=q, limit=limit, offset=offset)
    items = [UserOut.model_validate(u) for u in rows]
    return Page.build(items, total, (offset // limit + 1) if limit else 1, limit)


def list_user_audit(session: Session, *, limit: int = 100, user_id: int | None = None) -> list[UserAuditOut]:
    return [UserAuditOut.model_validate(e)
            for e in repo.list_user_audit(session, limit=limit, target_user_id=user_id)]


def _get_target(session: Session, user_id: int):
    user = repo.get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return user


def _guard_not_self(actor, user, action: str) -> None:
    if getattr(actor, "id", None) == user.id:
        raise HTTPException(status_code=400, detail=f"you cannot {action} your own account")


def _guard_keeps_an_admin(cohort: list[User] | None, user) -> None:
    """Block an action that would drop the *last* active admin-tier (admin or
    super_admin) user (lockout protection). *cohort* is the just-locked active
    admin-tier rows from repo.lock_active_privileged_users (F1: the invariant is
    always evaluated against that freshly-locked state, never a pre-lock count),
    or None when the caller already determined this action can't affect the
    invariant (no lock was taken)."""
    if cohort is None:
        return
    try:
        repo.check_keeps_an_admin(cohort, user)
    except repo.LastPrivilegedUserError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _guard_keeps_a_super_admin(cohort: list[User] | None, user) -> None:
    """Block an action that would drop the *last* active super_admin — a narrower,
    additional protection on top of _guard_keeps_an_admin (which treats admin and
    super_admin as one interchangeable tier). *cohort* as above."""
    if cohort is None:
        return
    try:
        repo.check_keeps_a_super_admin(cohort, user)
    except repo.LastPrivilegedUserError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _deny(session: Session, *, actor, target, detail: str) -> None:
    """Audit a blocked security-sensitive action, then raise 403. The caller's own
    mutation never ran, so the audit row is the only thing to commit — but the denial
    itself must still be durable, not lost with the rejected request."""
    repo.add_user_audit(session, action="denied", target=target, actor=actor, detail=detail)
    session.commit()
    raise HTTPException(status_code=403, detail=detail)


def _guard_super_admin_tier(session: Session, actor, user, new_role: str | None = None) -> None:
    """Only a super_admin may (a) change another super_admin's role/active-state, or
    (b) grant super_admin to anyone. (Self-promotion is separately always denied —
    see the self-guard in set_user_role — regardless of the actor's current tier.)"""
    if user.role == "super_admin" and actor.role != "super_admin":
        _deny(session, actor=actor, target=user,
              detail="only a super_admin may modify a super_admin account")
    if new_role == "super_admin" and actor.role != "super_admin":
        _deny(session, actor=actor, target=user,
              detail="only a super_admin may grant the super_admin role")


def approve_user(session: Session, user_id: int, actor) -> UserOut:
    user = _get_target(session, user_id)
    if user.status not in ("pending", "rejected"):
        raise HTTPException(status_code=409, detail=f"account is already {user.status}")
    repo.set_user_state(session, user, status="active")
    repo.add_user_audit(session, action="approved", target=user, actor=actor)
    session.commit()
    return UserOut.model_validate(user)


def reject_user(session: Session, user_id: int, actor) -> UserOut:
    user = _get_target(session, user_id)
    _guard_not_self(actor, user, "reject")
    if user.status != "pending":
        raise HTTPException(status_code=409, detail="only a pending account can be rejected")
    repo.set_user_state(session, user, status="rejected")
    repo.add_user_audit(session, action="rejected", target=user, actor=actor)
    session.commit()
    return UserOut.model_validate(user)


def set_user_active(session: Session, user_id: int, active: bool, actor) -> UserOut:
    user = _get_target(session, user_id)
    if user.status == "deleted":
        raise HTTPException(status_code=409, detail="account is deleted")
    if not active:
        _guard_not_self(actor, user, "disable")
        _guard_super_admin_tier(session, actor, user)
        # F1: lock only when this user is currently active admin-tier -- disabling
        # anyone else can never affect either invariant, so no lock is taken.
        cohort = repo.lock_active_privileged_users(session) if repo.is_active_privileged(user) else None
        _guard_keeps_an_admin(cohort, user)
        _guard_keeps_a_super_admin(cohort, user)
    repo.set_user_state(session, user, status="active" if active else "disabled")
    repo.add_user_audit(session, action="enabled" if active else "disabled",
                        target=user, actor=actor)
    session.commit()
    return UserOut.model_validate(user)


def set_user_role(session: Session, user_id: int, role: str, actor) -> UserOut:
    if role not in USER_ROLES:
        raise HTTPException(status_code=422, detail=f"invalid role; use {', '.join(USER_ROLES)}")
    user = _get_target(session, user_id)
    if user.status == "deleted":
        raise HTTPException(status_code=409, detail="account is deleted")
    _guard_not_self(actor, user, "change the role of")
    _guard_super_admin_tier(session, actor, user, new_role=role)
    # F1: lock only when THIS SPECIFIC transition could leave admin-tier (e.g.
    # super_admin -> admin does not -- the user stays admin-tier, so only the
    # narrower super_admin check, if any, applies) or leave super_admin-tier.
    leaves_admin_tier, leaves_super_admin = repo.role_change_exposure(user, role)
    cohort = (repo.lock_active_privileged_users(session)
              if (leaves_admin_tier or leaves_super_admin) else None)
    if leaves_admin_tier:
        _guard_keeps_an_admin(cohort, user)
    if leaves_super_admin:
        _guard_keeps_a_super_admin(cohort, user)
    old = user.role
    repo.set_user_state(session, user, role=role)
    repo.add_user_audit(session, action="role_changed", target=user, actor=actor,
                        detail=f"{old} → {role}")
    session.commit()
    return UserOut.model_validate(user)


def delete_user(session: Session, user_id: int, actor) -> UserOut:
    """Soft-delete: scrub PII, mark deleted, keep the row for audit/FK integrity."""
    user = _get_target(session, user_id)
    _guard_not_self(actor, user, "delete")
    _guard_super_admin_tier(session, actor, user)
    # F1: lock only when this user is currently active admin-tier -- see set_user_active.
    cohort = repo.lock_active_privileged_users(session) if repo.is_active_privileged(user) else None
    _guard_keeps_an_admin(cohort, user)
    _guard_keeps_a_super_admin(cohort, user)
    original_email = user.email
    repo.set_user_state(session, user, status="deleted")
    user.full_name = ""
    user.picture = ""
    user.email = f"deleted-user-{user.id}@deleted.invalid"   # anonymize (keeps UNIQUE)
    repo.add_user_audit(session, action="deleted", target=user, actor=actor,
                        detail=f"soft-deleted {original_email}")
    session.commit()
    return UserOut.model_validate(user)


def update_user(session: Session, user_id: int, patch: UserPatch, actor) -> UserOut:
    """Combined PATCH (role and/or enable-disable) used by the admin console."""
    user = _get_target(session, user_id)
    if patch.role is not None and patch.role != user.role:
        set_user_role(session, user_id, patch.role, actor)
    if patch.is_active is not None and patch.is_active != user.is_active:
        set_user_active(session, user_id, patch.is_active, actor)
    return UserOut.model_validate(repo.get_user(session, user_id))


# =========================================================== lead assignments
def _assignment_out(a, company, score, user, assigner=None) -> AssignmentOut:
    return AssignmentOut(
        id=a.id, company_domain=a.company_domain,
        company_name=company.company_name if company else a.company_domain,
        grade=score.grade if score else None,
        lead_score=score.lead_score if score else None,
        user_id=a.user_id, user_email=user.email if user else "",
        user_name=user.full_name if user else "",
        assigned_by=a.assigned_by,
        assigned_by_email=assigner.email if assigner else "",
        assigned_by_name=assigner.full_name if assigner else "",
        status=a.status, note=a.note,
        created_at=a.created_at, updated_at=a.updated_at,
    )


def _reload_assignment(session: Session, assignment_id: int, user_id: int) -> AssignmentOut:
    for (a, c, s, u) in repo.list_assignments(session, user_id=user_id):
        if a.id == assignment_id:
            assigner = repo.get_user(session, a.assigned_by) if a.assigned_by else None
            return _assignment_out(a, c, s, u, assigner)
    raise HTTPException(status_code=500, detail="assignment lookup failed")


def list_assignments(session: Session, *, user_id=None, status=None) -> list[AssignmentOut]:
    # Resolve each assignment's assigner (for "who left the note") once per distinct id.
    assigners: dict[int, object] = {}

    def _assigner(uid):
        if not uid:
            return None
        if uid not in assigners:
            assigners[uid] = repo.get_user(session, uid)
        return assigners[uid]

    return [_assignment_out(a, c, s, u, _assigner(a.assigned_by))
            for (a, c, s, u) in repo.list_assignments(session, user_id=user_id, status=status)]


def my_assignments(session: Session, user_id: int) -> list[AssignmentOut]:
    return list_assignments(session, user_id=user_id)


def create_assignment(session: Session, payload: AssignmentCreate, actor) -> AssignmentOut:
    if payload.status not in ASSIGNMENT_STATUSES:
        raise HTTPException(status_code=422, detail="invalid status")
    if repo.get_company(session, payload.company_domain) is None:
        raise HTTPException(status_code=404, detail="company not found")
    if repo.get_user(session, payload.user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    assignment, created = repo.create_or_update_assignment(
        session, company_domain=payload.company_domain, user_id=payload.user_id,
        assigned_by=actor.id, status=payload.status, note=payload.note,
    )
    repo.log_assignment_event(
        session, company_domain=assignment.company_domain, actor_user_id=actor.id,
        action="assigned" if created else "status_changed", assignment_id=assignment.id,
        to_value=assignment.status, detail=f"assigned to user {assignment.user_id}",
    )
    if created:
        workflow_service.fire_event(
            session, "lead_created", "lead", assignment.id,
            {"owner_id": assignment.user_id, "company_domain": assignment.company_domain,
             "status": assignment.status},
            actor=actor,
        )
    session.commit()
    return _reload_assignment(session, assignment.id, assignment.user_id)


def patch_assignment(session: Session, assignment_id: int, patch: AssignmentPatch, actor) -> AssignmentOut:
    a = repo.get_assignment(session, assignment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="assignment not found")
    # The assignee (any role) may update their own; managers/admins may update any.
    if a.user_id != actor.id and actor.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="you can only update your own assignments")
    if patch.status is not None and patch.status != a.status:
        if patch.status not in ASSIGNMENT_STATUSES:
            raise HTTPException(status_code=422, detail="invalid status")
        repo.log_assignment_event(
            session, company_domain=a.company_domain, actor_user_id=actor.id,
            action="status_changed", assignment_id=a.id, from_value=a.status, to_value=patch.status,
        )
        a.status = patch.status
    if patch.note is not None and patch.note != a.note:
        repo.log_assignment_event(
            session, company_domain=a.company_domain, actor_user_id=actor.id,
            action="note_changed", assignment_id=a.id, detail="note updated",
        )
        a.note = patch.note
    session.commit()
    return _reload_assignment(session, a.id, a.user_id)


def unassign(session: Session, assignment_id: int, actor) -> None:
    a = repo.get_assignment(session, assignment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="assignment not found")
    repo.log_assignment_event(
        session, company_domain=a.company_domain, actor_user_id=actor.id,
        action="unassigned", assignment_id=a.id, detail=f"unassigned user {a.user_id}",
    )
    repo.delete_assignment(session, a)
    session.commit()


def workload(session: Session) -> WorkloadOut:
    rows, unassigned_high = repo.workload(session)
    by_user: dict[int, WorkloadEntry] = {}
    for user_id, email, full_name, role, status, count in rows:
        entry = by_user.get(user_id)
        if entry is None:
            entry = WorkloadEntry(user_id=user_id, email=email, full_name=full_name or "", role=role)
            by_user[user_id] = entry
        entry.by_status[status] = count
        entry.total += count
    return WorkloadOut(
        users=sorted(by_user.values(), key=lambda e: e.total, reverse=True),
        unassigned_high_grade=unassigned_high,
    )


# ============================================================ company notes + activity
def list_company_notes(session: Session, domain: str) -> list[CompanyNoteOut]:
    return [CompanyNoteOut.model_validate(n) for n in repo.list_company_notes(session, domain)]


def add_company_note(session: Session, domain: str, payload: CompanyNoteIn, actor) -> CompanyNoteOut:
    if repo.get_company(session, domain) is None:
        raise HTTPException(status_code=404, detail="company not found")
    body = (payload.body or "").strip()
    if not body:
        raise HTTPException(status_code=422, detail="note body is required")
    note = repo.add_company_note(
        session, company_domain=domain, author_user_id=actor.id, author_email=actor.email, body=body
    )
    return CompanyNoteOut.model_validate(note)


def _aware(dt):
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def company_activity(session: Session, domain: str) -> list[ActivityItem]:
    items: list[ActivityItem] = []
    for n in repo.list_company_notes(session, domain):
        items.append(ActivityItem(kind="note", at=n.created_at, actor=n.author_email,
                                   title="Note", detail=n.body))
    events = repo.assignment_events_for(session, domain)
    emails = {uid: u.email for uid, u in
              repo.users_by_id(session, [e.actor_user_id for e in events if e.actor_user_id]).items()}
    for e in events:
        items.append(ActivityItem(
            kind="assignment", at=e.created_at,
            actor=emails.get(e.actor_user_id or -1, "system"),
            title=e.action.replace("_", " "),
            detail=e.detail or (f"{e.from_value} → {e.to_value}" if e.to_value else ""),
        ))
    score = repo.lead_score_for(session, domain)
    if score is not None and score.scored_at:
        items.append(ActivityItem(kind="score", at=score.scored_at, actor="system",
                                   title=f"Scored {score.grade} ({round(score.lead_score, 1)})"))
    for r in repo.lead_review_events_for(session, domain):
        items.append(ActivityItem(
            kind="review", at=r.created_at, actor=r.actor_email or "system",
            title=f"Human review → {r.to_status.replace('_', ' ')}",
            detail=r.notes or (f"{r.from_status} → {r.to_status}" if r.from_status else ""),
        ))
    items.sort(key=lambda i: _aware(i.at), reverse=True)
    return items


# ============================================================ human lead review (P-task viii)
def get_lead_review(session: Session, domain: str) -> LeadReviewOut | None:
    if repo.get_company(session, domain) is None:
        raise HTTPException(status_code=404, detail="company not found")
    review = repo.lead_review_for(session, domain)
    return LeadReviewOut.model_validate(review) if review is not None else None


def review_scoring_config() -> ScoringConfig:
    """The scoring config that governs review→score gating + adjustment. A seam
    tests monkeypatch to enable the (default-off) feature."""
    return ScoringConfig.load()


def set_lead_review(session: Session, domain: str, payload: LeadReviewIn, actor) -> LeadReviewOut:
    """Record a human assessment. The model ``lead_scores.lead_score``/``grade`` are
    NEVER changed — they stay separate. When the (default-off) ``review_feedback`` is
    enabled and the status is score-affecting, this also recomputes the company's
    SEPARATE adjusted score/grade (always from the pristine model score — never
    compounding), requires a reason + manager/admin, and snapshots the model→adjusted
    delta into the audit trail. No automatic learning/retraining."""
    if repo.get_company(session, domain) is None:
        raise HTTPException(status_code=404, detail="company not found")
    if payload.review_status not in LEAD_REVIEW_STATUSES:
        raise HTTPException(status_code=422, detail="invalid review_status")

    cfg = review_scoring_config()
    notes = (payload.human_notes or "").strip()
    score_affecting = cfg.review_feedback_enabled and cfg.status_affects_score(payload.review_status)
    if score_affecting and not notes:
        raise HTTPException(status_code=422, detail="a reason is required for a score-affecting review status")
    if score_affecting and getattr(actor, "role", "") not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="only managers/admins may set a score-affecting review status")

    existing = repo.lead_review_for(session, domain)
    from_status = existing.review_status if existing is not None else ""
    score = repo.lead_score_for(session, domain)
    now = datetime.now(timezone.utc)
    expires_at = payload.expires_at

    repo.upsert_lead_review(
        session, company_domain=domain, review_status=payload.review_status,
        human_notes=notes, reviewed_by=actor.id, reviewed_by_email=actor.email,
        reviewed_at=now, expires_at=expires_at,
    )

    # Recompute THIS company's adjusted value from the PRISTINE model score (cheap,
    # idempotent, no global re-score / no reshuffle of the model ranking).
    model_grade = score.grade if score is not None else ""
    model_score = score.lead_score if score is not None else 0.0
    adj_grade, adj_score = model_grade, model_score
    if score is not None:
        expired = bool(expires_at and _aware(expires_at) < now)
        a_score, a_g, a_rat = adjusted_score(score.lead_score, score.grade, payload.review_status, cfg, expired=expired)
        adjustment = None
        if a_rat:
            adjustment = {
                **a_rat, "reason": notes, "reviewed_by": actor.email,
                "reviewed_at": now.isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else None,
            }
        repo.set_lead_score_adjustment(session, domain, a_score, a_g, adjustment)
        adj_grade, adj_score = a_g, a_score

    repo.log_lead_review_event(
        session, company_domain=domain, actor_user_id=actor.id, actor_email=actor.email,
        from_status=from_status, to_status=payload.review_status, notes=notes,
        model_grade=model_grade, model_score=model_score,
        adjusted_grade=adj_grade, adjusted_score=adj_score,
    )
    session.commit()
    return LeadReviewOut.model_validate(repo.lead_review_for(session, domain))


def lead_review_history(session: Session, domain: str) -> list[LeadReviewEventOut]:
    if repo.get_company(session, domain) is None:
        raise HTTPException(status_code=404, detail="company not found")
    return [LeadReviewEventOut.model_validate(e) for e in repo.lead_review_events_for(session, domain)]


def review_reports(session: Session) -> ReviewReports:
    """The human-review reporting bundle (§7): model-vs-human disagreements,
    frequently-overridden companies, strategic accounts, false neg/pos, and the
    review-adjustment analytics (how human review is moving grades vs the model)."""
    cfg = review_scoring_config()

    def _adj(score) -> tuple[str, float]:
        if score is None:
            return "", 0.0
        g = score.adjusted_grade or score.grade
        s = score.adjusted_score if score.adjusted_score is not None else score.lead_score
        return g, s

    def _row(review, company, score, overrides) -> ReviewReportRow:
        grade = score.grade if score is not None else ""
        adj_grade, adj_score = _adj(score)
        return ReviewReportRow(
            company_domain=review.company_domain,
            company_name=getattr(company, "company_name", "") or review.company_domain,
            model_grade=grade,
            model_score=score.lead_score if score is not None else 0.0,
            adjusted_grade=adj_grade, adjusted_score=adj_score,
            human_status=review.review_status,
            human_notes=review.human_notes,
            override_count=int(overrides or 0),
            disagreement=disagreement(grade, review.review_status),
        )

    raw = repo.reviewed_leads(session)
    rows = [_row(*r) for r in raw]
    by_score = sorted(rows, key=lambda r: r.model_score, reverse=True)

    stats = ReviewAdjustmentStats(enabled=cfg.review_feedback_enabled)
    for (_rev, _co, score, _ov), row in zip(raw, rows):
        if score is None:
            continue
        adj_block = (score.rationale or {}).get("adjustment") or {}
        if adj_block.get("expired"):
            stats.expired += 1
        delta = row.adjusted_score - row.model_score
        if abs(delta) > 1e-9 or row.adjusted_grade != row.model_grade:
            stats.active_adjustments += 1
            stats.total_delta += delta
            if delta > 0:
                stats.boosted += 1
            elif delta < 0:
                stats.penalised += 1
            if adj_block.get("floor_grade"):
                stats.floor_applied += 1
    if stats.active_adjustments:
        stats.avg_delta = round(stats.total_delta / stats.active_adjustments, 2)
    stats.total_delta = round(stats.total_delta, 2)
    stats.movers = sorted(
        [r for r in rows if r.adjusted_grade and r.adjusted_grade != r.model_grade],
        key=lambda r: abs(r.adjusted_score - r.model_score), reverse=True)[:8]

    return ReviewReports(
        disagreements=[r for r in by_score if r.disagreement is not None],
        frequently_overridden=sorted(
            [r for r in rows if r.override_count >= 2],
            key=lambda r: r.override_count, reverse=True),
        strategic_accounts=[r for r in by_score if r.human_status == "strategic_account"],
        false_negatives=[r for r in by_score if r.disagreement == "false_negative"],
        false_positives=[r for r in by_score if r.disagreement == "false_positive"],
        status_distribution=repo.review_status_distribution(session),
        adjustments=stats,
    )
