"""Pydantic response schemas (API contract). ORM-mode (`from_attributes`)."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, field_validator

T = TypeVar("T")


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------- paging
class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(cls, items: list[T], total: int, page: int, page_size: int) -> "Page[T]":
        pages = (total + page_size - 1) // page_size if page_size else 0
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)


# ------------------------------------------------------------------- entities
class CompanySummary(_ORM):
    company_domain: str
    company_name: str
    company_tier: str
    prospect_type: str
    compliance_flag: str
    country: str = ""
    validation_status: str
    is_stub: bool
    lead_score: float | None = None
    grade: str | None = None


class CompanyOut(_ORM):
    company_domain: str
    canonical_company_id: str
    company_name: str
    website: str = ""
    company_linkedin: str = ""
    country: str = ""
    city: str = ""
    headquarters: str = ""
    compliance_flag: str
    industry_category: str = ""
    sub_category: str = ""
    technology_focus: str = ""
    prospect_type: str
    company_tier: str
    company_status: str = ""
    founded_year: str = ""
    confidence_score: float = 0.0
    validation_status: str
    is_stub: bool
    source: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OpportunityOut(_ORM):
    opportunity_id: str
    company_domain: str
    company_name: str = ""
    opportunity_type: str = ""
    opportunity_subtype: str = ""
    opportunity_category: str = ""
    opportunity_score: int = 0
    effective_opportunity_score: int = 0
    confidence_score: int = 0
    lead_readiness_score: int = 0
    source_credibility: int = 0
    technology_focus: str = ""
    article_title: str = ""
    article_url: str = ""
    source: str = ""
    source_type: str = ""
    published_date: str = ""
    event_age_days: int = -1
    summary: str = ""
    ai_summary: str = ""
    executive_summary: str = ""
    company_news_signal: str = ""   # annual-list rank ("Rank: N") / company-news one-liner
    validation_status: str = ""
    lifecycle_status: str = "NEW"
    is_relevant: bool = True
    related_group_id: str = ""
    technologies: list[str] = []

    @field_validator("company_news_signal", "opportunity_subtype", "ai_summary",
                     "executive_summary", "source_type", "related_group_id", mode="before")
    @classmethod
    def _str_or_empty(cls, v):   # NULL on pre-migration rows (columns added by the self-heal)
        return v or ""

    @field_validator("lifecycle_status", mode="before")
    @classmethod
    def _lifecycle_or_new(cls, v):
        return v or "NEW"

    @field_validator("technologies", mode="before")
    @classmethod
    def _list_or_empty(cls, v):
        return v or []


class OpportunitySourceOut(_ORM):
    id: int
    url: str = ""
    canonical_url: str = ""
    publisher: str = ""
    source_name: str = ""
    source_type: str = ""
    title: str = ""
    credibility: int = 0
    published_at: str = ""
    collected_at: datetime | None = None


class OpportunityReviewOut(_ORM):
    id: int
    action: str
    actor_email: str = ""
    detail: str = ""
    before_snapshot: dict = {}
    after_snapshot: dict = {}
    created_at: datetime | None = None


class OpportunityTimelineItemOut(BaseModel):
    opportunity_id: str
    opportunity_type: str = ""
    opportunity_subtype: str = ""
    article_title: str = ""
    published_date: str = ""
    lifecycle_status: str = "NEW"
    effective_opportunity_score: int = 0
    is_current: bool = False


class OpportunityDetailOut(OpportunityOut):
    """Full opportunity intelligence for the expandable detail panel."""

    why_this_matters: str = ""
    business_impact: str = ""
    ai_reasoning: str = ""
    products: list[str] = []
    people: list[str] = []
    organizations: list[str] = []
    countries: list[str] = []
    keywords: list[str] = []
    confidence_breakdown: dict = {}
    canonical_url: str = ""
    normalized_title: str = ""
    entity_fingerprint: str = ""
    merged_into: str = ""
    ingested_at: datetime | None = None
    sources: list[OpportunitySourceOut] = []
    related: list[OpportunityOut] = []
    timeline: list[OpportunityTimelineItemOut] = []
    reviews: list[OpportunityReviewOut] = []

    @field_validator("why_this_matters", "business_impact", "ai_reasoning",
                     "canonical_url", "normalized_title", "entity_fingerprint",
                     "merged_into", mode="before")
    @classmethod
    def _detail_str_or_empty(cls, v):
        return v or ""

    @field_validator("products", "people", "organizations", "countries", "keywords",
                     mode="before")
    @classmethod
    def _detail_list_or_empty(cls, v):
        return v or []

    @field_validator("confidence_breakdown", mode="before")
    @classmethod
    def _detail_dict_or_empty(cls, v):
        return v or {}


class OpportunityReviewIn(BaseModel):
    """A manual-review action. ``target_opportunity_id`` is required for merge;
    ``new_type`` for change_type; ``detail`` optional context / internal note."""

    action: str
    detail: str = ""
    target_opportunity_id: str | None = None
    new_type: str | None = None


class NewsSourceOut(_ORM):
    id: int
    name: str = ""
    adapter_type: str = ""
    url: str = ""
    publisher: str = ""
    credibility: int = 50
    enabled: bool = True
    last_collected_at: datetime | None = None


class NewsSourceIn(BaseModel):
    name: str
    adapter_type: str = "rss"       # rss | google_alerts | file | manual
    url: str = ""
    publisher: str = ""
    credibility: int = 50
    enabled: bool = True


class NewsSourcePatch(BaseModel):
    name: str | None = None
    adapter_type: str | None = None
    url: str | None = None
    publisher: str | None = None
    credibility: int | None = None
    enabled: bool | None = None


class NewsSeedResult(BaseModel):
    created: int
    updated: int
    total: int


# ------------------------------------------------------- Machine Learning Foundation
class InteractionIn(BaseModel):
    interaction_type: str          # thumbs_up | thumbs_down | export | contact | ignore
    entity_type: str = "opportunity"
    entity_id: str
    company_domain: str = ""
    sample_weight: float | None = None
    context: dict = {}


class InteractionOut(_ORM):
    id: int
    user_email: str = ""
    interaction_type: str
    entity_type: str
    entity_id: str
    company_domain: str = ""
    sample_weight: float = 1.0
    created_at: datetime | None = None


class FeatureVectorOut(BaseModel):
    entity_type: str = "company"
    entity_id: str
    feature_version: str
    features: dict


class FeatureRefreshResult(BaseModel):
    feature_version: str
    computed: int
    reused: int
    total: int


class DatasetBuildResult(BaseModel):
    version: str
    feature_version: str
    window_days: int
    row_count: int
    positive: int
    negative: int
    columns: list[str]


class MlModelOut(_ORM):
    id: int
    name: str
    version: str
    status: str
    model_type: str = ""
    feature_version: str = ""
    metrics: dict = {}
    created_at: datetime | None = None


class MlStatusOut(BaseModel):
    ml_enabled: bool
    feature_version: str
    embedding_backend: str
    embedding_model: str
    embedding_dim: int
    decay_half_lives: dict
    feature_row_count: int
    embedding_count: int
    interaction_count: int
    model_count: int
    training_run_count: int
    production_model: str | None = None
    recommendation_count: int = 0


class TrainResultOut(BaseModel):
    version: str
    backend: str
    feature_version: str
    dataset_version: str
    n_rows: int
    positive: int
    negative: int
    metrics: dict
    status: str = "draft"


class PromotionResultOut(BaseModel):
    promoted: bool
    version: str
    reason: str
    previous_version: str | None = None
    metrics: dict = {}
    checks: dict = {}


class InferenceResultOut(BaseModel):
    model_version: str
    scored: int
    batches: int


class RecommendationOut(_ORM):
    entity_type: str = "company"
    entity_id: str
    company_domain: str = ""
    model_version: str = ""
    probability: float = 0.0
    created_at: datetime | None = None


class MlModelDetailOut(_ORM):
    id: int
    name: str
    version: str
    status: str
    model_type: str = ""
    feature_version: str = ""
    metrics: dict = {}
    feature_importance: dict = {}
    model_metadata: dict = {}
    promoted_at: datetime | None = None
    created_at: datetime | None = None


class MlModelEventOut(_ORM):
    id: int
    model_version: str = ""
    action: str
    detail: str = ""
    actor_email: str = ""
    created_at: datetime | None = None


class JobOut(_ORM):
    job_id: str
    company_domain: str
    job_title: str = ""
    job_category: str = ""
    seniority: str = ""
    location: str = ""
    country: str = ""
    geo_region: str = ""
    employment_type: str = ""
    posted_date: str = ""
    ats_provider: str = ""
    technologies: str = ""
    engineering_relevance_score: int = 0
    job_url: str = ""


class DemandSignalOut(_ORM):
    company_domain: str
    demand_score: float = 0.0
    normalized_demand_score: float = 0.0
    total_engineering_jobs: int = 0
    primary_focus: str = ""
    technologies_detected: str = ""
    hiring_trend: str = ""
    lead_readiness_score: float = 0.0
    india_hiring_flag: bool = False
    newest_job_date: str = ""
    ats_provider: str = ""


class DecisionMakerOut(_ORM):
    id: int
    linkedin_url: str
    company_domain: str | None = None
    resolved_company_name: str = ""
    first_name: str = ""
    last_name: str = ""
    headline: str = ""
    current_title: str = ""
    seniority: str = ""
    location: str = ""
    # Structured professional fields from the engine (Apify). NULL when not supplied.
    full_name: str | None = None
    functional_area: str | None = None
    work_email: str | None = None
    email_status: str | None = None
    work_phone: str | None = None
    city: str | None = None
    state_region: str | None = None
    country: str | None = None
    organization_website: str | None = None
    organization_linkedin: str | None = None
    # Engine (Apify) metadata surfaced from profile_data (read-only properties).
    company_size: str | None = None
    industry: str | None = None
    alt_emails: str | None = None
    photo_url: str | None = None     # cheap enough for the list (avatar); heavy fields → Detail
    match_score: float = 0.0
    agent_score: float | None = None
    status: str = ""
    # Phase 2 decision intelligence — computed deterministically in the service
    # (batched company context, no N+1). All optional → backward compatible.
    department_class: str | None = None   # classified taxonomy (Executive, ASIC, Verification, …)
    department_group: str | None = None   # Company Contact Map bucket
    exec_level: str | None = None         # org-hierarchy label (Founder/CEO, VP, Director, …)
    influence_score: int | None = None    # 0–100 (normalized)
    confidence_score: int | None = None   # 0–100
    confidence_level: str = ""            # High | Medium | Low


class DecisionMakerDetailOut(DecisionMakerOut):
    """Full enrichment for ONE decision maker (lazy-loaded by the profile panel).

    Everything in :class:`DecisionMakerOut` plus the heavier/rarer fields read from
    the raw Apify record in ``profile_data`` — kept off the list payload so the
    directory and Company Profile stay fast. All optional: missing → None/blank."""

    department: str | None = None
    business_unit: str | None = None
    summary: str | None = None
    skills: str | None = None
    languages: str | None = None
    years_in_company: str | None = None
    years_in_role: str | None = None
    followers: str | None = None
    connections: str | None = None
    apify_person_id: str | None = None
    # Provenance / freshness metadata.
    source: str = ""
    captured_at: datetime | None = None
    ingested_at: datetime | None = None
    # Phase 2 decision intelligence (detail-only, lazy-loaded with the profile).
    influence_raw: float | None = None
    hierarchy_rank: int | None = None
    engineering_relevance: int | None = None
    influence_factors: list[str] = []
    confidence_factors: list[str] = []
    leadership_signals: list["LeadershipSignalOut"] = []
    # Phase 3 relationship intelligence (per contact).
    relationship_status: str = ""        # Cold | Known | Engaged | Active | Strategic
    relationship_score: int | None = None
    next_action: "NextActionOut | None" = None
    follow_up: "FollowUpOut | None" = None
    risk_severity: str = ""              # high | medium | low | ""
    risk_flags: list[str] = []


class DecisionMakerCompany(BaseModel):
    """A company with its resolved decision-maker count (company-first directory)."""

    company_domain: str
    company_name: str
    total: int
    senior: int = 0


class DecisionMakerCompanies(BaseModel):
    companies: list[DecisionMakerCompany]
    unresolved: int = 0


class ContactIn(BaseModel):
    """Professional contact details only — work email / phone. No personal data."""

    work_email: str = ""
    work_phone: str = ""
    notes: str = ""


class ContactOut(_ORM):
    id: int
    decision_maker_id: int
    work_email: str = ""
    work_phone: str = ""
    notes: str = ""
    added_by: int | None = None
    added_by_email: str = ""
    updated_at: datetime | None = None
    # True when the effective values are sourced from the engine (Apify) rather than a
    # saved, analyst-entered contact row — lets the UI label/badge it appropriately.
    from_source: bool = False
    # The original engine-sourced (Apify) values, ALWAYS preserved even after a manual
    # override, so the UI can show "manually overridden (was: …)" and never lose source.
    source_work_email: str = ""
    source_work_phone: str = ""
    # True when an analyst saved a value that differs from the engine's original.
    email_overridden: bool = False
    phone_overridden: bool = False


class DecisionMakerNoteIn(BaseModel):
    """Create a collaboration note. Tier rules (enforced in the service):
    ``admin`` → admins only · ``manager`` → admin/manager · ``team`` & ``personal``
    → any authenticated user (``personal`` is private to its author)."""

    note_type: Literal["admin", "manager", "team", "personal"] = "personal"
    content: str = ""


class DecisionMakerNoteUpdate(BaseModel):
    content: str


class DecisionMakerNoteOut(_ORM):
    id: int
    decision_maker_id: int
    note_type: str
    created_by: int | None = None
    author_email: str = ""
    author_role: str = ""          # the author's role (admin/manager/member) for display
    content: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Computed per request: may the *current* user edit/delete this note?
    can_edit: bool = False


class LeadScoreOut(_ORM):
    company_domain: str
    lead_score: float
    grade: str
    priority_rank: int
    opportunity_subscore: float
    demand_subscore: float
    readiness_subscore: float
    dm_subscore: float
    region_mult: float
    prospect_mult: float
    tier_mult: float
    coverage: int = 0
    confidence: str = "low"
    # Optional human-review adjustment (reconciled Change_05) — SEPARATE from the model
    # lead_score/grade above. null == no adjustment (adjusted == model).
    adjusted_score: float | None = None
    adjusted_grade: str = ""
    model_version: str
    scored_at: datetime | None = None
    rationale: dict = {}

    # Existing rows pre-0015 have a NULL adjusted_grade (column added by the SQLite
    # self-heal without backfilling); treat it as "no adjustment yet".
    @field_validator("adjusted_grade", mode="before")
    @classmethod
    def _grade_or_empty(cls, v):
        return v or ""


class ReviewStatusOut(BaseModel):
    is_stub: bool
    validation_status: str
    pending_review_items: int = 0
    match_types: list[str] = []


class LeadOut(_ORM):
    company_domain: str
    company_name: str = ""
    company_tier: str = ""
    prospect_type: str = ""
    compliance_flag: str = ""
    lead_score: float
    grade: str
    priority_rank: int
    opportunity_subscore: float = 0.0
    demand_subscore: float = 0.0
    readiness_subscore: float = 0.0
    dm_subscore: float = 0.0
    coverage: int = 0
    confidence: str = "low"
    # Human review (P-task viii) — surfaced ALONGSIDE the model grade, never replacing it.
    human_status: str | None = None       # None == not yet human-reviewed
    # Optional adjusted score/grade (reconciled Change_05) — the model values stay above.
    adjusted_score: float | None = None
    adjusted_grade: str = ""
    combined_priority: float | None = None  # = adjusted_score (the "combined" sort key)


# ---- Human lead review / feedback (P-task viii) ----
class LeadReviewIn(BaseModel):
    """A human assessment submission — the status verdict + a reason (required for
    score-affecting statuses when the feature is enabled) + an optional expiry."""

    review_status: str
    human_notes: str = ""
    expires_at: datetime | None = None


class LeadReviewOut(_ORM):
    """The current human assessment of a lead (separate from the model score)."""

    company_domain: str
    review_status: str
    human_notes: str = ""
    reviewed_by: int | None = None
    reviewed_by_email: str = ""
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LeadReviewEventOut(_ORM):
    """One entry in the review feedback / audit trail (who, when, status change,
    notes, and the model grade/score snapshot at the time)."""

    id: int
    company_domain: str = ""
    actor_user_id: int | None = None
    actor_email: str = ""
    from_status: str = ""
    to_status: str = ""
    notes: str = ""
    model_grade: str = ""
    model_score: float = 0.0
    adjusted_grade: str = ""
    adjusted_score: float = 0.0
    created_at: datetime | None = None

    @field_validator("adjusted_grade", mode="before")
    @classmethod
    def _grade_or_empty(cls, v):
        return v or ""

    @field_validator("adjusted_score", mode="before")
    @classmethod
    def _score_or_zero(cls, v):
        return v or 0.0


class ReviewReportRow(BaseModel):
    """A company in one of the review reports, with both verdicts side by side."""

    company_domain: str
    company_name: str = ""
    model_grade: str = ""
    model_score: float = 0.0
    adjusted_grade: str = ""           # the adjusted grade (== model when no effect)
    adjusted_score: float = 0.0
    human_status: str | None = None
    human_notes: str = ""
    override_count: int = 0          # number of human review actions logged
    disagreement: str | None = None  # false_positive | false_negative | None


class ReviewAdjustmentStats(BaseModel):
    """Review-adjustment analytics (reconciled Change_05 §7): how human review is
    moving grades vs the model. Zeroes when the feature is OFF."""

    enabled: bool = False
    active_adjustments: int = 0   # companies whose adjusted grade differs from the model
    boosted: int = 0
    penalised: int = 0
    floor_applied: int = 0
    expired: int = 0
    total_delta: float = 0.0      # Σ(adjusted_score − model_score)
    avg_delta: float = 0.0
    movers: list[ReviewReportRow] = []   # biggest model→adjusted grade movers


class ReviewReports(BaseModel):
    """The human-review reporting bundle (P-task viii §7 + reconciled Change_05)."""

    disagreements: list[ReviewReportRow] = []
    frequently_overridden: list[ReviewReportRow] = []
    strategic_accounts: list[ReviewReportRow] = []
    false_negatives: list[ReviewReportRow] = []
    false_positives: list[ReviewReportRow] = []
    status_distribution: dict[str, int] = {}
    adjustments: ReviewAdjustmentStats = ReviewAdjustmentStats()


class LeadershipSignalOut(_ORM):
    """A person-level director+ leadership-movement signal (P-task 8).

    Distinct from ``OpportunityOut``: this is who moved (a person), not that an
    event happened (a company opportunity). ``company_domain`` may be null when a
    historical employer didn't resolve to a catalogued company.
    """

    signal_id: str
    company_domain: str | None = None
    company_name: str = ""
    decision_maker_id: int | None = None
    linkedin_url: str = ""
    person_name: str = ""
    movement_type: str = ""
    from_title: str = ""
    to_title: str = ""
    seniority_band: str = ""
    role_function: str = ""
    effective_date: str = ""
    event_age_days: int = -1
    confidence: str = "low"
    source: str = ""
    summary: str = ""


class EngagementOut(_ORM):
    """A per-company sales-pitch / engagement recommendation (P-task 9): a likely
    business need, the matching Silicon Patterns offering, a one-line pitch, a
    confidence score, and the rationale (evidence) that produced it."""

    company_domain: str
    business_need: str = ""
    offering: str = ""
    pitch: str = ""
    confidence: int = 0
    confidence_label: str = "low"
    rationale: list[str] = []
    signals_used: int = 0
    model_version: str = ""


class CompanyProfile(BaseModel):
    """The unified view — every engine's data for one company, joined on domain."""

    company: CompanyOut
    lead_score: LeadScoreOut | None = None
    review_status: ReviewStatusOut
    counts: dict[str, int]
    opportunities: list[OpportunityOut] = []
    jobs: list[JobOut] = []
    demand_signal: DemandSignalOut | None = None
    decision_makers: list[DecisionMakerOut] = []
    leadership_signals: list[LeadershipSignalOut] = []
    engagement: EngagementOut | None = None
    lead_review: LeadReviewOut | None = None             # current human assessment (P-task viii)
    lead_review_history: list[LeadReviewEventOut] = []    # the audit trail for this company
    review_feedback_enabled: bool = False                # is review→score adjustment turned on?


class AnalyticsSummary(BaseModel):
    total_companies: int
    total_opportunities: int
    total_jobs: int
    total_demand_signals: int
    total_decision_makers: int
    total_leads: int
    grade_distribution: dict[str, int]
    top_companies: list[LeadOut]


class HealthOut(BaseModel):
    status: str
    app: str
    version: str
    database: str


# ------------------------------------------------------------ review queue
class ReviewItemOut(_ORM):
    id: int
    raw_name: str
    raw_domain: str
    raw_website: str
    source_engine: str
    source_record_ref: str
    suggested_domain: str
    match_type: str
    confidence: float
    status: str
    resolved_domain: str
    notes: str
    created_at: datetime | None = None
    reviewed_at: datetime | None = None


class ReviewActionOut(_ORM):
    id: int
    review_id: int | None
    action: str
    actor: str
    from_domain: str
    to_domain: str
    detail: str
    created_at: datetime | None = None


class ReviewActionResult(BaseModel):
    id: int
    status: str
    action: str
    resolved_domain: str | None = None
    detail: str = ""
    moved: dict[str, int] | None = None


class MergeBody(BaseModel):
    target_domain: str


class AliasBody(BaseModel):
    name: str
    company_domain: str


class RejectBody(BaseModel):
    reason: str | None = None


# ------------------------------------------------------- pipeline + coverage
class PipelineRunOut(_ORM):
    run_id: int
    pipeline_id: str
    component: str
    mode: str
    trigger: str
    status: str
    records_processed: int
    records_created: int
    records_updated: int
    records_review: int
    duration_ms: int
    started_at: datetime | None = None
    finished_at: datetime | None = None


class PipelineComponentHealth(BaseModel):
    component: str
    last_status: str
    last_run: datetime | None = None
    last_success: datetime | None = None
    last_duration_ms: int = 0
    failed_runs: int = 0


class AnalyticsCoverage(BaseModel):
    total_companies: int
    with_opportunities: int
    with_demand: int
    with_decision_makers: int
    with_lead_score: int
    with_all_three: int
    signal_distribution: dict[str, int]


class PipelineStatusOut(BaseModel):
    """Data-freshness signal. `last_successful_refresh` is when a full pipeline last
    completed (scoring is the final stage), so the UI can anchor to the last *good*
    refresh and warn when the latest run failed or is mid-flight."""

    last_successful_refresh: datetime | None = None
    latest_run_status: str
    latest_run_component: str | None = None
    in_progress: bool


# ----------------------------------------------------------- accounts / auth
class UserOut(_ORM):
    id: int
    email: str
    full_name: str = ""
    picture: str = ""
    role: str
    status: str = "active"
    is_active: bool = True
    login_count: int = 0
    created_at: datetime | None = None
    last_login_at: datetime | None = None
    last_seen_at: datetime | None = None
    deleted_at: datetime | None = None


class UserAuditOut(_ORM):
    id: int
    target_user_id: int | None = None
    target_email: str = ""
    actor_user_id: int | None = None
    actor_email: str = ""
    action: str
    detail: str = ""
    created_at: datetime | None = None


class MicrosoftAuthBody(BaseModel):
    id_token: str


class AuthResult(BaseModel):
    token: str       # the app's own session JWT
    user: UserOut


# ----------------------------------------------------- CRM: users / assignments / notes
class UserPatch(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class AssignmentCreate(BaseModel):
    company_domain: str
    user_id: int
    status: str = "assigned"
    note: str = ""


class AssignmentPatch(BaseModel):
    status: str | None = None
    note: str | None = None


class AssignmentOut(BaseModel):
    id: int
    company_domain: str
    company_name: str = ""
    grade: str | None = None
    lead_score: float | None = None
    user_id: int
    user_email: str = ""
    user_name: str = ""
    assigned_by: int | None = None
    assigned_by_email: str = ""
    assigned_by_name: str = ""
    status: str
    note: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AssignmentEventOut(BaseModel):
    id: int
    company_domain: str = ""
    actor_email: str = ""
    action: str
    from_value: str = ""
    to_value: str = ""
    detail: str = ""
    created_at: datetime | None = None


class WorkloadEntry(BaseModel):
    user_id: int
    email: str
    full_name: str = ""
    role: str = "member"
    total: int = 0
    by_status: dict[str, int] = {}


class WorkloadOut(BaseModel):
    users: list[WorkloadEntry]
    unassigned_high_grade: int = 0


class CompanyNoteIn(BaseModel):
    body: str


class CompanyNoteOut(_ORM):
    id: int
    company_domain: str
    author_user_id: int | None = None
    author_email: str = ""
    body: str = ""
    created_at: datetime | None = None


class ActivityItem(BaseModel):
    kind: str               # note | assignment | score
    at: datetime | None = None
    actor: str = ""
    title: str = ""
    detail: str = ""


# =====================================================================
# Outreach module (native) — engagement cycle over reused platform data
# =====================================================================
class OutreachContactOut(BaseModel):
    """A decision maker presented as an outreach contact (reused, not duplicated)."""

    decision_maker_id: int
    full_name: str = ""
    title: str = ""
    email: str = ""
    seniority: str = ""
    linkedin_url: str = ""
    is_primary: bool = False
    # Phase 2 decision intelligence (drives default ordering + the picker display).
    department: str = ""
    influence_score: int | None = None
    confidence_score: int | None = None
    confidence_level: str = ""
    recommendation_rank: str = ""        # primary | secondary | alternate | ""
    recommendation_reason: list[str] = []
    # Phase 3 relationship intelligence surfaced on the outreach picker.
    relationship_status: str = ""
    next_action: str = ""
    next_action_reason: str = ""


class OutreachSignalOut(BaseModel):
    """A one-line intelligence signal surfaced on the lead (from opportunities / demand)."""

    type: str = ""
    label: str = ""
    detail: str = ""
    source_url: str = ""


class OutreachLeadOut(_ORM):
    """A pipeline row: outreach state + live intelligence read from platform tables."""

    id: int
    company_domain: str
    company_name: str = ""
    stage: str
    service_interest: str | None = None
    source: str = "discovery"
    owner_id: int | None = None
    owner_email: str = ""
    # live intelligence (NOT stored on outreach_leads — read from lead_scores/engagement)
    lead_score: float | None = None
    grade: str = ""
    priority: str = ""                       # high | medium | low (derived from grade)
    signal_summary: str = ""
    qualification_reason: str = ""
    primary_contact: OutreachContactOut | None = None
    open_messages: int = 0
    sent_messages: int = 0
    reply_count: int = 0
    next_action_at: datetime | None = None
    last_activity_at: datetime | None = None
    qualified_at: datetime | None = None
    created_at: datetime | None = None


class OutreachLeadDetail(OutreachLeadOut):
    recommended_pitch: str = ""              # from engagement_recommendations
    recommended_offering: str = ""
    contacts: list[OutreachContactOut] = []
    signals: list[OutreachSignalOut] = []


class OutreachLeadCreate(BaseModel):
    company_domain: str
    service_interest: Literal["staffing", "engineering", "training"] | None = None
    owner_id: int | None = None


class OutreachLeadPatch(BaseModel):
    stage: Literal[
        "research_complete", "outreach_ready", "contacted", "replied",
        "interested", "meeting_scheduled", "proposal_sent", "won", "lost",
    ] | None = None
    owner_id: int | None = None
    service_interest: Literal["staffing", "engineering", "training"] | None = None
    primary_dm_id: int | None = None
    next_action_at: datetime | None = None


class OutreachSyncResult(BaseModel):
    created: int = 0
    updated: int = 0
    total: int = 0


class OutreachTemplateIn(BaseModel):
    name: str
    category: str = ""
    subject: str = ""
    body: str = ""
    is_active: bool = True


class OutreachTemplateOut(_ORM):
    id: int
    name: str
    category: str = ""
    subject: str = ""
    body: str = ""
    variables: list[str] = []               # parsed {{tokens}} (computed)
    is_active: bool = True
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OutreachMessageOut(_ORM):
    id: int
    outreach_lead_id: int
    decision_maker_id: int | None = None
    template_id: int | None = None
    direction: str = "outbound"
    status: str = "draft"
    to_email: str = ""
    from_email: str = ""
    subject: str = ""
    body: str = ""
    thread_id: str = ""
    recipient_name: str = ""
    created_by_email: str = ""
    approved_by_email: str = ""
    failed_reason: str = ""
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    scheduled_at: datetime | None = None
    cancel_at: datetime | None = None
    delivered_at: datetime | None = None
    bounced_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    provider: str = "mock"
    provider_message_id: str = ""
    updated_at: datetime | None = None
    created_at: datetime | None = None
    can_approve: bool = False               # computed for the current user/role
    attachment_count: int = 0              # computed
    # Phase 3: conversation + state
    conversation_id: int | None = None
    parent_message_id: int | None = None
    folder: str = "inbox"
    is_read: bool = False
    is_starred: bool = False
    is_archived: bool = False
    is_trashed: bool = False
    is_important: bool = False
    is_pinned: bool = False


class OutreachMessageCreate(BaseModel):
    decision_maker_id: int | None = None
    template_id: int | None = None
    subject: str = ""
    body: str = ""


class OutreachMessagePatch(BaseModel):
    subject: str | None = None
    body: str | None = None
    decision_maker_id: int | None = None


class OutreachThreadOut(BaseModel):
    thread_id: str
    outreach_lead_id: int
    company_name: str = ""
    company_domain: str = ""
    subject: str = ""
    last_at: datetime | None = None
    message_count: int = 0
    has_reply: bool = False
    messages: list[OutreachMessageOut] = []


class OutreachNoteIn(BaseModel):
    text: str


class OutreachActivityOut(_ORM):
    id: int
    outreach_lead_id: int
    type: str
    detail: str = ""
    actor_email: str = ""
    created_at: datetime | None = None


class OutreachStageCount(BaseModel):
    stage: str
    count: int


class OutreachAnalytics(BaseModel):
    total_leads: int = 0
    open_leads: int = 0
    won: int = 0
    lost: int = 0
    funnel: list[OutreachStageCount] = []
    drafts: int = 0
    pending_approval: int = 0
    sent: int = 0
    replied: int = 0
    reply_rate: float = 0.0
    win_rate: float = 0.0


# ----- Tasks -----
class OutreachTaskIn(BaseModel):
    title: str
    description: str = ""
    company_domain: str | None = None
    decision_maker_id: int | None = None
    outreach_lead_id: int | None = None
    assigned_to: int | None = None
    due_at: datetime | None = None
    priority: str = "medium"


class OutreachTaskPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    assigned_to: int | None = None
    due_at: datetime | None = None
    priority: str | None = None
    status: str | None = None


class OutreachTaskOut(_ORM):
    id: int
    title: str
    description: str = ""
    company_domain: str | None = None
    decision_maker_id: int | None = None
    outreach_lead_id: int | None = None
    assigned_to: int | None = None
    created_by: int | None = None
    due_at: datetime | None = None
    priority: str = "medium"
    status: str = "pending"
    completed_by: int | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # computed
    is_overdue: bool = False
    assigned_to_email: str = ""
    created_by_email: str = ""
    company_name: str = ""
    decision_maker_name: str = ""


# ----- Meetings -----
class OutreachMeetingIn(BaseModel):
    outreach_lead_id: int | None = None
    company_domain: str | None = None
    decision_maker_id: int | None = None
    meeting_type: str = "call"
    title: str = ""
    scheduled_at: datetime
    duration_minutes: int = 30
    participants: list[str] = []
    notes: str = ""
    outcome: str = ""
    next_action: str = ""


class OutreachMeetingPatch(BaseModel):
    meeting_type: str | None = None
    title: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    participants: list[str] | None = None
    notes: str | None = None
    outcome: str | None = None
    next_action: str | None = None


class OutreachMeetingOut(_ORM):
    id: int
    outreach_lead_id: int | None = None
    company_domain: str | None = None
    decision_maker_id: int | None = None
    meeting_type: str = "call"
    title: str = ""
    scheduled_at: datetime
    duration_minutes: int = 30
    participants: list = []
    notes: str = ""
    outcome: str = ""
    next_action: str = ""
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # computed
    company_name: str = ""
    decision_maker_name: str = ""
    created_by_email: str = ""
    is_upcoming: bool = False


# ----- Unified Timeline -----
class UnifiedTimelineEvent(BaseModel):
    event_id: str          # e.g. "activity-42" or "meeting-7" or "task-3"
    event_type: str        # "activity" | "meeting" | "task"
    type: str              # specific sub-type (e.g. "sent", "call", "task_completed")
    label: str             # human-readable one-liner
    detail: str = ""
    actor: str = ""
    timestamp: datetime


# ----- Follow-up items -----
class OutreachFollowUpItem(BaseModel):
    lead_id: int
    company_name: str
    company_domain: str
    due_at: datetime
    days_until: int           # negative = overdue
    is_overdue: bool
    days_since_activity: int | None = None
    reminder_priority: str = "low"    # "urgent" | "high" | "medium" | "low"
    stage: str = ""


# ----- Dashboard -----
class OutreachDashboardOut(BaseModel):
    tasks_due_today: list[OutreachTaskOut] = []
    overdue_tasks: list[OutreachTaskOut] = []
    upcoming_follow_ups: list[OutreachFollowUpItem] = []
    upcoming_meetings: list[OutreachMeetingOut] = []
    recent_activity: list[OutreachActivityOut] = []
    # summary counts
    open_tasks: int = 0
    total_meetings_this_week: int = 0
    overdue_follow_ups: int = 0


# ----- Contact history -----
class ContactHistoryOut(BaseModel):
    decision_maker_id: int
    full_name: str = ""
    title: str = ""
    company_domain: str = ""
    company_name: str = ""
    emails_sent: int = 0
    emails_received: int = 0
    meetings_count: int = 0
    notes_count: int = 0
    tasks_count: int = 0
    last_contacted_at: datetime | None = None
    timeline: list[UnifiedTimelineEvent] = []


# --------------------------------------------------------------------------- #
# Phase 2 — company contact map / recommendations / hierarchy
# --------------------------------------------------------------------------- #
class RankedContactOut(BaseModel):
    """A ranked decision maker with its recommendation role + deterministic reasons."""

    rank: str = ""                  # primary | secondary | alternate | ""
    ranking_score: float = 0.0
    reasons: list[str] = []
    contact: DecisionMakerOut       # carries the computed influence/confidence/department


class ContactGroupOut(BaseModel):
    """A Company Contact Map bucket (Executive, Engineering Leaders, …)."""

    group: str
    contacts: list[RankedContactOut] = []


class HierarchyLevelOut(BaseModel):
    """One organisation-hierarchy tier (Founder/CEO → IC), with its contacts."""

    rank: int
    level: str
    contacts: list[RankedContactOut] = []


class CompanyContactsOut(BaseModel):
    """Decision-intelligence view of a company's contacts: ranked recommendations,
    the auto-grouped contact map, and the inferred org hierarchy."""

    company_domain: str
    company_name: str = ""
    total: int = 0
    recommended: list[RankedContactOut] = []   # top three (primary/secondary/alternate)
    groups: list[ContactGroupOut] = []
    hierarchy: list[HierarchyLevelOut] = []


# --------------------------------------------------------------------------- #
# Phase 2.5 — company intelligence bundle (buying committee, coverage,
# completeness, engagement, heatmap, opportunity alignment, risk, timeline)
# --------------------------------------------------------------------------- #
class ContactRefOut(BaseModel):
    """A compact decision-maker reference carrying its computed intelligence."""

    decision_maker_id: int
    full_name: str = ""
    title: str = ""
    department: str = ""
    influence_score: int | None = None
    confidence_score: int | None = None
    confidence_level: str = ""


class CommitteeRoleOut(BaseModel):
    role: str
    present: bool = False
    contact: ContactRefOut | None = None


class BuyingCommitteeOut(BaseModel):
    roles: list[CommitteeRoleOut] = []
    present: int = 0
    total: int = 0
    coverage_pct: int = 0


class DeptCoverageRowOut(BaseModel):
    department: str
    count: int = 0
    present: bool = False


class DepartmentCoverageOut(BaseModel):
    rows: list[DeptCoverageRowOut] = []
    present: int = 0
    total: int = 0
    coverage_pct: int = 0
    missing: list[str] = []


class ContactCompletenessOut(BaseModel):
    total_contacts: int = 0
    verified_email_pct: int = 0
    phone_pct: int = 0          # phone presence (no provider phone verification)
    linkedin_pct: int = 0
    high_confidence_pct: int = 0
    avg_influence: int = 0
    avg_confidence: int = 0
    missing_email: int = 0
    missing_phone: int = 0
    missing_linkedin: int = 0


class EngagementScoreOut(BaseModel):
    score: int = 0
    label: str = "Dormant"          # Healthy | Warm | Cold | Dormant
    relationship: str = "Cold"      # Cold | Known | Engaged | Active | Strategic
    factors: list[str] = []


class TimelineEventOut(BaseModel):
    at: str = ""                    # ISO datetime / date / YYYY-MM
    kind: str = ""
    title: str = ""
    detail: str = ""


class HeatmapRowOut(BaseModel):
    department: str
    status: str = "Missing"         # Strong | Moderate | Weak | Missing
    contacts: int = 0
    detail: str = ""


class OppAlignmentOut(BaseModel):
    opportunity_id: str
    label: str = ""
    opportunity_type: str = ""
    best_department: str = ""
    contact: ContactRefOut | None = None
    reason: str = ""


class ContactRiskItemOut(BaseModel):
    decision_maker_id: int
    name: str = ""
    risks: list[str] = []


class ContactRiskOut(BaseModel):
    missing_email: int = 0
    missing_phone: int = 0
    missing_linkedin: int = 0
    low_confidence: int = 0
    stale: int = 0
    duplicates: int = 0
    leadership_departures: int = 0
    items: list[ContactRiskItemOut] = []


class CompanyIntelligenceOut(BaseModel):
    """The Company Intelligence panel bundle (Phase 2.5)."""

    company_domain: str
    company_name: str = ""
    total_contacts: int = 0
    buying_committee: BuyingCommitteeOut
    department_coverage: DepartmentCoverageOut
    contact_completeness: ContactCompletenessOut
    engagement: EngagementScoreOut
    contact_risk: ContactRiskOut
    relationship_heatmap: list[HeatmapRowOut] = []
    opportunity_alignment: list[OppAlignmentOut] = []
    timeline: list[TimelineEventOut] = []


# --------------------------------------------------------------------------- #
# Phase 3 — relationship intelligence (next best contact/action, follow-up,
# alerts, opportunity intelligence, relationship graph)
# --------------------------------------------------------------------------- #
class NextActionOut(BaseModel):
    action: str = ""        # Send Introduction | Follow Up | Schedule Meeting | …
    reason: str = ""
    priority: str = ""      # high | medium | low


class FollowUpOut(BaseModel):
    next_followup_at: datetime | None = None
    days_since_last_contact: int | None = None
    overdue: bool = False
    reminder_priority: str = "low"   # high | medium | low
    reason: str = ""


class NextBestContactOut(BaseModel):
    contact: ContactRefOut
    priority: str = ""               # Contact Now | Contact This Week | Monitor | Low Priority
    score: int = 0
    reasons: list[str] = []
    relationship_status: str = ""
    relationship_score: int | None = None
    next_action: NextActionOut | None = None
    follow_up: FollowUpOut | None = None
    risk_severity: str = ""
    risk_flags: list[str] = []


class OppIntelOut(BaseModel):
    opportunity_id: str
    label: str = ""
    opportunity_type: str = ""
    best_department: str = ""
    best: ContactRefOut | None = None
    backups: list[ContactRefOut] = []
    relationship_status: str = ""
    suggested_action: NextActionOut | None = None
    reason: str = ""


class AlertOut(BaseModel):
    type: str                       # executive_joined | executive_departed | promotion | …
    severity: str = "info"          # high | medium | info
    company_domain: str = ""
    company_name: str = ""
    title: str = ""
    detail: str = ""
    at: str = ""
    decision_maker_id: int | None = None


class GraphNodeOut(BaseModel):
    id: str
    kind: str                       # company | department | contact | leadership | opportunity | outreach
    label: str = ""
    detail: str = ""
    dm_id: int | None = None
    score: int | None = None


class GraphEdgeOut(BaseModel):
    source: str
    target: str
    kind: str = ""                  # department | hierarchy | committee | outreach | leadership | alignment


class RelationshipGraphOut(BaseModel):
    nodes: list[GraphNodeOut] = []
    edges: list[GraphEdgeOut] = []


class CompanyRelationshipsOut(BaseModel):
    company_domain: str
    company_name: str = ""
    next_best_contacts: list[NextBestContactOut] = []
    follow_ups: list[NextBestContactOut] = []
    opportunity_intelligence: list[OppIntelOut] = []
    alerts: list[AlertOut] = []
    graph: RelationshipGraphOut


# --------------------------------------------------------------------------- #
# Phase 2 — Email Architecture (providers, attachments, scheduling)
# --------------------------------------------------------------------------- #

class EmailAttachmentIn(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"
    content_b64: str                       # Base64-encoded file content


class EmailAttachmentOut(_ORM):
    id: int
    outreach_message_id: int
    filename: str
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    status: str = "uploaded"
    created_at: datetime | None = None
    # content_b64 omitted by default — fetched via /download endpoint


class EmailProviderAccountIn(BaseModel):
    provider_type: str = "mock"
    config_json: str | None = None         # JSON-encoded provider config


class EmailProviderAccountOut(_ORM):
    id: int = 0
    user_id: int | None = None
    provider_type: str = "mock"
    connection_status: str = "connected"
    error_message: str = ""
    # Phase 4: Gmail fields
    email_address: str = ""
    sync_status: str = "idle"
    sync_error: str = ""
    token_expires_at: datetime | None = None
    last_sync_at: datetime | None = None
    updated_at: datetime | None = None


# Phase 4 — Gmail OAuth & Sync
class GmailAuthUrlOut(BaseModel):
    auth_url: str
    state: str


class GmailConnectOut(_ORM):
    id: int = 0
    provider_type: str = "gmail"
    connection_status: str = "connected"
    email_address: str = ""
    sync_status: str = "idle"
    token_expires_at: datetime | None = None


class GmailSyncResultOut(BaseModel):
    ingested: int = 0
    skipped: int = 0
    next_cursor: str = ""
    error: str = ""
    accounts_synced: int = 0


class GmailRefreshOut(BaseModel):
    refreshed: bool
    token_expires_at: datetime | None = None
    error: str = ""


# --------------------------------------------------------------------------- #
# Phase 5 — Outreach Intelligence (recommendations, priority, analytics)
# --------------------------------------------------------------------------- #

class ContactRecommendationOut(BaseModel):
    decision_maker_id: int
    full_name: str = ""
    title: str = ""
    email: str = ""
    influence_score: int = 0
    confidence_score: int = 0
    confidence_level: str = ""
    relationship_strength: int = 0
    company_engagement: str = ""              # "Strong" | "Moderate" | "Weak"
    recommendation_reason: list[str] = []


class SendTimeRecommendationOut(BaseModel):
    recommended_time: datetime
    timezone_offset: str = ""
    factors: list[str] = []
    rationale: str = ""


class SubjectRecommendationOut(BaseModel):
    subject: str
    reason: str = ""
    confidence: str = ""                      # "high" | "medium" | "low"


class TemplateRecommendationOut(BaseModel):
    template_id: int
    name: str = ""
    category: str = ""
    reason: str = ""
    match_score: float = 0.0


class SuccessProbabilityOut(BaseModel):
    probability: int = 0                      # 0–100
    confidence_level: str = ""                # "High" | "Medium" | "Low"
    factors: list[str] = []


class OutreachPriorityOut(BaseModel):
    priority: str = ""                        # "Critical" | "High" | "Medium" | "Low"
    score: int = 0                            # 0–100
    factors: list[str] = []


class SequenceStepOut(BaseModel):
    order: int
    action: str = ""
    description: str = ""
    rationale: str = ""


class OutreachAnalyticsDetailOut(BaseModel):
    emails_sent: int = 0
    replies: int = 0
    meetings: int = 0
    reply_rate: float = 0.0
    meeting_rate: float = 0.0
    conversion_rate: float = 0.0


class CampaignIntelligenceOut(BaseModel):
    best_contact: ContactRecommendationOut | None = None
    best_send_time: SendTimeRecommendationOut | None = None
    best_subjects: list[SubjectRecommendationOut] = []
    best_template: TemplateRecommendationOut | None = None
    success_probability: SuccessProbabilityOut | None = None
    outreach_priority: OutreachPriorityOut | None = None


class EmailSchedulerTickOut(BaseModel):
    scheduled_to_queued: int = 0
    cancelled_by_deadline: int = 0
    gmail_synced: int = 0
    gmail_tokens_refreshed: int = 0
    sequences_advanced: int = 0
    timestamp: datetime


class MessageScheduleIn(BaseModel):
    scheduled_at: datetime
    cancel_at: datetime | None = None      # optional hard deadline for auto-cancellation


# --------------------------------------------------------------------------- #
# Phase 3 — Conversation & Inbox Engine
# --------------------------------------------------------------------------- #

class EmailLabelOut(_ORM):
    id: int
    name: str
    color: str = "gray"
    is_system: bool = False
    created_by: int | None = None
    created_at: datetime | None = None


class EmailLabelIn(BaseModel):
    name: str
    color: str = "gray"


class EmailConversationOut(BaseModel):
    id: int
    outreach_lead_id: int | None = None
    company_domain: str | None = None
    decision_maker_id: int | None = None
    subject: str = ""
    thread_id: str = ""
    folder: str = "inbox"
    message_count: int = 0
    unread_count: int = 0
    last_message_at: datetime | None = None
    is_starred: bool = False
    is_archived: bool = False
    is_trashed: bool = False
    is_pinned: bool = False
    company_name: str = ""
    labels: list[EmailLabelOut] = []
    preview_text: str = ""                  # first 120 chars of latest message body
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MessageReplyIn(BaseModel):
    body: str
    body_html: str = ""
    to_email: str = ""                      # defaults to original sender
    subject: str = ""                       # defaults to "Re: {original subject}"


class MessageForwardIn(BaseModel):
    body: str = ""
    body_html: str = ""
    to_email: str                           # required for forward
    subject: str = ""                       # defaults to "Fwd: {original subject}"


class MessagePreviewOut(BaseModel):
    id: int
    subject: str = ""
    body_plain: str = ""
    body_html_safe: str = ""               # sanitized HTML safe for rendering
    folder: str = "inbox"
    conversation_id: int | None = None
    attachments: list[EmailAttachmentOut] = []
    is_read: bool = False
    is_starred: bool = False
    is_important: bool = False


class BulkMessageIn(BaseModel):
    message_ids: list[int]
    action: str                             # "archive"|"restore"|"trash"|"mark_read"|"mark_unread"


class BulkConversationIn(BaseModel):
    conversation_ids: list[int]
    label_id: int | None = None
    action: str                             # "archive"|"restore"|"trash"|"apply_label"|"remove_label"


class BulkOperationOut(BaseModel):
    affected: int
    action: str


# --------------------------------------------------------------------------- #
# Enterprise CRM Phase 1 — Campaign & Sequence Management
# --------------------------------------------------------------------------- #

class CampaignCreate(BaseModel):
    name: str
    description: str = ""
    campaign_type: str = "cold_outreach"
    owner_id: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    goal: str = ""
    budget: float | None = None
    tags: list[str] = []


class CampaignPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    campaign_type: str | None = None
    status: str | None = None
    owner_id: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    goal: str | None = None
    budget: float | None = None
    tags: list[str] | None = None


class CampaignOut(BaseModel):
    id: int
    name: str
    description: str = ""
    campaign_type: str = "cold_outreach"
    status: str = "draft"
    owner_id: int | None = None
    owner_email: str = ""
    created_by: int | None = None
    created_by_email: str = ""
    start_date: datetime | None = None
    end_date: datetime | None = None
    goal: str = ""
    budget: float | None = None
    tags: list[str] = []
    # computed stats (batch-loaded, no N+1)
    member_count: int = 0
    active_count: int = 0
    converted_count: int = 0
    emails_sent: int = 0
    replies: int = 0
    meetings: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CampaignMemberIn(BaseModel):
    company_domain: str | None = None
    decision_maker_id: int | None = None
    opportunity_id: str | None = None
    outreach_lead_id: int | None = None


class CampaignMemberPatch(BaseModel):
    current_stage: str | None = None
    engagement_status: str | None = None
    campaign_outcome: str | None = None
    notes: str | None = None
    outreach_lead_id: int | None = None
    decision_maker_id: int | None = None


class CampaignMemberOut(BaseModel):
    id: int
    campaign_id: int
    company_domain: str = ""
    company_name: str = ""
    decision_maker_id: int | None = None
    decision_maker_name: str = ""
    opportunity_id: str | None = None
    outreach_lead_id: int | None = None
    joined_at: datetime | None = None
    current_stage: str = "pending"
    last_activity_at: datetime | None = None
    engagement_status: str = "active"
    campaign_outcome: str = ""
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CampaignAnalyticsOut(BaseModel):
    campaign_id: int
    campaign_name: str = ""
    companies_contacted: int = 0
    decision_makers_contacted: int = 0
    emails_sent: int = 0
    replies: int = 0
    meetings: int = 0
    reply_rate: float = 0.0
    meeting_rate: float = 0.0
    conversion_rate: float = 0.0
    active_members: int = 0
    total_members: int = 0
    converted: int = 0
    sequence_completion_rate: float = 0.0


class CampaignDashboardOut(BaseModel):
    active_campaigns: int = 0
    total_members: int = 0
    emails_sent: int = 0
    replies: int = 0
    meetings: int = 0
    overall_reply_rate: float = 0.0
    campaigns: list[CampaignOut] = []


# ----- Sequences -----
class CrmSequenceCreate(BaseModel):
    name: str
    description: str = ""


class CrmSequencePatch(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class CrmSequenceStepOut(BaseModel):
    id: int
    sequence_id: int
    step_order: int
    action: str
    name: str = ""
    description: str = ""
    delay_days: int = 0
    template_id: int | None = None
    config: dict = {}
    created_at: datetime | None = None


class CrmSequenceStepIn(BaseModel):
    step_order: int
    action: str
    name: str = ""
    description: str = ""
    delay_days: int = 0
    template_id: int | None = None
    config: dict = {}


class CrmSequenceStepPatch(BaseModel):
    step_order: int | None = None
    action: str | None = None
    name: str | None = None
    description: str | None = None
    delay_days: int | None = None
    template_id: int | None = None
    config: dict | None = None


class CrmSequenceOut(BaseModel):
    id: int
    name: str
    description: str = ""
    is_active: bool = True
    created_by: int | None = None
    step_count: int = 0
    steps: list[CrmSequenceStepOut] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CrmEnrollmentOut(BaseModel):
    id: int
    sequence_id: int
    outreach_lead_id: int
    campaign_member_id: int | None = None
    status: str = "active"
    current_step: int = 0
    next_step_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    # computed display fields (joined, not stored) — populated by the list endpoint;
    # absent (default) on the enroll/pause/resume/cancel/advance/skip action responses.
    sequence_name: str = ""
    step_count: int = 0
    campaign_id: int | None = None
    campaign_name: str = ""
    company_domain: str = ""
    company_name: str = ""


# --------------------------------------------------------------------------- #
# Enterprise CRM Phase 2 — Pipeline & Deal Management schemas
# --------------------------------------------------------------------------- #

class PipelineStageCreate(BaseModel):
    name: str
    stage_type: str = "open"
    stage_order: int = 1
    probability: int = 0


class PipelineStagePatch(BaseModel):
    name: str | None = None
    stage_type: str | None = None
    stage_order: int | None = None
    probability: int | None = None


class PipelineStageOut(BaseModel):
    id: int
    pipeline_id: int
    name: str
    stage_type: str = "open"
    stage_order: int = 1
    probability: int = 0
    created_at: datetime | None = None


class PipelineCreate(BaseModel):
    name: str
    description: str = ""
    is_default: bool = False
    stages: list[PipelineStageCreate] = []


class PipelinePatch(BaseModel):
    name: str | None = None
    description: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class PipelineOut(BaseModel):
    id: int
    name: str
    description: str = ""
    is_default: bool = False
    is_active: bool = True
    created_by: int | None = None
    stage_count: int = 0
    stages: list[PipelineStageOut] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DealCreate(BaseModel):
    title: str
    company_domain: str
    pipeline_id: int
    stage_id: int
    opportunity_id: str | None = None
    owner_id: int | None = None
    value: float | None = None
    currency: str = "USD"
    probability: int | None = None
    forecast_category: str = "pipeline"
    expected_close_date: datetime | None = None
    tags: list = []
    notes: str = ""
    lost_reason: str = ""
    won_reason: str = ""


class DealPatch(BaseModel):
    title: str | None = None
    opportunity_id: str | None = None
    owner_id: int | None = None
    value: float | None = None
    currency: str | None = None
    probability: int | None = None
    forecast_category: str | None = None
    expected_close_date: datetime | None = None
    tags: list | None = None
    notes: str | None = None
    lost_reason: str | None = None
    won_reason: str | None = None


class DealOut(BaseModel):
    id: int
    title: str
    company_domain: str
    opportunity_id: str | None = None
    pipeline_id: int
    stage_id: int
    stage_name: str = ""
    owner_id: int | None = None
    owner_email: str = ""
    created_by: int | None = None
    value: float | None = None
    currency: str = "USD"
    probability: int = 0
    forecast_category: str = "pipeline"
    expected_close_date: datetime | None = None
    last_activity_at: datetime | None = None
    tags: list = []
    notes: str = ""
    lost_reason: str = ""
    won_reason: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DealStageHistoryOut(BaseModel):
    id: int
    deal_id: int
    from_stage_id: int | None = None
    to_stage_id: int
    entered_at: datetime | None = None
    exited_at: datetime | None = None
    time_in_stage_seconds: int | None = None
    changed_by: int | None = None
    created_at: datetime | None = None


class DealMoveIn(BaseModel):
    stage_id: int


class KanbanColumnOut(BaseModel):
    stage_id: int
    stage_name: str
    stage_type: str = "open"
    stage_order: int
    deal_count: int = 0
    total_value: float = 0.0
    deals: list[DealOut] = []


class KanbanOut(BaseModel):
    pipeline_id: int
    pipeline_name: str = ""
    columns: list[KanbanColumnOut] = []
    total_deals: int = 0
    total_value: float = 0.0


class ForecastByQuarterOut(BaseModel):
    quarter: str
    weighted_value: float = 0.0


class ForecastByOwnerOut(BaseModel):
    owner_id: int
    owner_email: str = ""
    weighted_value: float = 0.0


class ForecastOut(BaseModel):
    pipeline_id: int
    pipeline_value: float = 0.0
    weighted_pipeline: float = 0.0
    expected_revenue: float = 0.0
    win_probability: float = 0.0
    avg_deal_size: float = 0.0
    avg_sales_cycle_days: float | None = None
    pipeline_velocity: float | None = None
    open_deals: int = 0
    won_deals: int = 0
    lost_deals: int = 0
    forecast_by_quarter: list[ForecastByQuarterOut] = []
    forecast_by_owner: list[ForecastByOwnerOut] = []


class StageVelocityOut(BaseModel):
    stage_id: int
    stage_name: str
    stage_type: str = "open"
    stage_order: int = 0
    avg_time_days: float = 0.0
    deals_entered: int = 0
    deals_exited: int = 0
    conversion_rate: float = 0.0


class DealAnalyticsOut(BaseModel):
    pipeline_id: int
    total_deals: int = 0
    open_deals: int = 0
    won_deals: int = 0
    lost_deals: int = 0
    win_rate: float = 0.0
    loss_rate: float = 0.0
    pipeline_value: float = 0.0
    weighted_pipeline: float = 0.0
    stalled_deal_count: int = 0
    stage_velocity: list[StageVelocityOut] = []


class DealDashboardOut(BaseModel):
    pipeline_id: int | None = None
    total_open_deals: int = 0
    total_won_deals: int = 0
    total_lost_deals: int = 0
    pipeline_value: float = 0.0
    weighted_pipeline: float = 0.0
    win_rate: float = 0.0
    closing_soon: list[DealOut] = []
    stalled_deals: list[DealOut] = []
    high_value_deals: list[DealOut] = []
    recently_won: list[DealOut] = []
    recently_lost: list[DealOut] = []


class DealIntelligenceOut(BaseModel):
    deal_id: int
    company_domain: str
    best_contact: "ContactRecommendationOut | None" = None
    backup_contacts: list["ContactRecommendationOut"] = []
    buying_committee: "BuyingCommitteeOut | None" = None
    relationship_strength: int = 0
    success_probability: "SuccessProbabilityOut | None" = None
    next_action: "NextActionOut | None" = None
    recommended_sequence: list["SequenceStepOut"] = []
    outreach_priority: "OutreachPriorityOut | None" = None


# --------------------------------------------------------------------------- #
# Enterprise CRM Phase 3 — Team Collaboration schemas
# --------------------------------------------------------------------------- #

class CrmAssignmentCreate(BaseModel):
    entity_type: str
    entity_id: str
    user_id: int
    role: str = "assignee"
    note: str = ""


class CrmAssignmentPatch(BaseModel):
    role: str | None = None
    note: str | None = None


class CrmAssignmentOut(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    user_id: int
    user_email: str = ""
    role: str = "assignee"
    assigned_by: int | None = None
    note: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CrmAssignmentHistoryOut(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    user_id: int | None = None
    user_email: str = ""
    role: str = ""
    action: str
    changed_by: int | None = None
    detail: str = ""
    created_at: datetime | None = None


class CommentCreate(BaseModel):
    body: str
    parent_id: int | None = None
    mentions: list[int] = []


class CommentPatch(BaseModel):
    body: str | None = None


class CommentOut(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    author_id: int | None = None
    author_email: str = ""
    body: str
    mentions: list[int] = []
    parent_id: int | None = None
    is_edited: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NotificationOut(BaseModel):
    id: int
    user_id: int
    notif_type: str
    title: str = ""
    body: str = ""
    entity_type: str | None = None
    entity_id: str | None = None
    is_read: bool = False
    created_at: datetime | None = None


class SavedViewCreate(BaseModel):
    name: str
    entity_type: str
    is_shared: bool = False
    filters: dict = {}
    sort_by: str = ""
    sort_dir: str = "desc"
    columns: list[str] = []
    grouping: str = ""
    search: str = ""


class SavedViewPatch(BaseModel):
    name: str | None = None
    is_shared: bool | None = None
    filters: dict | None = None
    sort_by: str | None = None
    sort_dir: str | None = None
    columns: list[str] | None = None
    grouping: str | None = None
    search: str | None = None


class SavedViewOut(BaseModel):
    id: int
    name: str
    entity_type: str
    owner_id: int | None = None
    owner_email: str = ""
    is_shared: bool = False
    filters: dict = {}
    sort_by: str = ""
    sort_dir: str = "desc"
    columns: list[str] = []
    grouping: str = ""
    search: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WorkQueueOut(BaseModel):
    my_deals: list["DealOut"] = []
    my_campaigns: list["CampaignOut"] = []
    tasks_due: list["OutreachTaskOut"] = []
    overdue_tasks: list["OutreachTaskOut"] = []
    upcoming_meetings: list["OutreachMeetingOut"] = []
    unread_notifications: int = 0
    pending_approvals: int = 0


class TeamDashboardOut(BaseModel):
    unread_notifications: int = 0
    pending_approvals: int = 0
    my_active_deals: int = 0
    my_active_campaigns: int = 0
    tasks_due_count: int = 0
    overdue_tasks_count: int = 0
    upcoming_meetings_count: int = 0
    team_open_tasks: int = 0
    team_overdue_tasks: int = 0
    team_completed_tasks: int = 0
    total_assignments: int = 0


class TeamAssignmentDistRow(BaseModel):
    user_id: int
    user_email: str = ""
    total: int = 0
    deals: int = 0
    campaigns: int = 0
    tasks: int = 0
    meetings: int = 0


class TeamAnalyticsOut(BaseModel):
    open_work: int = 0
    completed_work: int = 0
    overdue_work: int = 0
    avg_completion_time_hours: float | None = None
    total_assignments: int = 0
    assignment_distribution: list[TeamAssignmentDistRow] = []


# --------------------------------------------------------------------------- #
# Enterprise CRM Phase 4 — Customer Success & Account Management schemas
# --------------------------------------------------------------------------- #

class CsAccountCreate(BaseModel):
    name: str
    company_domain: str | None = None
    owner_id: int | None = None
    status: str = "active"
    tier: str = "mid_market"
    industry: str = ""
    arr: float = 0.0
    mrr: float = 0.0
    contract_value: float = 0.0
    currency: str = "USD"
    renewal_date: datetime | None = None
    lifecycle_stage: str = "customer"
    notes: str = ""
    tags: list[str] = []


class CsAccountPatch(BaseModel):
    name: str | None = None
    company_domain: str | None = None
    owner_id: int | None = None
    status: str | None = None
    tier: str | None = None
    industry: str | None = None
    arr: float | None = None
    mrr: float | None = None
    contract_value: float | None = None
    currency: str | None = None
    renewal_date: datetime | None = None
    lifecycle_stage: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


class CsAccountOut(BaseModel):
    id: int
    name: str
    company_domain: str | None = None
    owner_id: int | None = None
    owner_email: str = ""
    status: str = "active"
    tier: str = "mid_market"
    industry: str = ""
    arr: float = 0.0
    mrr: float = 0.0
    contract_value: float = 0.0
    currency: str = "USD"
    renewal_date: datetime | None = None
    lifecycle_stage: str = "customer"
    notes: str = ""
    tags: list[str] = []
    health_score: float | None = None
    health_grade: str | None = None
    health_trend: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CsContactCreate(BaseModel):
    account_id: int
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    title: str = ""
    role: str = "primary"
    is_primary: bool = False
    owner_id: int | None = None
    notes: str = ""


class CsContactPatch(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    role: str | None = None
    is_primary: bool | None = None
    owner_id: int | None = None
    notes: str | None = None


class CsContactOut(BaseModel):
    id: int
    account_id: int
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    title: str = ""
    role: str = "primary"
    is_primary: bool = False
    owner_id: int | None = None
    owner_email: str = ""
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CsHealthScoreCreate(BaseModel):
    product_adoption: float = 0.0
    meeting_activity: float = 0.0
    email_activity: float = 0.0
    opportunity_activity: float = 0.0
    open_issues: float = 100.0    # 100 = no issues, lower = issues exist
    renewal_status: float = 100.0
    executive_engagement: float = 0.0
    detail: dict = {}


class CsHealthScoreOut(BaseModel):
    id: int
    account_id: int
    score: float
    grade: str
    trend: str
    product_adoption: float
    meeting_activity: float
    email_activity: float
    opportunity_activity: float
    open_issues: float
    renewal_status: float
    executive_engagement: float
    detail: dict = {}
    created_at: datetime | None = None


class CsLifecycleEventOut(BaseModel):
    id: int
    account_id: int
    stage: str
    from_stage: str = ""
    changed_by: int | None = None
    note: str = ""
    created_at: datetime | None = None


class CsContractCreate(BaseModel):
    account_id: int
    name: str
    status: str = "active"
    value: float = 0.0
    currency: str = "USD"
    start_date: datetime | None = None
    end_date: datetime | None = None
    auto_renew: bool = False
    renewal_probability: float = 0.5
    owner_id: int | None = None
    notes: str = ""


class CsContractPatch(BaseModel):
    name: str | None = None
    status: str | None = None
    value: float | None = None
    currency: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    auto_renew: bool | None = None
    renewal_probability: float | None = None
    owner_id: int | None = None
    notes: str | None = None


class CsContractOut(BaseModel):
    id: int
    account_id: int
    name: str
    status: str
    value: float = 0.0
    currency: str = "USD"
    start_date: datetime | None = None
    end_date: datetime | None = None
    auto_renew: bool = False
    renewal_probability: float = 0.5
    owner_id: int | None = None
    owner_email: str = ""
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CsSuccessPlanCreate(BaseModel):
    account_id: int
    name: str
    status: str = "active"
    owner_id: int | None = None
    goals: list[dict] = []
    notes: str = ""
    due_date: datetime | None = None


class CsSuccessPlanPatch(BaseModel):
    name: str | None = None
    status: str | None = None
    owner_id: int | None = None
    goals: list[dict] | None = None
    notes: str | None = None
    due_date: datetime | None = None


class CsSuccessPlanOut(BaseModel):
    id: int
    account_id: int
    name: str
    status: str
    owner_id: int | None = None
    owner_email: str = ""
    goals: list[dict] = []
    notes: str = ""
    due_date: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CsMilestoneCreate(BaseModel):
    plan_id: int
    account_id: int
    name: str
    status: str = "pending"
    due_date: datetime | None = None
    owner_id: int | None = None
    notes: str = ""


class CsMilestonePatch(BaseModel):
    name: str | None = None
    status: str | None = None
    due_date: datetime | None = None
    owner_id: int | None = None
    notes: str | None = None


class CsMilestoneOut(BaseModel):
    id: int
    plan_id: int
    account_id: int
    name: str
    status: str
    due_date: datetime | None = None
    completed_at: datetime | None = None
    owner_id: int | None = None
    owner_email: str = ""
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CsRiskCreate(BaseModel):
    account_id: int
    title: str
    description: str = ""
    severity: str = "medium"
    status: str = "open"
    owner_id: int | None = None
    due_date: datetime | None = None


class CsRiskPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: str | None = None
    status: str | None = None
    owner_id: int | None = None
    due_date: datetime | None = None


class CsRiskOut(BaseModel):
    id: int
    account_id: int
    title: str
    description: str = ""
    severity: str
    status: str
    owner_id: int | None = None
    owner_email: str = ""
    due_date: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CsTimelineEvent(BaseModel):
    event_id: str
    event_type: str   # task | meeting | comment | contract | lifecycle | health | risk
    label: str
    detail: str = ""
    timestamp: datetime


class CsDashboardOut(BaseModel):
    total_accounts: int = 0
    active_accounts: int = 0
    at_risk_accounts: int = 0
    churned_accounts: int = 0
    total_arr: float = 0.0
    total_mrr: float = 0.0
    avg_health_score: float | None = None
    renewals_due_90d: int = 0
    open_risks: int = 0
    expansion_accounts: int = 0
    open_tasks: int = 0
    upcoming_meetings: int = 0


class CsAnalyticsOut(BaseModel):
    total_arr: float = 0.0
    total_mrr: float = 0.0
    active_count: int = 0
    churn_rate: float = 0.0
    renewal_rate: float = 0.0
    churn_count: int = 0
    avg_health_score: float | None = None
    health_distribution: dict[str, int] = {}
    expansion_account_count: int = 0
    by_status: dict[str, int] = {}


# =====================================================================
# Enterprise CRM Phase 5 — Revenue Operations, Forecasting & Executive Analytics
# =====================================================================

class RevenueTargetCreate(BaseModel):
    scope: str = "company"
    owner_id: int | None = None
    pipeline_id: int | None = None
    period_type: str = "monthly"
    period_start: datetime
    period_end: datetime
    target_amount: float = 0.0
    currency: str = "USD"
    notes: str = ""


class RevenueTargetOut(BaseModel):
    id: int
    scope: str
    owner_id: int | None = None
    owner_email: str = ""
    pipeline_id: int | None = None
    period_type: str
    period_start: datetime
    period_end: datetime
    target_amount: float = 0.0
    currency: str = "USD"
    notes: str = ""
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TargetAttainmentOut(BaseModel):
    target_id: int
    target_amount: float = 0.0
    actual_amount: float = 0.0
    attainment_pct: float = 0.0
    period_start: datetime
    period_end: datetime
    is_elapsed: bool = False


class ForecastPeriodOut(BaseModel):
    period_key: str
    period_type: str
    pipeline_value: float = 0.0
    weighted_value: float = 0.0
    best_case_value: float = 0.0
    commit_value: float = 0.0
    deal_count: int = 0


class RevenueForecastOut(BaseModel):
    period_type: str
    pipeline_id: int | None = None
    periods: list[ForecastPeriodOut] = []


class ForecastSnapshotOut(BaseModel):
    id: int
    pipeline_id: int | None = None
    period_type: str
    period_key: str
    category: str
    forecasted_amount: float = 0.0
    snapshot_at: datetime | None = None


class ForecastAccuracyOut(BaseModel):
    snapshot_id: int
    pipeline_id: int | None = None
    period_type: str
    period_key: str
    category: str
    forecasted_amount: float = 0.0
    actual_amount: float = 0.0
    variance: float = 0.0
    accuracy_pct: float = 0.0


class ExecutiveDashboardOut(BaseModel):
    revenue_ttm: float = 0.0
    pipeline_value: float = 0.0
    weighted_forecast: float = 0.0
    win_rate: float = 0.0
    conversion_rate: float = 0.0
    sales_velocity: float | None = None
    avg_sales_cycle_days: float | None = None
    arr: float = 0.0
    mrr: float = 0.0
    active_customers: int = 0
    churn_rate: float = 0.0
    expansion_accounts: int = 0
    generated_at: datetime | None = None


class PipelineAgingOut(BaseModel):
    bucket: str
    deal_count: int = 0


class RevopsPipelineAnalyticsOut(BaseModel):
    pipeline_id: int | None = None
    total_deals: int = 0
    open_deals: int = 0
    won_deals: int = 0
    lost_deals: int = 0
    win_rate: float = 0.0
    loss_rate: float = 0.0
    pipeline_value: float = 0.0
    weighted_pipeline: float = 0.0
    pipeline_health_score: float = 0.0
    aging: list[PipelineAgingOut] = []
    lost_reasons: dict[str, int] = {}
    won_reasons: dict[str, int] = {}
    stage_velocity: list[StageVelocityOut] = []


class RevenueByDimensionOut(BaseModel):
    key: str
    deal_count: int = 0
    revenue: float = 0.0


class SalesPerformanceOut(BaseModel):
    by_owner: list[RevenueByDimensionOut] = []
    by_team: list[RevenueByDimensionOut] = []
    by_region: list[RevenueByDimensionOut] = []
    by_industry: list[RevenueByDimensionOut] = []
    by_tier: list[RevenueByDimensionOut] = []
    avg_deal_size: float = 0.0
    avg_sales_cycle_days: float | None = None
    close_rate: float = 0.0


class FunnelStageOut(BaseModel):
    stage: str
    count: int = 0
    drop_off_pct: float | None = None


class FunnelAnalyticsOut(BaseModel):
    lead_funnel: list[FunnelStageOut] = []
    opportunity_funnel: list[FunnelStageOut] = []
    deal_funnel: list[FunnelStageOut] = []
    campaign_funnel: list[FunnelStageOut] = []


class ExecutiveReportOut(BaseModel):
    report_type: str
    generated_at: datetime
    data: dict = {}


class BiSummaryOut(BaseModel):
    executive_dashboard: ExecutiveDashboardOut
    funnels: FunnelAnalyticsOut
    sales_performance: SalesPerformanceOut
    revenue_trend: list[dict] = []


# =====================================================================
# Enterprise CRM Phase 6 — Workflow Automation & Business Process Engine
# =====================================================================

class WorkflowConditionRule(BaseModel):
    field: str
    op: str = "eq"   # eq | neq | gt | gte | lt | lte | in | contains
    value: object = None


class WorkflowConditionGroup(BaseModel):
    logic: str = "AND"   # AND | OR (between rules in this group)
    rules: list[WorkflowConditionRule] = []


class WorkflowConditions(BaseModel):
    logic: str = "AND"   # AND | OR (between groups)
    groups: list[WorkflowConditionGroup] = []


class WorkflowAction(BaseModel):
    type: str
    params: dict = {}


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    status: str = "draft"
    trigger_event: str
    conditions: WorkflowConditions = WorkflowConditions()
    actions: list[WorkflowAction] = []
    is_enabled: bool = True


class WorkflowPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    conditions: WorkflowConditions | None = None
    actions: list[WorkflowAction] | None = None
    is_enabled: bool | None = None


class WorkflowOut(BaseModel):
    id: int
    name: str
    description: str = ""
    status: str
    trigger_event: str
    conditions: dict = {}
    actions: list = []
    version: int = 1
    is_enabled: bool = True
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WorkflowActionResult(BaseModel):
    type: str
    ok: bool = True
    detail: str = ""


class WorkflowExecutionOut(BaseModel):
    id: int
    workflow_id: int
    workflow_name: str = ""
    trigger_event: str
    entity_type: str = ""
    entity_id: str = ""
    status: str
    actions_executed: list[WorkflowActionResult] = []
    error_detail: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0


class ApprovalRequestCreate(BaseModel):
    approval_type: str
    entity_type: str = ""
    entity_id: str = ""
    approver_id: int | None = None


class ApprovalDecisionIn(BaseModel):
    decision: str   # approved | rejected
    comments: str = ""


class ApprovalRequestOut(BaseModel):
    id: int
    approval_type: str
    entity_type: str = ""
    entity_id: str = ""
    requested_by: int | None = None
    requested_by_email: str = ""
    approver_id: int | None = None
    approver_email: str = ""
    status: str
    decision_reason: str = ""
    workflow_execution_id: int | None = None
    requested_at: datetime | None = None
    decided_at: datetime | None = None


class SlaPolicyCreate(BaseModel):
    name: str
    entity_type: str = ""
    trigger_event: str = ""
    due_hours: int = 24
    escalate_after_hours: int | None = None
    escalate_to_user_id: int | None = None
    is_enabled: bool = True


class SlaPolicyPatch(BaseModel):
    name: str | None = None
    due_hours: int | None = None
    escalate_after_hours: int | None = None
    escalate_to_user_id: int | None = None
    is_enabled: bool | None = None


class SlaPolicyOut(BaseModel):
    id: int
    name: str
    entity_type: str = ""
    trigger_event: str = ""
    due_hours: int = 24
    escalate_after_hours: int | None = None
    escalate_to_user_id: int | None = None
    is_enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SlaTrackerCreate(BaseModel):
    policy_id: int
    entity_type: str = ""
    entity_id: str = ""
    due_at: datetime | None = None


class SlaTrackerOut(BaseModel):
    id: int
    policy_id: int
    entity_type: str = ""
    entity_id: str = ""
    due_at: datetime
    status: str
    escalated_at: datetime | None = None
    breached_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime | None = None


class SlaTickResultOut(BaseModel):
    checked: int = 0
    newly_at_risk: int = 0
    newly_breached: int = 0
    newly_escalated: int = 0


class RenewalScanResultOut(BaseModel):
    workflows_fired: int = 0


class WorkflowDashboardOut(BaseModel):
    active_workflows: int = 0
    total_executions: int = 0
    success_rate: float = 0.0
    failure_count: int = 0
    pending_approvals: int = 0
    sla_breaches: int = 0
    recent_executions: list[WorkflowExecutionOut] = []


class WorkflowUsageOut(BaseModel):
    workflow_id: int
    workflow_name: str
    execution_count: int = 0


class WorkflowAnalyticsOut(BaseModel):
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    avg_execution_time_ms: float = 0.0
    avg_approval_time_hours: float | None = None
    sla_compliance_rate: float = 0.0
    most_used_workflows: list[WorkflowUsageOut] = []


# =====================================================================
# Enterprise CRM Phase 7 — Custom Objects, Forms & No-Code Platform
# =====================================================================

class CustomObjectCreate(BaseModel):
    name: str
    api_name: str
    description: str = ""
    icon: str = ""
    status: str = "draft"


class CustomObjectPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    status: str | None = None


class CustomObjectOut(BaseModel):
    id: int
    name: str
    api_name: str
    description: str = ""
    icon: str = ""
    status: str
    version: int = 1
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CustomFieldCreate(BaseModel):
    name: str
    api_name: str
    field_type: str
    is_required: bool = False
    default_value: object = None
    validation: dict = {}
    picklist_options: list[str] = []
    lookup_object_id: int | None = None
    display_order: int = 0


class CustomFieldPatch(BaseModel):
    name: str | None = None
    is_required: bool | None = None
    default_value: object = None
    validation: dict | None = None
    picklist_options: list[str] | None = None
    display_order: int | None = None


class CustomFieldOut(BaseModel):
    id: int
    object_id: int
    name: str
    api_name: str
    field_type: str
    is_required: bool = False
    default_value: object = None
    validation: dict = {}
    picklist_options: list[str] = []
    lookup_object_id: int | None = None
    display_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CustomFormFieldLayout(BaseModel):
    field_api_name: str
    read_only: bool = False
    required_override: bool | None = None
    visible_if: dict | None = None


class CustomFormSection(BaseModel):
    title: str = ""
    fields: list[CustomFormFieldLayout] = []


class CustomFormLayout(BaseModel):
    sections: list[CustomFormSection] = []


class CustomFormCreate(BaseModel):
    name: str
    description: str = ""
    layout: CustomFormLayout = CustomFormLayout()
    is_default: bool = False


class CustomFormPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    layout: CustomFormLayout | None = None
    is_default: bool | None = None


class CustomFormOut(BaseModel):
    id: int
    object_id: int
    name: str
    description: str = ""
    layout: dict = {}
    is_default: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CustomRecordCreate(BaseModel):
    data: dict = {}


class CustomRecordPatch(BaseModel):
    data: dict = {}


class CustomRecordOut(BaseModel):
    id: int
    object_id: int
    data: dict = {}
    created_by: int | None = None
    updated_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CustomRecordAuditOut(BaseModel):
    id: int
    record_id: int
    action: str
    changed_by: int | None = None
    changed_by_email: str = ""
    field_changes: dict = {}
    created_at: datetime | None = None


class CustomRecordValidationError(BaseModel):
    field_api_name: str
    message: str


class CustomDataJobOut(BaseModel):
    id: int
    object_id: int
    job_type: str
    status: str
    total_rows: int = 0
    success_count: int = 0
    error_count: int = 0
    errors: list = []
    created_by: int | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


class CustomObjectDashboardOut(BaseModel):
    total_objects: int = 0
    active_objects: int = 0
    total_records: int = 0
    recent_records: list[CustomRecordOut] = []
    recent_import_errors: int = 0
    import_jobs_run: int = 0


class FieldUtilizationOut(BaseModel):
    field_api_name: str
    filled_pct: float = 0.0


class CustomObjectAnalyticsOut(BaseModel):
    object_id: int
    records_created_total: int = 0
    records_created_by_period: dict[str, int] = {}
    records_updated_total: int = 0
    field_utilization: list[FieldUtilizationOut] = []
    import_success_rate: float = 0.0
    export_count: int = 0


# =====================================================================
# Enterprise CRM Phase 8 — AI Intelligence & Copilot
# =====================================================================

class AiInsightOut(BaseModel):
    id: int
    insight_type: str
    entity_type: str = ""
    entity_id: str = ""
    title: str
    detail: str = ""
    severity: str
    confidence: str
    status: str
    generated_at: datetime | None = None
    created_at: datetime | None = None


class AiInsightPatch(BaseModel):
    status: str


class AiRecommendationOut(BaseModel):
    id: int
    recommendation_type: str
    entity_type: str = ""
    entity_id: str = ""
    title: str
    detail: str = ""
    priority: str = "medium"
    status: str
    generated_at: datetime | None = None
    dismissed_at: datetime | None = None
    completed_at: datetime | None = None
    completed_by: int | None = None


class AiRiskScoreOut(BaseModel):
    id: int
    risk_type: str
    entity_type: str = ""
    entity_id: str = ""
    score: float = 0.0
    severity: str
    detail: dict = {}
    generated_at: datetime | None = None


class AiEngagementScoreOut(BaseModel):
    id: int
    entity_type: str = ""
    entity_id: str = ""
    score: float = 0.0
    email_activity_score: float = 0.0
    meeting_activity_score: float = 0.0
    task_completion_score: float = 0.0
    trend: str
    computed_at: datetime | None = None


class AiBriefingOut(BaseModel):
    id: int
    period: str = ""
    sections: dict = {}
    generated_by: int | None = None
    generated_at: datetime | None = None


class AiCopilotSummaryOut(BaseModel):
    query_type: str
    entity_type: str = ""
    entity_id: str = ""
    summary: str
    generated_at: datetime


class AiGenerationResultOut(BaseModel):
    generated: int = 0


class AiDashboardOut(BaseModel):
    active_insights: int = 0
    pending_recommendations: int = 0
    active_risks: int = 0
    latest_briefing: AiBriefingOut | None = None
    avg_engagement_score: float | None = None
    recent_ai_activity: list[AiInsightOut] = []


class AiRecommendationAcceptanceOut(BaseModel):
    recommendation_type: str
    total: int = 0
    completed: int = 0
    dismissed: int = 0
    acceptance_rate: float = 0.0


class AiAnalyticsOut(BaseModel):
    insight_counts: dict[str, int] = {}
    recommendation_acceptance: list[AiRecommendationAcceptanceOut] = []
    risk_distribution: dict[str, int] = {}
    avg_engagement_score: float | None = None
    engagement_trend_counts: dict[str, int] = {}
    copilot_usage_by_type: dict[str, int] = {}
    executive_briefings_generated: int = 0


# =====================================================================
# Enterprise CRM Phase 9 — Enterprise Administration, Security & Compliance
# =====================================================================

class OrganizationCreate(BaseModel):
    name: str
    slug: str
    industry: str = ""
    size: str = ""
    settings: dict = {}
    feature_flags: dict = {}


class OrganizationPatch(BaseModel):
    name: str | None = None
    industry: str | None = None
    size: str | None = None
    settings: dict | None = None
    feature_flags: dict | None = None


class OrganizationOut(BaseModel):
    id: int
    name: str
    slug: str
    industry: str = ""
    size: str = ""
    settings: dict = {}
    feature_flags: dict = {}
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OrgUnitCreate(BaseModel):
    name: str
    unit_type: str
    parent_id: int | None = None
    lead_user_id: int | None = None


class OrgUnitPatch(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    lead_user_id: int | None = None


class OrgUnitOut(BaseModel):
    id: int
    organization_id: int
    name: str
    unit_type: str
    parent_id: int | None = None
    lead_user_id: int | None = None
    member_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OrgUnitMemberIn(BaseModel):
    user_id: int
    role: str = "member"


class OrgUnitMemberOut(BaseModel):
    id: int
    unit_id: int
    user_id: int
    user_email: str = ""
    role: str
    created_at: datetime | None = None


class SystemSettingIn(BaseModel):
    category: str
    key: str
    value: dict = {}


class SystemSettingOut(BaseModel):
    id: int
    category: str
    key: str
    value: dict = {}
    updated_by: int | None = None
    updated_at: datetime | None = None


class SecurityPolicyIn(BaseModel):
    policy_type: str
    config: dict = {}
    is_enabled: bool = True


class SecurityPolicyOut(BaseModel):
    id: int
    policy_type: str
    config: dict = {}
    is_enabled: bool = True
    updated_by: int | None = None
    updated_at: datetime | None = None


class AuditEventOut(BaseModel):
    id: int
    category: str
    action: str
    actor_id: int | None = None
    actor_email: str = ""
    entity_type: str = ""
    entity_id: str = ""
    detail: dict = {}
    ip_address: str = ""
    created_at: datetime


class ComplianceRecordCreate(BaseModel):
    record_type: str
    entity_type: str = ""
    entity_id: str = ""
    detail: dict = {}


class ComplianceRecordPatch(BaseModel):
    status: str


class ComplianceRecordOut(BaseModel):
    id: int
    record_type: str
    entity_type: str = ""
    entity_id: str = ""
    status: str
    requested_by: int | None = None
    detail: dict = {}
    requested_at: datetime | None = None
    resolved_at: datetime | None = None


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = []
    expires_at: datetime | None = None


class ApiKeyCreatedOut(BaseModel):
    id: int
    name: str
    api_key: str  # shown once, at creation only
    key_prefix: str
    scopes: list[str] = []
    status: str
    expires_at: datetime | None = None
    created_at: datetime | None = None


class ApiKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    scopes: list[str] = []
    owner_id: int | None = None
    status: str
    request_count: int = 0
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    created_at: datetime | None = None
    revoked_at: datetime | None = None


class QueueStatusOut(BaseModel):
    scheduled: int = 0
    queued: int = 0
    sending: int = 0
    failed: int = 0


class IntegrationStatusOut(BaseModel):
    name: str
    configured: bool


class SystemHealthOut(BaseModel):
    api_usage_total: int = 0
    workflow_executions: int = 0
    workflow_success_rate: float = 0.0
    queue_status: QueueStatusOut
    scheduler_healthy: bool = True
    integrations: list[IntegrationStatusOut] = []


class AdminDashboardOut(BaseModel):
    active_users: int = 0
    total_organizations: int = 0
    api_usage_total: int = 0
    security_events_24h: int = 0
    audit_events_24h: int = 0
    pending_compliance_requests: int = 0
    system_health: SystemHealthOut


class AdminAnalyticsOut(BaseModel):
    user_growth_by_period: dict[str, int] = {}
    login_activity_by_period: dict[str, int] = {}
    audit_volume_by_category: dict[str, int] = {}
    api_utilization: dict[str, int] = {}
    workflow_utilization: dict[str, int] = {}
    security_events_by_type: dict[str, int] = {}
    compliance_stats: dict[str, int] = {}


# =====================================================================
# Enterprise CRM Phase 10 — Integration Platform & Developer Ecosystem
# =====================================================================

class IntegrationCreate(BaseModel):
    name: str
    provider: str = ""
    category: str
    version: str = "1.0.0"
    configuration: dict = {}


class IntegrationPatch(BaseModel):
    status: str | None = None
    version: str | None = None
    configuration: dict | None = None
    health_status: str | None = None


class IntegrationOut(BaseModel):
    id: int
    name: str
    provider: str = ""
    category: str
    status: str
    version: str = "1.0.0"
    configuration: dict = {}
    health_status: str = "unknown"
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WebhookCreate(BaseModel):
    name: str
    event_type: str
    target_url: str
    retry_policy: dict = {}


class WebhookPatch(BaseModel):
    name: str | None = None
    target_url: str | None = None
    retry_policy: dict | None = None
    status: str | None = None


class WebhookOut(BaseModel):
    id: int
    name: str
    event_type: str
    target_url: str
    retry_policy: dict = {}
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WebhookCreatedOut(WebhookOut):
    secret: str  # shown once, at creation only


class WebhookDeliveryOut(BaseModel):
    id: int
    webhook_id: int
    webhook_name: str = ""
    event_type: str
    payload: dict = {}
    status: str
    response_code: int | None = None
    attempt_count: int = 0
    error_detail: str = ""
    last_attempted_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime | None = None


class OAuthCredentialCreate(BaseModel):
    name: str
    provider: str
    client_id: str = ""
    client_secret: str | None = None  # generated if omitted
    scopes: list[str] = []
    expires_at: datetime | None = None


class OAuthCredentialOut(BaseModel):
    id: int
    name: str
    provider: str
    client_id: str = ""
    scopes: list[str] = []
    owner_id: int | None = None
    status: str
    request_count: int = 0
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    created_at: datetime | None = None
    revoked_at: datetime | None = None


class OAuthCredentialCreatedOut(OAuthCredentialOut):
    client_secret: str  # shown once, at creation/rotation only


class IntegrationEventOut(BaseModel):
    id: int
    category: str
    event_type: str
    entity_type: str = ""
    entity_id: str = ""
    payload: dict = {}
    created_at: datetime | None = None


class EventPublishIn(BaseModel):
    category: str
    event_type: str
    entity_type: str = ""
    entity_id: str = ""
    payload: dict = {}


class ConnectorCreate(BaseModel):
    name: str
    connector_type: str
    config: dict = {}
    schedule_cron: str = ""


class ConnectorPatch(BaseModel):
    name: str | None = None
    config: dict | None = None
    schedule_cron: str | None = None
    status: str | None = None


class ConnectorOut(BaseModel):
    id: int
    name: str
    connector_type: str
    config: dict = {}
    schedule_cron: str = ""
    status: str
    last_run_at: datetime | None = None
    last_run_status: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConnectorRunOut(BaseModel):
    id: int
    connector_id: int
    status: str
    duration_ms: int = 0
    result_detail: dict = {}
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PluginCreate(BaseModel):
    name: str
    version: str = "1.0.0"
    plugin_metadata: dict = {}
    permissions: list[str] = []
    execution_hooks: list[str] = []


class PluginPatch(BaseModel):
    plugin_metadata: dict | None = None
    permissions: list[str] | None = None
    execution_hooks: list[str] | None = None
    status: str | None = None


class PluginOut(BaseModel):
    id: int
    name: str
    version: str = "1.0.0"
    plugin_metadata: dict = {}
    permissions: list[str] = []
    execution_hooks: list[str] = []
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PluginExecutionOut(BaseModel):
    id: int
    plugin_id: int
    hook_name: str
    status: str
    detail: dict = {}
    executed_at: datetime | None = None


class ConnectorHealthOut(BaseModel):
    connector_id: int
    name: str
    connector_type: str
    status: str
    last_run_status: str = ""
    last_run_at: datetime | None = None


class IntegrationDashboardOut(BaseModel):
    active_integrations: int = 0
    webhook_deliveries_total: int = 0
    failed_deliveries: int = 0
    connector_health: list[ConnectorHealthOut] = []
    api_usage_total: int = 0
    plugin_status: dict[str, int] = {}


class IntegrationAnalyticsOut(BaseModel):
    api_requests_total: int = 0
    webhook_success_rate: float = 0.0
    retry_rate: float = 0.0
    connector_usage: dict[str, int] = {}
    plugin_usage: dict[str, int] = {}
    integration_health: dict[str, int] = {}


# =====================================================================
# Enterprise CRM Phase 11 — Enterprise Search & Knowledge Platform
# =====================================================================

class SearchResultOut(BaseModel):
    entity_type: str
    entity_id: str
    title: str
    snippet: str = ""
    score: float = 0.0


class SearchResponseOut(BaseModel):
    query: str
    results: list[SearchResultOut] = []
    total: int = 0
    response_time_ms: int = 0


class SavedSearchCreate(BaseModel):
    name: str
    query: dict
    is_favorite: bool = False
    is_shared: bool = False


class SavedSearchPatch(BaseModel):
    name: str | None = None
    query: dict | None = None
    is_favorite: bool | None = None
    is_shared: bool | None = None


class SavedSearchOut(BaseModel):
    id: int
    name: str
    query: dict = {}
    owner_id: int | None = None
    is_favorite: bool = False
    is_shared: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SearchHistoryOut(BaseModel):
    id: int
    query_text: str = ""
    entity_types: list[str] = []
    result_count: int = 0
    response_time_ms: int = 0
    created_at: datetime | None = None


class KbCategoryCreate(BaseModel):
    name: str
    description: str = ""
    parent_id: int | None = None


class KbCategoryPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    parent_id: int | None = None


class KbCategoryOut(BaseModel):
    id: int
    name: str
    description: str = ""
    parent_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KbArticleCreate(BaseModel):
    title: str
    body: str = ""
    category_id: int | None = None
    tags: list[str] = []


class KbArticlePatch(BaseModel):
    title: str | None = None
    body: str | None = None
    category_id: int | None = None
    tags: list[str] | None = None
    status: str | None = None


class KbArticleOut(BaseModel):
    id: int
    category_id: int | None = None
    title: str
    body: str = ""
    status: str
    tags: list[str] = []
    owner_id: int | None = None
    version: int = 1
    view_count: int = 0
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    published_at: datetime | None = None


class KbArticleVersionOut(BaseModel):
    id: int
    article_id: int
    version: int
    title: str = ""
    body: str = ""
    edited_by: int | None = None
    created_at: datetime | None = None


class KbAttachmentCreate(BaseModel):
    filename: str
    content_type: str = ""
    size_bytes: int = 0


class KbAttachmentOut(BaseModel):
    id: int
    article_id: int
    filename: str
    content_type: str = ""
    size_bytes: int = 0
    uploaded_by: int | None = None
    created_at: datetime | None = None


class RelatedArticleOut(BaseModel):
    article_id: int
    title: str
    score: float = 0.0
    reason: str = ""


class KnowledgeSummaryOut(BaseModel):
    article_id: int
    title: str
    summary: str
    tags: list[str] = []
    view_count: int = 0


class ContextSuggestionOut(BaseModel):
    entity_type: str
    entity_id: str
    articles: list[RelatedArticleOut] = []


class SearchDashboardOut(BaseModel):
    recent_searches: list[SearchHistoryOut] = []
    popular_searches: list[str] = []
    knowledge_activity: dict[str, int] = {}
    avg_response_time_ms: float = 0.0
    top_articles: list[KbArticleOut] = []


class SearchAnalyticsOut(BaseModel):
    search_volume: int = 0
    zero_result_searches: int = 0
    popular_records: dict[str, int] = {}
    article_views: dict[str, int] = {}
    article_usage: dict[str, int] = {}
    avg_search_response_ms: float = 0.0


# =====================================================================
# Enterprise CRM Phase 12 — Data Warehouse & Advanced Business Intelligence
# =====================================================================

class WarehouseSnapshotOut(BaseModel):
    id: int
    metric_type: str
    snapshot_date: datetime
    metrics: dict = {}
    created_at: datetime | None = None


class WarehouseRefreshResultOut(BaseModel):
    snapshots_created: int = 0


class KpiCreate(BaseModel):
    name: str
    category: str
    target_value: float | None = None
    unit: str = ""


class KpiPatch(BaseModel):
    target_value: float | None = None
    unit: str | None = None


class KpiOut(BaseModel):
    id: int
    name: str
    category: str
    target_value: float | None = None
    unit: str = ""
    current_value: float | None = None
    status: str = "no_target"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KpiValueIn(BaseModel):
    value: float


class KpiValueOut(BaseModel):
    id: int
    kpi_id: int
    value: float
    recorded_at: datetime | None = None


class TrendPointOut(BaseModel):
    period: str
    value: float


class TrendOut(BaseModel):
    metric: str
    points: list[TrendPointOut] = []
    growth_rate: float | None = None


class CustomReportCreate(BaseModel):
    name: str
    entity_type: str
    filters: dict = {}
    group_by: str = ""


class CustomReportPatch(BaseModel):
    name: str | None = None
    filters: dict | None = None
    group_by: str | None = None
    status: str | None = None


class CustomReportOut(BaseModel):
    id: int
    name: str
    entity_type: str
    filters: dict = {}
    group_by: str = ""
    status: str
    owner_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CustomReportResultOut(BaseModel):
    report_id: int
    columns: list[str] = []
    rows: list[dict] = []
    total_rows: int = 0


class ReportScheduleCreate(BaseModel):
    frequency: str
    recipient_emails: list[str] = []
    is_enabled: bool = True


class ReportSchedulePatch(BaseModel):
    frequency: str | None = None
    recipient_emails: list[str] | None = None
    is_enabled: bool | None = None


class ReportScheduleOut(BaseModel):
    id: int
    report_id: int
    frequency: str
    recipient_emails: list[str] = []
    is_enabled: bool = True
    last_run_at: datetime | None = None
    created_at: datetime | None = None


class ScheduledReportRunOut(BaseModel):
    id: int
    schedule_id: int
    status: str
    row_count: int = 0
    detail: str = ""
    run_at: datetime | None = None


class BiExecutiveDashboardOut(BaseModel):
    dashboard_type: str
    metrics: dict = {}
    generated_at: datetime


class BiDashboardOut(BaseModel):
    kpis: list[KpiOut] = []
    trends: list[TrendOut] = []
    executive_metrics: dict[str, dict] = {}
    scheduled_reports_count: int = 0
    warehouse_snapshots_count: int = 0
    data_freshness: datetime | None = None


class BiAnalyticsOut(BaseModel):
    kpi_achievement: dict[str, float] = {}
    growth_rates: dict[str, float] = {}
    forecast_trends: dict[str, float] = {}
    report_usage: dict[str, int] = {}
    dashboard_usage: dict[str, int] = {}
    warehouse_statistics: dict[str, int] = {}


# --------------------------------------------------- scheduler / run history
class ExecutionStageOut(BaseModel):
    component: str
    status: str = ""
    processed: int = 0
    created: int = 0
    updated: int = 0
    review: int = 0
    duration_ms: int = 0
    errors: list[str] = []
    notes: str = ""


class ExecutionOut(_ORM):
    id: int
    run_id: str
    trigger: str
    scheduled_slot: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int = 0
    status: str
    records_processed: int = 0
    failure_count: int = 0
    warning_count: int = 0
    stages: list[ExecutionStageOut] = []
    totals: dict[str, int] = {}
    notification_status: str = "pending"
    notification_detail: str = ""
    notified_count: int = 0
    created_at: datetime | None = None


class SchedulerStatusOut(BaseModel):
    enabled: bool
    running: bool
    schedule_times: list[str] = []
    grace_minutes: int = 0
    next_run: datetime | None = None
    notify_mode: str = "auto"
    notify_configured: bool = False
    active_recipient_count: int = 0
    is_run_in_progress: bool = False
    last_run: ExecutionOut | None = None


class RunNowResult(BaseModel):
    status: str          # accepted | busy
    detail: str = ""
    run_id: str | None = None


# Resolve forward references now that the referenced models are all defined.
DecisionMakerDetailOut.model_rebuild()
DealIntelligenceOut.model_rebuild()
WorkQueueOut.model_rebuild()
