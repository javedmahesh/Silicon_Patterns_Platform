"""SQLAlchemy ORM models for the master database.

These MIRROR ``master_db/migrations/*.sql`` (the source of truth). They give the
resolver and the P1 ingestors a portable, testable data layer:
``Base.metadata.create_all`` builds the same tables on a local SQLite file, so
the platform runs and is unit-tested offline with no Supabase.

Postgres-only niceties in the migrations (``jsonb``, ``GENERATED ... IDENTITY``,
``gin_trgm_ops``, the ``updated_at`` trigger) degrade cleanly here: ``JSON`` maps
to TEXT on SQLite, identity becomes autoincrement, and ``updated_at`` is stamped
in Python via ``onupdate``.

If you change a column here, change the matching migration too (and vice versa).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from functools import cached_property

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config.enums import (
    signal_category_for,
    AI_COPILOT_QUERY_TYPES,
    AI_INSIGHT_SEVERITIES,
    AI_INSIGHT_STATUSES,
    AI_INSIGHT_TYPES,
    AI_RECOMMENDATION_STATUSES,
    AI_RECOMMENDATION_TYPES,
    AI_RISK_TYPES,
    API_KEY_STATUSES,
    ASSIGNMENT_STATUSES,
    AUDIT_CATEGORIES,
    COMPLIANCE_RECORD_TYPES,
    COMPLIANCE_STATUSES,
    DISCOVERY_CANDIDATE_STATUSES,
    MARKET_INTELLIGENCE_PRIORITIES,
    NOTIFICATION_DELIVERY_STATUSES,
    ORG_UNIT_MEMBER_ROLES,
    ORG_UNIT_TYPES,
    SECURITY_POLICY_TYPES,
    SETTINGS_CATEGORIES,
    CAMPAIGN_MEMBER_STATUSES,
    COLLAB_ASSIGNMENT_ACTIONS,
    COLLAB_ENTITY_TYPES,
    COLLAB_NOTIF_TYPES,
    COLLAB_ROLES,
    SAVED_VIEW_ENTITY_TYPES,
    CAMPAIGN_OUTCOMES,
    CAMPAIGN_STATUSES,
    CAMPAIGN_TYPES,
    COMPANY_TIERS,
    IMPORT_JOB_STATUSES,
    REVIEW_CATEGORIES,
    REVIEW_KINDS,
    REVIEW_STATES,
    CS_ACCOUNT_STATUSES,
    CS_ACCOUNT_TIERS,
    CS_CONTACT_ROLES,
    CS_CONTRACT_STATUSES,
    CS_HEALTH_GRADES,
    CS_HEALTH_TRENDS,
    CS_LIFECYCLE_STAGES,
    CS_MILESTONE_STATUSES,
    CS_PLAN_STATUSES,
    CS_RISK_SEVERITIES,
    CS_RISK_STATUSES,
    DEAL_CURRENCIES,
    DEAL_FORECAST_CATEGORIES,
    DEAL_PIPELINE_STAGE_TYPES,
    COMPLIANCE_FLAGS,
    CONFIDENCE_LEVELS,
    DM_JOB_ITEM_STATUSES,
    DM_JOB_STATUSES,
    DM_NOTE_TYPES,
    EMAIL_ATTACHMENT_STATUSES,
    EMAIL_CONNECTION_STATUSES,
    EMAIL_LABEL_COLORS,
    EMAIL_PROVIDER_TYPES,
    GMAIL_SYNC_STATUSES,
    LEAD_GRADES,
    LEAD_REVIEW_STATUSES,
    LEADERSHIP_MOVEMENT_TYPES,
    LEADERSHIP_PRIORITY_TIERS,
    LEADERSHIP_SENIORITY_BANDS,
    LEADERSHIP_SIGNAL_SOURCES,
    MATCH_TYPES,
    OUTREACH_ACTIVITY_TYPES,
    OUTREACH_LEAD_SOURCES,
    OUTREACH_MEETING_OUTCOMES,
    OUTREACH_MEETING_TYPES,
    OUTREACH_MESSAGE_DIRECTIONS,
    OUTREACH_MESSAGE_STATUSES,
    OUTREACH_SERVICE_LINES,
    OUTREACH_STAGES,
    OUTREACH_TASK_PRIORITIES,
    OUTREACH_TASK_STATUSES,
    EXECUTION_STATUSES,
    EXECUTION_TRIGGERS,
    PIPELINE_STATUSES,
    PROSPECT_TYPES,
    CUSTOM_DATA_JOB_STATUSES,
    CUSTOM_DATA_JOB_TYPES,
    CUSTOM_FIELD_TYPES,
    CUSTOM_OBJECT_STATUSES,
    CUSTOM_RECORD_AUDIT_ACTIONS,
    CONNECTOR_RUN_STATUSES,
    CONNECTOR_STATUSES,
    CONNECTOR_TYPES,
    EVENT_BUS_CATEGORIES,
    INTEGRATION_CATEGORIES,
    INTEGRATION_HEALTH_STATUSES,
    INTEGRATION_STATUSES,
    OAUTH_CREDENTIAL_STATUSES,
    PLUGIN_EXECUTION_STATUSES,
    PLUGIN_STATUSES,
    WEBHOOK_DELIVERY_STATUSES,
    WEBHOOK_STATUSES,
    KB_ARTICLE_STATUSES,
    KPI_CATEGORIES,
    REPORT_SCHEDULE_FREQUENCIES,
    REPORT_STATUSES,
    SCHEDULED_REPORT_RUN_STATUSES,
    WAREHOUSE_METRIC_TYPES,
    REVIEW_STATUSES,
    REVOPS_FORECAST_SNAPSHOT_CATEGORIES,
    REVOPS_PERIOD_TYPES,
    REVOPS_TARGET_SCOPES,
    SEQUENCE_ENROLLMENT_STATUSES,
    WORKFLOW_APPROVAL_STATUSES,
    WORKFLOW_APPROVAL_TYPES,
    WORKFLOW_EXECUTION_STATUSES,
    WORKFLOW_SLA_STATUSES,
    WORKFLOW_STATUSES,
    WORKFLOW_TRIGGER_EVENTS,
    SEQUENCE_STEP_ACTIONS,
    SEQUENCE_STEP_STATUSES,
    USER_AUDIT_ACTIONS,
    USER_ROLES,
    USER_STATUSES,
    VALIDATION_STATUSES,
    ML_ENTITY_TYPES,
    ML_INTERACTION_TYPES,
    ML_MODEL_STATUSES,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _in(column: str, values: tuple[str, ...]) -> str:
    """Render a portable ``CHECK col IN (...)`` clause body."""
    rendered = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({rendered})"


def _coerce_str(value) -> str | None:
    """Normalize a profile_data value to a display string, or None when empty.

    Lists (e.g. skills/languages) become a comma-joined string; everything else
    is stringified. Used by the read-only enrichment views over ``profile_data``
    so callers never have to know whether the actor returned a scalar or a list.
    """
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        parts = [str(v).strip() for v in value if str(v).strip()]
        return ", ".join(parts) or None
    if isinstance(value, dict):
        return None  # nested objects aren't directly displayable
    s = str(value).strip()
    return s or None


class Base(DeclarativeBase):
    pass


# =====================================================================
# Resolution-layer tables (mirror 0001_foundations.sql)
# =====================================================================
class Company(Base):
    """Master company record. Owned by Industry Discovery; the resolver may also
    create low-confidence *stub* rows (``is_stub=True``, ``validation_status='STUB'``)
    for domains seen by other engines before Industry Discovery has catalogued them.

    Primary key is the normalized ``company_domain`` — the universal join key.
    """

    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint(_in("company_tier", COMPANY_TIERS), name="ck_companies_tier"),
        CheckConstraint(_in("prospect_type", PROSPECT_TYPES), name="ck_companies_prospect"),
        CheckConstraint(_in("compliance_flag", COMPLIANCE_FLAGS), name="ck_companies_compliance"),
        CheckConstraint(_in("validation_status", VALIDATION_STATUSES), name="ck_companies_validation"),
        CheckConstraint(
            "company_domain = lower(company_domain) "
            "AND company_domain NOT LIKE '%/%' "
            "AND company_domain LIKE '%.%'",
            name="ck_companies_domain_normalized",
        ),
        Index("ix_companies_name_key", "name_key"),
        Index("ix_companies_canonical_id", "canonical_company_id"),
    )

    company_domain: Mapped[str] = mapped_column(String(255), primary_key=True)
    canonical_company_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    name_key: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    website: Mapped[str] = mapped_column(String(512), default="")
    company_linkedin: Mapped[str] = mapped_column(String(255), default="")
    country: Mapped[str] = mapped_column(String(120), default="")
    city: Mapped[str] = mapped_column(String(120), default="")
    headquarters: Mapped[str] = mapped_column(String(255), default="")
    compliance_flag: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    industry_category: Mapped[str] = mapped_column(String(120), default="")
    sub_category: Mapped[str] = mapped_column(String(120), default="")
    industry_type: Mapped[str] = mapped_column(String(80), default="")
    technology_focus: Mapped[str] = mapped_column(String(255), default="")
    prospect_type: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    company_tier: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    company_status: Mapped[str] = mapped_column(String(20), default="")
    company_type: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    description: Mapped[str] = mapped_column(Text, default="")
    founded_year: Mapped[str] = mapped_column(String(8), default="")
    source: Mapped[str] = mapped_column(String(255), default="")
    source_type: Mapped[str] = mapped_column(String(60), default="")
    discovery_date: Mapped[str] = mapped_column(String(32), default="")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    validation_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    is_stub: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    aliases: Mapped[list["CompanyAlias"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class CompanyAlias(Base):
    """Name → domain mapping that powers canonical resolution."""

    __tablename__ = "company_aliases"
    __table_args__ = (
        UniqueConstraint("name_key", "company_domain", name="uq_alias_namekey_domain"),
        Index("ix_aliases_name_key", "name_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    name_key: Mapped[str] = mapped_column(String(255), nullable=False)
    company_domain: Mapped[str] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(60), default="")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    company: Mapped["Company"] = relationship(back_populates="aliases")


class CompanySource(Base):
    """Provenance: every source that surfaced a given company."""

    __tablename__ = "company_sources"
    __table_args__ = (
        UniqueConstraint("company_domain", "source_name", name="uq_company_source"),
        Index("ix_company_sources_domain", "company_domain"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_domain: Mapped[str] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), nullable=False
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(60), default="")
    source_tier: Mapped[int] = mapped_column(Integer, default=99)
    source_url: Mapped[str] = mapped_column(String(512), default="")
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ResolutionReviewQueue(Base):
    """Records that could not be resolved confidently (or that produced a new
    stub) — parked for a human to confirm/merge. The pipeline never blocks."""

    __tablename__ = "resolution_review_queue"
    __table_args__ = (
        CheckConstraint(_in("match_type", MATCH_TYPES), name="ck_review_match_type"),
        CheckConstraint(_in("status", REVIEW_STATUSES), name="ck_review_status"),
        Index("ix_review_status", "status"),
        Index("ix_review_source_engine", "source_engine"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_name: Mapped[str] = mapped_column(String(255), default="")
    raw_domain: Mapped[str] = mapped_column(String(255), default="")
    raw_website: Mapped[str] = mapped_column(String(512), default="")
    source_engine: Mapped[str] = mapped_column(String(40), default="")
    source_record_ref: Mapped[str] = mapped_column(String(512), default="")
    suggested_domain: Mapped[str] = mapped_column(String(255), default="")
    match_type: Mapped[str] = mapped_column(String(20), default="UNRESOLVED")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    resolved_domain: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# =====================================================================
# Engine-owned tables (mirror 0002_engine_tables.sql)
# =====================================================================
class Opportunity(Base):
    """One row per article / market event. Owned by the Blog Crawler."""

    __tablename__ = "opportunities"
    __table_args__ = (
        Index("ix_opportunities_domain", "company_domain"),
        Index("ix_opportunities_type", "opportunity_type"),
        Index("ix_opportunities_validation", "validation_status"),
        Index("ix_opportunities_eff_score", "effective_opportunity_score"),
        Index("ix_opportunities_signal_category", "signal_category"),
        Index("ix_opportunities_priority", "priority_tier"),
        CheckConstraint(_in("priority_tier", LEADERSHIP_PRIORITY_TIERS), name="ck_opp_priority_tier"),
    )

    opportunity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_domain: Mapped[str] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), nullable=False
    )
    canonical_company_id: Mapped[str] = mapped_column(String(64), default="")
    company_name: Mapped[str] = mapped_column(String(255), default="")
    company_tier: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    prospect_type: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    country: Mapped[str] = mapped_column(String(120), default="")
    compliance_flag: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    article_title: Mapped[str] = mapped_column(Text, default="")
    article_url: Mapped[str] = mapped_column(String(1024), default="")
    source: Mapped[str] = mapped_column(String(255), default="")
    source_type: Mapped[str] = mapped_column(String(60), default="")
    published_date: Mapped[str] = mapped_column(String(64), default="")
    event_age_days: Mapped[int] = mapped_column(Integer, default=-1)
    opportunity_type: Mapped[str] = mapped_column(String(64), default="")
    opportunity_category: Mapped[str] = mapped_column(String(64), default="")
    # First-class signal category (LEADERSHIP | NEWS), derived from opportunity_type
    # and kept in sync by the ORM listener below (so every writer — the news engine,
    # every ingestor, tests — agrees) plus the migration backfill. Leadership
    # people-movement events are separated OUT of the general NEWS feed everywhere.
    signal_category: Mapped[str] = mapped_column(String(20), default="NEWS")
    # One-line human-readable signal (Change_04 annual-list rank "Rank: N"; shared with
    # Change_03 company-news moves). Added by migration 0016.
    company_news_signal: Mapped[str] = mapped_column(String(512), default="")
    funding_stage: Mapped[str] = mapped_column(String(64), default="")
    funding_amount: Mapped[str] = mapped_column(String(64), default="")
    product_mentioned: Mapped[str] = mapped_column(String(255), default="")
    technology_mentioned: Mapped[str] = mapped_column(String(255), default="")
    technology_focus: Mapped[str] = mapped_column(String(255), default="")
    conference_mentioned: Mapped[str] = mapped_column(String(255), default="")
    partnership_mentioned: Mapped[str] = mapped_column(String(255), default="")
    expansion_mentioned: Mapped[str] = mapped_column(String(255), default="")
    partner_company: Mapped[str] = mapped_column(String(255), default="")
    foundry_partner: Mapped[str] = mapped_column(String(120), default="")
    eda_partner: Mapped[str] = mapped_column(String(120), default="")
    opportunity_score: Mapped[int] = mapped_column(Integer, default=0)
    effective_opportunity_score: Mapped[int] = mapped_column(Integer, default=0)
    recency_weight: Mapped[float] = mapped_column(Float, default=1.0)
    confidence_score: Mapped[int] = mapped_column(Integer, default=0)
    lead_readiness_score: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    validation_status: Mapped[str] = mapped_column(String(30), default="REVIEW_REQUIRED")
    source_tier: Mapped[int] = mapped_column(Integer, default=0)
    discovery_date: Mapped[str] = mapped_column(String(32), default="")

    # --- News Intelligence: rich AI extraction (migration 0044) --------------
    # Deterministic, evidence-grounded extraction (no external LLM) — reuses the
    # platform's rules-based "AI" style. Additive & NULL/default-backfilled, so
    # every pre-0044 opportunity keeps working (the fields are simply blank).
    executive_summary: Mapped[str] = mapped_column(Text, default="")
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    why_this_matters: Mapped[str] = mapped_column(Text, default="")
    business_impact: Mapped[str] = mapped_column(Text, default="")
    ai_reasoning: Mapped[str] = mapped_column(Text, default="")
    opportunity_subtype: Mapped[str] = mapped_column(String(64), default="")
    # Extracted entities (JSON lists of strings).
    technologies: Mapped[list] = mapped_column(JSON, default=list)
    products: Mapped[list] = mapped_column(JSON, default=list)
    people: Mapped[list] = mapped_column(JSON, default=list)
    organizations: Mapped[list] = mapped_column(JSON, default=list)
    countries: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    # Per-factor confidence breakdown ({factor: 0..100}); source_credibility 0..100.
    confidence_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    source_credibility: Mapped[int] = mapped_column(Integer, default=0)
    # Lifecycle (NEW/ACTIVE/MONITORING/RESOLVED/ARCHIVED); independent of AI outputs.
    lifecycle_status: Mapped[str] = mapped_column(String(20), default="NEW")
    # Manual review: not_relevant flips this (AI outputs preserved); merged_into set
    # when this row was folded into another opportunity.
    is_relevant: Mapped[bool] = mapped_column(Boolean, default=True)
    merged_into: Mapped[str] = mapped_column(String(64), default="")
    # Dedup / relationship keys.
    canonical_url: Mapped[str] = mapped_column(String(1024), default="")
    normalized_title: Mapped[str] = mapped_column(String(512), default="")
    entity_fingerprint: Mapped[str] = mapped_column(String(64), default="")
    related_group_id: Mapped[str] = mapped_column(String(64), default="")
    # New Project Intelligence (migration 0055): article-derived location (India-city
    # aware, "" when none) and buying-intent priority tier for PROJECT_INTEL rows
    # (integration/news/project_intel.py). Additive/defaulted — every existing row and
    # every non-project opportunity is unaffected (priority_tier stays 'medium').
    geography: Mapped[str] = mapped_column(String(120), default="")
    priority_tier: Mapped[str] = mapped_column(String(10), default="medium")

    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    sources: Mapped[list["OpportunityArticle"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan",
        order_by="OpportunityArticle.published_at.desc()",
    )
    reviews: Mapped[list["OpportunityReview"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan",
        order_by="OpportunityReview.created_at.desc()",
    )


@event.listens_for(Opportunity, "before_insert")
@event.listens_for(Opportunity, "before_update")
def _sync_opportunity_signal_category(_mapper, _conn, target: "Opportunity") -> None:
    """Keep signal_category derived from opportunity_type on every write, so the
    LEADERSHIP vs NEWS split is consistent no matter which writer created the row
    (news engine, company_news / blog / annual_list ingestors, tests) — one place,
    no per-writer drift. See config.enums.signal_category_for + migration 0047."""
    target.signal_category = signal_category_for(target.opportunity_type)


_PUBLISHED_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def normalize_published_date(value: str | None) -> str:
    """Best-effort feed date -> ``YYYY-MM-DD`` so opportunities sort and filter
    chronologically no matter how a source phrased it: ISO datetime, ISO date,
    ``YYYY-MM``, bare ``YYYY``, ``Month D, YYYY``, or ``D Month YYYY``. A blank or
    unparseable value is returned as its trimmed self — a date is never invented."""
    s = (value or "").strip()
    if not s:
        return ""
    # ISO date or datetime -> keep the date part.
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # YYYY-MM -> first of month.
    m = re.fullmatch(r"(\d{4})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-01"
    # Bare YYYY (e.g. an annual-list year) -> Jan 1.
    m = re.fullmatch(r"(\d{4})", s)
    if m:
        return f"{m.group(1)}-01-01"
    # "Month D, YYYY" / "Mon. D YYYY" (comma optional).
    m = re.match(r"([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})", s)
    if m and m.group(1)[:3].lower() in _PUBLISHED_MONTHS:
        return f"{int(m.group(3)):04d}-{_PUBLISHED_MONTHS[m.group(1)[:3].lower()]:02d}-{int(m.group(2)):02d}"
    # "D Month YYYY".
    m = re.match(r"(\d{1,2})\s+([A-Za-z]{3,9})\.?\s+(\d{4})", s)
    if m and m.group(2)[:3].lower() in _PUBLISHED_MONTHS:
        return f"{int(m.group(3)):04d}-{_PUBLISHED_MONTHS[m.group(2)[:3].lower()]:02d}-{int(m.group(1)):02d}"
    return s


@event.listens_for(Opportunity, "before_insert")
@event.listens_for(Opportunity, "before_update")
def _normalize_opportunity_published_date(_mapper, _conn, target: "Opportunity") -> None:
    """Normalize published_date to ISO ``YYYY-MM-DD`` on every write so the
    Opportunities newest/oldest sort and date-range filters are chronologically
    correct regardless of which writer created the row. The news engine already
    emits ISO; this makes every other writer (blog / annual_list / company_news
    ingestors, tests) consistent — one place, no per-writer drift."""
    target.published_date = normalize_published_date(target.published_date)


class NewsSource(Base):
    """A configured news feed the News Collection Engine pulls from.

    ``adapter_type`` selects the parser (rss / google_alerts / file / manual).
    Credibility (0..100) seeds each collected article's source_credibility.
    """

    __tablename__ = "news_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    adapter_type: Mapped[str] = mapped_column(String(30), default="rss")
    url: Mapped[str] = mapped_column(String(1024), default="")
    publisher: Mapped[str] = mapped_column(String(255), default="")
    credibility: Mapped[int] = mapped_column(Integer, default=50)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        CheckConstraint(
            "adapter_type in ('rss','google_alerts','file','manual')",
            name="ck_news_sources_adapter",
        ),
    )


class NewsArticle(Base):
    """One collected article (raw, pre-extraction) with its source metadata.

    Deduplicated by ``content_hash`` (canonical-url + normalized-title). One article
    can yield several opportunities (multi-signal extraction) — the link rows in
    ``opportunity_articles`` carry that many-to-many relationship.
    """

    __tablename__ = "news_articles"
    __table_args__ = (
        Index("ix_news_articles_domain", "company_domain"),
        Index("ix_news_articles_canonical", "canonical_url"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("news_sources.id", ondelete="SET NULL"), nullable=True
    )
    adapter_type: Mapped[str] = mapped_column(String(30), default="file")
    publisher: Mapped[str] = mapped_column(String(255), default="")
    source_name: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(String(1024), default="")
    canonical_url: Mapped[str] = mapped_column(String(1024), default="")
    title: Mapped[str] = mapped_column(Text, default="")
    normalized_title: Mapped[str] = mapped_column(String(512), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    company_domain: Mapped[str] = mapped_column(String(255), default="")
    company_name: Mapped[str] = mapped_column(String(255), default="")
    entities: Mapped[dict] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), default="", unique=True)
    published_at: Mapped[str] = mapped_column(String(64), default="")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)


class OpportunityArticle(Base):
    """Link row: one reporting source (article) under one opportunity.

    Intelligent dedup stores EVERY source that reported the same business event as a
    separate row here (all under one opportunity), while multi-signal extraction links
    ONE article to several opportunities. Unique on (opportunity_id, canonical_url).
    """

    __tablename__ = "opportunity_articles"
    __table_args__ = (
        UniqueConstraint("opportunity_id", "canonical_url", name="uq_opp_article_url"),
        Index("ix_opp_articles_opp", "opportunity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunities.opportunity_id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[int | None] = mapped_column(
        ForeignKey("news_articles.id", ondelete="SET NULL"), nullable=True
    )
    url: Mapped[str] = mapped_column(String(1024), default="")
    canonical_url: Mapped[str] = mapped_column(String(1024), default="")
    publisher: Mapped[str] = mapped_column(String(255), default="")
    source_name: Mapped[str] = mapped_column(String(255), default="")
    source_type: Mapped[str] = mapped_column(String(60), default="")
    title: Mapped[str] = mapped_column(Text, default="")
    credibility: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[str] = mapped_column(String(64), default="")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    opportunity: Mapped["Opportunity"] = relationship(back_populates="sources")


class OpportunityReview(Base):
    """Append-only manual-review history for an opportunity.

    Records analyst actions (not_relevant / merge / split / change_type / archive /
    restore / note). Snapshots the before/after so AI outputs are never lost — the
    action mutates lifecycle/relevance/type, never the extraction fields.
    """

    __tablename__ = "opportunity_reviews"
    __table_args__ = (
        CheckConstraint(
            "action in ('not_relevant','merge','split','change_type','archive','restore','note')",
            name="ck_opp_review_action",
        ),
        Index("ix_opp_reviews_opp", "opportunity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunities.opportunity_id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    before_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    after_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    opportunity: Mapped["Opportunity"] = relationship(back_populates="reviews")


class Job(Base):
    """One row per posting. Owned by the Career Scraper."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("company_domain", "job_url", name="uq_jobs_domain_url"),
        Index("ix_jobs_domain", "company_domain"),
        Index("ix_jobs_category", "job_category"),
        Index("ix_jobs_seniority", "seniority"),
    )

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_domain: Mapped[str] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(255), default="")
    company_tier: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    job_title: Mapped[str] = mapped_column(String(512), default="")
    job_category: Mapped[str] = mapped_column(String(64), default="")
    department: Mapped[str] = mapped_column(String(255), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    country: Mapped[str] = mapped_column(String(100), default="")
    geo_region: Mapped[str] = mapped_column(String(64), default="")
    employment_type: Mapped[str] = mapped_column(String(64), default="")
    posted_date: Mapped[str] = mapped_column(String(64), default="")
    ats_provider: Mapped[str] = mapped_column(String(64), default="")
    technologies: Mapped[str] = mapped_column(Text, default="")
    seniority: Mapped[str] = mapped_column(String(32), default="")
    engineering_relevance_score: Mapped[int] = mapped_column(Integer, default=0)
    job_url: Mapped[str] = mapped_column(String(1024), default="")
    source_url: Mapped[str] = mapped_column(String(1024), default="")
    scrape_date: Mapped[str] = mapped_column(String(32), default="")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class DemandSignal(Base):
    """One demand rollup per company. Owned by the Career Scraper."""

    __tablename__ = "demand_signals"

    company_domain: Mapped[str] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), primary_key=True
    )
    canonical_company_id: Mapped[str] = mapped_column(String(64), default="")
    company_name: Mapped[str] = mapped_column(String(255), default="")
    country: Mapped[str] = mapped_column(String(100), default="")
    geo_region: Mapped[str] = mapped_column(String(64), default="")
    rtl_jobs: Mapped[int] = mapped_column(Integer, default=0)
    asic_jobs: Mapped[int] = mapped_column(Integer, default=0)
    verification_jobs: Mapped[int] = mapped_column(Integer, default=0)
    physical_design_jobs: Mapped[int] = mapped_column(Integer, default=0)
    dft_jobs: Mapped[int] = mapped_column(Integer, default=0)
    sta_jobs: Mapped[int] = mapped_column(Integer, default=0)
    validation_jobs: Mapped[int] = mapped_column(Integer, default=0)
    fpga_jobs: Mapped[int] = mapped_column(Integer, default=0)
    embedded_jobs: Mapped[int] = mapped_column(Integer, default=0)
    architecture_jobs: Mapped[int] = mapped_column(Integer, default=0)
    total_engineering_jobs: Mapped[int] = mapped_column(Integer, default=0)
    technologies_detected: Mapped[str] = mapped_column(Text, default="")
    primary_focus: Mapped[str] = mapped_column(String(64), default="")
    demand_score: Mapped[float] = mapped_column(Float, default=0.0)
    normalized_demand_score: Mapped[float] = mapped_column(Float, default=0.0)
    demand_signal: Mapped[str] = mapped_column(String(512), default="")
    hiring_trend: Mapped[str] = mapped_column(String(16), default="")
    lead_readiness_score: Mapped[float] = mapped_column(Float, default=0.0)
    newest_job_date: Mapped[str] = mapped_column(String(32), default="")
    hiring_regions: Mapped[str] = mapped_column(String(256), default="")
    india_hiring_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    ats_provider: Mapped[str] = mapped_column(String(64), default="")
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CompanyRollup(Base):
    """Sales-ready demand summary per company (company_intelligence.xlsx).
    Owned by the Career Scraper. ``priority_rank`` here is Career's own A/B/C,
    distinct from ``LeadScore.grade``."""

    __tablename__ = "company_rollups"

    company_domain: Mapped[str] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), primary_key=True
    )
    company_name: Mapped[str] = mapped_column(String(255), default="")
    company_tier: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    country: Mapped[str] = mapped_column(String(100), default="")
    geo_region: Mapped[str] = mapped_column(String(64), default="")
    demand_score: Mapped[float] = mapped_column(Float, default=0.0)
    lead_readiness_score: Mapped[float] = mapped_column(Float, default=0.0)
    demand_signal: Mapped[str] = mapped_column(String(512), default="")
    total_engineering_jobs: Mapped[int] = mapped_column(Integer, default=0)
    primary_focus: Mapped[str] = mapped_column(String(64), default="")
    technologies_detected: Mapped[str] = mapped_column(Text, default="")
    newest_job_date: Mapped[str] = mapped_column(String(32), default="")
    hiring_regions: Mapped[str] = mapped_column(String(256), default="")
    india_hiring_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_rank: Mapped[str] = mapped_column(String(4), default="C")
    next_action: Mapped[str] = mapped_column(String(128), default="")
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class DecisionMaker(Base):
    """A sourced decision maker (LinkedIn or Apify).

    ``company_domain`` is NULLABLE: Apify provides it directly; LinkedIn carries
    no domain natively and the resolver attaches one best-effort. Unresolved rows
    keep NULL and live in the review queue (LinkedIn) or are skipped (Apify).
    """

    __tablename__ = "decision_makers"
    __table_args__ = (
        Index("ix_dm_domain", "company_domain"),
        Index("ix_dm_status", "status"),
        Index("ix_dm_seniority", "seniority"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    linkedin_url: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    company_domain: Mapped[str | None] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="SET NULL"), nullable=True
    )
    resolved_company_name: Mapped[str] = mapped_column(String(255), default="")
    first_name: Mapped[str] = mapped_column(String(120), default="")
    last_name: Mapped[str] = mapped_column(String(120), default="")
    headline: Mapped[str] = mapped_column(String(512), default="")
    current_title: Mapped[str] = mapped_column(String(255), default="")
    seniority: Mapped[str] = mapped_column(String(32), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    # Structured professional fields sourced from the engine (Apify). These are
    # NULLABLE on purpose: a field absent from the actor's output stays NULL rather
    # than carrying a placeholder. The full raw record is preserved in profile_data.
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    functional_area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    work_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    email_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    work_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state_region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    organization_website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organization_linkedin: Mapped[str | None] = mapped_column(String(512), nullable=True)
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    agent_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    agent_reasoning: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="sourced")
    profile_data: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(60), default="linkedin")
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # ---- Read-only enrichment views over the engine (Apify) profile_data -------
    # Phase 1 enterprise enrichment: NO useful field the actor returns stays buried
    # in JSON. The full raw record lives in profile_data["raw"]; these surface
    # individual fields for display, reading the curated key first and falling back
    # to known raw aliases (so rows ingested before a key was curated still resolve).
    # profile_data is parsed once by SQLAlchemy and cached here (perf: no re-parse).
    @cached_property
    def _profile(self) -> dict:
        return self.profile_data or {}

    @cached_property
    def _raw(self) -> dict:
        raw = self._profile.get("raw")
        return raw if isinstance(raw, dict) else {}

    def _pd_get(self, *keys: str) -> str | None:
        """First non-empty value across the curated keys, then the raw aliases."""
        for k in keys:
            v = _coerce_str(self._profile.get(k))
            if v:
                return v
        for k in keys:
            v = _coerce_str(self._raw.get(k))
            if v:
                return v
        return None

    @property
    def company_size(self) -> str | None:
        return self._pd_get("company_size", "organizationSize", "companySize", "employeeCount")

    @property
    def industry(self) -> str | None:
        return self._pd_get("industry", "organizationIndustry")

    @property
    def alt_emails(self) -> str | None:
        return self._pd_get("all_emails", "alternateEmails", "emails")

    @property
    def photo_url(self) -> str | None:
        return self._pd_get("photo_url", "photoUrl", "photo", "imageUrl", "image_url",
                            "profilePicture", "profile_pic_url", "picture", "avatar")

    @property
    def department(self) -> str | None:
        return self._pd_get("department", "departments")

    @property
    def business_unit(self) -> str | None:
        return self._pd_get("business_unit", "businessUnit")

    @property
    def summary(self) -> str | None:
        return self._pd_get("summary", "about", "bio", "description")

    @property
    def skills(self) -> str | None:
        return self._pd_get("skills", "topSkills")

    @property
    def languages(self) -> str | None:
        return self._pd_get("languages", "language")

    @property
    def years_in_company(self) -> str | None:
        return self._pd_get("years_in_company", "yearsInCompany", "companyTenure", "tenure")

    @property
    def years_in_role(self) -> str | None:
        return self._pd_get("years_in_role", "yearsInRole", "roleTenure")

    @property
    def followers(self) -> str | None:
        return self._pd_get("followers", "followersCount", "follower_count", "numFollowers")

    @property
    def connections(self) -> str | None:
        return self._pd_get("connections", "connectionsCount", "connection_count", "numConnections")

    @property
    def apify_person_id(self) -> str | None:
        return self._pd_get("person_id", "personId")


class DecisionMakerSnapshot(Base):
    """Timestamped snapshot of a decision maker's current position.

    Used for leadership signal derivation: snapshot comparison detects promotions,
    role changes, new hires, and departures by comparing current vs. previous
    snapshots. Captured at the end of each decision_maker_intelligence run.
    """

    __tablename__ = "decision_maker_snapshots"
    __table_args__ = (
        Index("ix_dm_snapshot_date", "decision_maker_id", "captured_at"),
        Index("ix_dm_snapshot_all_date", "captured_at"),
    )

    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_maker_id: Mapped[int] = mapped_column(
        ForeignKey("decision_makers.id", ondelete="CASCADE"), nullable=False
    )
    company_domain: Mapped[str | None] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="SET NULL"), nullable=True
    )
    current_title: Mapped[str] = mapped_column(String(255), nullable=False)
    current_company: Mapped[str] = mapped_column(String(255), nullable=False)
    seniority: Mapped[str] = mapped_column(String(32), default="")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ApifyActorRun(Base):
    """Track each Apify API call for monitoring and debugging.

    Records Apify actor execution details: run ID, status, timing, and error messages.
    Linked to pipeline_runs for end-to-end tracing of ingest operations.
    """

    __tablename__ = "apify_actor_runs"
    __table_args__ = (
        Index("ix_apify_run_pipeline_id", "pipeline_run_id"),
        Index("ix_apify_run_started", "started_at"),
    )

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str] = mapped_column(String(32), nullable=False)
    apify_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pipeline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_runs.run_id", ondelete="SET NULL"), nullable=True
    )
    batch_index: Mapped[int] = mapped_column(Integer, default=0)
    company_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="unknown")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_returned: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class DmIntelligenceJob(Base):
    """A MANUAL Decision Maker Intelligence run over a chosen set of companies.

    DM intelligence is never scheduled (paid Apify actor). A user triggers a job from
    the Decision Makers page picking one-or-many companies, each with its OWN requested
    lead count; the job runs the existing Apify engine per company on a background
    thread and records live per-company progress in :class:`DmIntelligenceJobItem`.
    Linked to a ``pipeline_runs`` row (``pipeline_run_id``) so the manual execution
    also shows up in the existing pipeline run history.
    """

    __tablename__ = "dm_intelligence_jobs"
    __table_args__ = (
        CheckConstraint(_in("status", DM_JOB_STATUSES), name="ck_dm_job_status"),
        Index("ix_dm_job_status", "status"),
        Index("ix_dm_job_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    requested_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_by_email: Mapped[str] = mapped_column(String(320), default="")
    total_companies: Mapped[int] = mapped_column(Integer, default=0)
    total_requested: Mapped[int] = mapped_column(Integer, default=0)
    total_found: Mapped[int] = mapped_column(Integer, default=0)
    # Soft link to the pipeline_runs audit row for this manual execution (nullable so
    # a job row can exist before/without the tracker row).
    pipeline_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    items: Mapped[list["DmIntelligenceJobItem"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="DmIntelligenceJobItem.id",
    )


class DmIntelligenceJobItem(Base):
    """One company within a :class:`DmIntelligenceJob` — its requested count and live
    progress (queued -> running -> completed/failed) with records found, timing, the
    Apify run id, and any error."""

    __tablename__ = "dm_intelligence_job_items"
    __table_args__ = (
        CheckConstraint(_in("status", DM_JOB_ITEM_STATUSES), name="ck_dm_job_item_status"),
        Index("ix_dm_job_item_job", "job_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("dm_intelligence_jobs.id", ondelete="CASCADE"), nullable=False
    )
    company_domain: Mapped[str] = mapped_column(String(255), default="")
    company_name: Mapped[str] = mapped_column(String(255), default="")
    requested_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    records_found: Mapped[int] = mapped_column(Integer, default=0)
    apify_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    job: Mapped["DmIntelligenceJob"] = relationship(back_populates="items")


class ImportJob(Base):
    """Reusable tracking for one historical-data import run (Phase 3).

    A single job spans company + decision-maker synchronization for one uploaded file.
    ``status='previewed'`` records a read-only reconciliation preview (no data written);
    the Phase-4 apply step reuses the same row (running -> completed/failed) and the same
    counters. ``stats`` holds the full preview payload as JSON for the Admin Import UI.
    Additive and independent of every other table.
    """

    __tablename__ = "import_jobs"
    __table_args__ = (
        CheckConstraint(_in("status", IMPORT_JOB_STATUSES), name="ck_import_job_status"),
        Index("ix_import_jobs_status", "status"),
        Index("ix_import_jobs_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_id: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(60), default="historical_excel")
    filename: Mapped[str] = mapped_column(String(512), default="")
    initiated_by: Mapped[str] = mapped_column(String(320), default="")
    status: Mapped[str] = mapped_column(String(20), default="previewed")
    companies_processed: Mapped[int] = mapped_column(Integer, default=0)
    decision_makers_processed: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    unchanged_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    conflict_count: Mapped[int] = mapped_column(Integer, default=0)
    invalid_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    # Phase 4 execution tracking. `preview` holds the full serialized company + DM
    # synchronization results so the commit step consumes them WITHOUT reconciling
    # again. The rest powers live progress for the future Admin UI.
    preview: Mapped[dict] = mapped_column(JSON, default=dict)
    current_stage: Mapped[str] = mapped_column(String(40), default="")
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ImportReviewItem(Base):
    """One reviewable record from an import preview (Phase 5).

    Seeded from the Phase-2/3 synchronization results when a combined import preview is
    created. Every record gets an explicit ``state``; ``field_decisions`` records the
    per-field keep-platform/accept-historical choices for updates and conflicts. Only
    ``approved``/``resolved`` items reach the transaction engine at commit time.
    """

    __tablename__ = "import_review_items"
    __table_args__ = (
        UniqueConstraint("job_id", "record_kind", "source_ref", name="uq_review_item_ref"),
        CheckConstraint(_in("record_kind", REVIEW_KINDS), name="ck_review_item_kind"),
        CheckConstraint(_in("category", REVIEW_CATEGORIES), name="ck_review_item_category"),
        CheckConstraint(_in("state", REVIEW_STATES), name="ck_review_item_state"),
        Index("ix_review_items_job", "job_id"),
        Index("ix_review_items_state", "job_id", "state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False
    )
    record_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    state: Mapped[str] = mapped_column(String(20), default="pending")
    field_decisions: Mapped[dict] = mapped_column(JSON, default=dict)
    label: Mapped[str] = mapped_column(String(255), default="")   # display name (company/person)
    reviewer: Mapped[str] = mapped_column(String(320), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ImportReviewEvent(Base):
    """Immutable audit trail of every review decision (Phase 5). Never deleted."""

    __tablename__ = "import_review_events"
    __table_args__ = (
        Index("ix_review_events_job", "job_id"),
        Index("ix_review_events_item", "review_item_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False
    )
    review_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_review_items.id", ondelete="SET NULL"), nullable=True
    )
    record_kind: Mapped[str] = mapped_column(String(20), default="")
    source_ref: Mapped[str] = mapped_column(String(120), default="")
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    field: Mapped[str] = mapped_column(String(120), default="")
    previous_value: Mapped[str] = mapped_column(Text, default="")
    approved_value: Mapped[str] = mapped_column(Text, default="")
    reviewer: Mapped[str] = mapped_column(String(320), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# =====================================================================
# Platform-owned tables (mirror 0003_platform_tables.sql)
# =====================================================================
class LeadScore(Base):
    """Final lead score per company. Owned by the Lead Scoring service (P3)."""

    __tablename__ = "lead_scores"
    __table_args__ = (
        CheckConstraint(_in("grade", LEAD_GRADES), name="ck_lead_grade"),
        Index("ix_lead_scores_grade", "grade"),
        Index("ix_lead_scores_score", "lead_score"),
        Index("ix_lead_scores_priority", "priority_rank"),
    )

    company_domain: Mapped[str] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), primary_key=True
    )
    lead_score: Mapped[float] = mapped_column(Float, default=0.0)
    grade: Mapped[str] = mapped_column(String(4), default="C")
    priority_rank: Mapped[int] = mapped_column(Integer, default=0)
    opportunity_subscore: Mapped[float] = mapped_column(Float, default=0.0)
    demand_subscore: Mapped[float] = mapped_column(Float, default=0.0)
    readiness_subscore: Mapped[float] = mapped_column(Float, default=0.0)
    dm_subscore: Mapped[float] = mapped_column(Float, default=0.0)
    region_mult: Mapped[float] = mapped_column(Float, default=1.0)
    prospect_mult: Mapped[float] = mapped_column(Float, default=1.0)
    tier_mult: Mapped[float] = mapped_column(Float, default=1.0)
    coverage: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[str] = mapped_column(String(8), default="low")
    # Optional human-review adjustment (reconciled Change_05), SEPARATE from the model
    # lead_score/grade above (which are never modified). NULL/'' == no adjustment yet
    # (falls back to the model value). See lead_scoring/human_review.adjusted_score.
    adjusted_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    adjusted_grade: Mapped[str] = mapped_column(String(4), default="")
    rationale: Mapped[dict] = mapped_column(JSON, default=dict)
    model_version: Mapped[str] = mapped_column(String(40), default="")
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class LeadReview(Base):
    """A human analyst's assessment of a lead (P-task viii) — the current state.

    Kept STRICTLY SEPARATE from ``lead_scores``: the model score/grade is never
    overwritten. This row records the human verdict (``review_status``) and the
    reason (``human_notes``); the model value is read alongside it, not replaced.
    1:1 per company. Every change is appended to ``LeadReviewEvent`` (the feedback
    trail). Open to any authenticated user; attribution is recorded.
    """

    __tablename__ = "lead_reviews"
    __table_args__ = (
        CheckConstraint(_in("review_status", LEAD_REVIEW_STATUSES), name="ck_lead_review_status"),
        Index("ix_lead_reviews_status", "review_status"),
    )

    company_domain: Mapped[str] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), primary_key=True
    )
    review_status: Mapped[str] = mapped_column(String(20), default="needs_review")
    human_notes: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_by_email: Mapped[str] = mapped_column(String(320), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Optional expiry — past this the review's SCORE effect lapses (the assessment
    # record + audit remain). Null == never expires.
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class LeadReviewEvent(Base):
    """Append-only feedback / audit trail for human lead reviews (P-task viii).

    One row per human review action. Snapshots the model ``grade``/``score`` AT
    THE TIME of the action so disagreement reports stay correct as the model
    re-scores, and so a future version can learn from the feedback (today the
    platform only records it — it never retrains or modifies scores). Soft
    references (no FK) so the trail survives user/company removal.
    """

    __tablename__ = "lead_review_events"
    __table_args__ = (Index("ix_lead_review_events_company", "company_domain"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_domain: Mapped[str] = mapped_column(String(255), default="")
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_email: Mapped[str] = mapped_column(String(320), default="")
    from_status: Mapped[str] = mapped_column(String(20), default="")
    to_status: Mapped[str] = mapped_column(String(20), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    model_grade: Mapped[str] = mapped_column(String(4), default="")
    model_score: Mapped[float] = mapped_column(Float, default=0.0)
    adjusted_grade: Mapped[str] = mapped_column(String(4), default="")
    adjusted_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class LeadershipSignal(Base):
    """Person-level director+ leadership-movement signal (P-task 8).

    Platform-derived intelligence about *who moved* — promotions, role changes,
    executive hires/departures, board appointments, founder changes — for
    director-level and above only (manager-level and ICs are gated out). This is
    deliberately distinct from the Blog Crawler's company-level ``Leadership
    Change`` *opportunity*: that records that an event happened at a company; this
    records the person and their movement, and lives in the people domain.

    Two feeders write here (``source``): ``linkedin_history`` (derived from a
    decision maker's own ``profile_data`` career history — works on existing data)
    and ``blog_event`` (extracted from ``Leadership Change`` opportunities once
    crawls populate them). ``company_domain`` is nullable — the same documented
    LinkedIn exception as ``decision_makers`` (a historical employer may not
    resolve to a catalogued company).
    """

    __tablename__ = "leadership_signals"
    __table_args__ = (
        CheckConstraint(_in("movement_type", LEADERSHIP_MOVEMENT_TYPES), name="ck_ldr_movement"),
        CheckConstraint(_in("seniority_band", LEADERSHIP_SENIORITY_BANDS), name="ck_ldr_band"),
        CheckConstraint(_in("source", LEADERSHIP_SIGNAL_SOURCES), name="ck_ldr_source"),
        CheckConstraint(_in("confidence", CONFIDENCE_LEVELS), name="ck_ldr_confidence"),
        CheckConstraint(_in("priority_tier", LEADERSHIP_PRIORITY_TIERS), name="ck_ldr_priority"),
        Index("ix_ldr_domain", "company_domain"),
        Index("ix_ldr_movement", "movement_type"),
        Index("ix_ldr_band", "seniority_band"),
        Index("ix_ldr_source", "source"),
        Index("ix_ldr_effective", "effective_date"),
        Index("ix_ldr_priority", "priority_tier"),
    )

    signal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_domain: Mapped[str | None] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), nullable=True
    )
    company_name: Mapped[str] = mapped_column(String(255), default="")
    decision_maker_id: Mapped[int | None] = mapped_column(
        ForeignKey("decision_makers.id", ondelete="SET NULL"), nullable=True
    )
    linkedin_url: Mapped[str] = mapped_column(String(512), default="")
    person_name: Mapped[str] = mapped_column(String(255), default="")
    movement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    from_title: Mapped[str] = mapped_column(String(255), default="")
    to_title: Mapped[str] = mapped_column(String(255), default="")
    seniority_band: Mapped[str] = mapped_column(String(20), nullable=False)
    role_function: Mapped[str] = mapped_column(String(40), default="")
    effective_date: Mapped[str] = mapped_column(String(16), default="")   # YYYY-MM
    event_age_days: Mapped[int] = mapped_column(Integer, default=-1)
    confidence: Mapped[str] = mapped_column(String(8), default="low")
    source: Mapped[str] = mapped_column(String(20), default="linkedin_history")
    source_ref: Mapped[str] = mapped_column(String(1024), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    # News phase 2 additions (migration 0054): a text-derived location signal (India-city
    # aware; "" when nothing recognizable) and the reusable priority tier it (plus company
    # tier) drive — see leadership_signals/priority.py. Additive; every existing feeder
    # still works, defaulting to geography="" / priority_tier="medium".
    geography: Mapped[str] = mapped_column(String(120), default="")
    priority_tier: Mapped[str] = mapped_column(String(10), default="medium")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class EngagementRecommendation(Base):
    """Sales-pitch / engagement recommendation per company (1:1; P-task 9).

    Platform-derived from the company's own intelligence signals (opportunities,
    leadership signals, hiring/demand, job mix, technology, partnerships, funding,
    company type, decision makers) into a likely **business need**, the matching
    **Silicon Patterns offering**, and a **one-line pitch** — with a confidence
    score and a rationale listing the evidence that drove it. Evidence-grounded and
    deterministic (no LLM); recomputed every refresh by the `engagement` stage.
    """

    __tablename__ = "engagement_recommendations"
    __table_args__ = (
        CheckConstraint(_in("confidence_label", CONFIDENCE_LEVELS), name="ck_engagement_confidence"),
        Index("ix_engagement_offering", "offering"),
        Index("ix_engagement_confidence", "confidence"),
    )

    company_domain: Mapped[str] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), primary_key=True
    )
    business_need: Mapped[str] = mapped_column(Text, default="")
    offering: Mapped[str] = mapped_column(String(80), default="")
    pitch: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    confidence_label: Mapped[str] = mapped_column(String(8), default="low")
    rationale: Mapped[list] = mapped_column(JSON, default=list)
    signals_used: Mapped[int] = mapped_column(Integer, default=0)
    model_version: Mapped[str] = mapped_column(String(40), default="")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class IngestionRun(Base):
    """Audit / incremental bookkeeping — one row per engine ingestion run."""

    __tablename__ = "ingestion_runs"
    __table_args__ = (
        Index("ix_ingestion_engine", "engine"),
        Index("ix_ingestion_status", "status"),
        Index("ix_ingestion_started", "started_at"),
    )

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    engine: Mapped[str] = mapped_column(String(60), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="standalone")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    rows_in: Mapped[int] = mapped_column(Integer, default=0)
    rows_upserted: Mapped[int] = mapped_column(Integer, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0)
    rows_review_queued: Mapped[int] = mapped_column(Integer, default=0)
    source_path: Mapped[str] = mapped_column(String(1024), default="")
    notes: Mapped[str] = mapped_column(Text, default="")


class PipelineRun(Base):
    """Orchestrator-level run tracking — one row per stage execution (P5).

    Higher level than ``ingestion_runs``: a stage may run the upstream engine
    AND ingest its output. ``pipeline_id`` groups the stages of one ``run all``.
    """

    __tablename__ = "pipeline_runs"
    __table_args__ = (
        CheckConstraint(_in("status", PIPELINE_STATUSES), name="ck_pipeline_status"),
        Index("ix_pipeline_component", "component"),
        Index("ix_pipeline_status", "status"),
        Index("ix_pipeline_started", "started_at"),
        Index("ix_pipeline_group", "pipeline_id"),
    )

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_id: Mapped[str] = mapped_column(String(60), default="")
    component: Mapped[str] = mapped_column(String(40), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="ingest")
    trigger: Mapped[str] = mapped_column(String(20), default="manual")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_review: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[str] = mapped_column(Text, default="")   # JSON list
    notes: Mapped[str] = mapped_column(Text, default="")


class DiscoveryCandidateRecord(Base):
    """A potential market entrant surfaced by the Market Discovery Engine.

    A candidate is NOT a company. It may be unresolved, below the confidence
    threshold, or later rejected — writing every sighting into ``companies`` would
    fill the canonical table with speculative rows. This table is the engine's
    cross-run memory: it is how a nightly run distinguishes "new" from "seen
    yesterday", which no existing table records.

    Promotion to a real company still goes through the existing
    ``integration.resolver.CompanyResolver``, and provenance is recorded in the
    existing ``company_sources`` — discovery adds no parallel company model.

    ``candidate_key`` is the engine's deterministic identity (domain → LinkedIn slug
    → comparison name, hashed), so the same company always lands on the same row
    regardless of which source reported it.
    """

    __tablename__ = "discovery_candidates"
    __table_args__ = (
        CheckConstraint(_in("status", DISCOVERY_CANDIDATE_STATUSES), name="ck_discovery_status"),
        Index("ix_discovery_candidates_status", "status"),
        Index("ix_discovery_candidates_domain", "company_domain"),
        Index("ix_discovery_candidates_last_seen", "last_seen"),
        Index("ix_discovery_candidates_run", "run_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    company_name: Mapped[str] = mapped_column(String(255), default="")
    # Not a FK: a candidate usually has no company row yet, and must survive one
    # being merged or removed.
    company_domain: Mapped[str] = mapped_column(String(255), default="")
    website: Mapped[str] = mapped_column(String(512), default="")
    linkedin_url: Mapped[str] = mapped_column(String(512), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    industry: Mapped[str] = mapped_column(String(120), default="")
    headquarters: Mapped[str] = mapped_column(String(255), default="")
    country: Mapped[str] = mapped_column(String(120), default="")
    founded_year: Mapped[str] = mapped_column(String(8), default="")
    employee_count: Mapped[str] = mapped_column(String(40), default="")
    funding_stage: Mapped[str] = mapped_column(String(60), default="")
    # JSON-encoded text, not a JSON column: identical behaviour on SQLite and
    # Postgres, and the engine never queries inside these.
    technologies: Mapped[str] = mapped_column(Text, default="[]")
    markets: Mapped[str] = mapped_column(Text, default="[]")
    source: Mapped[str] = mapped_column(String(60), default="")
    source_id: Mapped[str] = mapped_column(String(255), default="")
    source_url: Mapped[str] = mapped_column(String(512), default="")
    sources: Mapped[str] = mapped_column(Text, default="[]")     # every corroborating source
    status: Mapped[str] = mapped_column(String(20), default="new")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    times_seen: Mapped[int] = mapped_column(Integer, default=1)
    run_id: Mapped[str] = mapped_column(String(80), default="")
    raw_payload: Mapped[str] = mapped_column(Text, default="{}")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MarketIntelligenceRecord(Base):
    """What the Market Intelligence Layer concluded about one discovered candidate.

    Separate from ``discovery_candidates`` on purpose. That table is the discovery
    engine's memory of *what was seen*; this one holds the *interpretation* — and the
    two change for different reasons. A rule-pack change re-derives every row here
    while touching nothing there, and a re-crawl updates candidates without
    invalidating an interpretation that is still correct.

    Keyed by ``candidate_key``, the discovery engine's deterministic identity, so an
    interpretation always lands on the same row no matter which source reported the
    company. Not a foreign key, for the same reason the candidate's own domain is
    not: intelligence must survive its candidate being merged or re-keyed.

    ``priority`` and ``priority_score`` are columns rather than JSON because that is
    what the executive dashboard and lead scoring filter and rank on. Everything
    else — classifications, technologies, signals, factors, reasons — is JSON-encoded
    text: identical behaviour on SQLite (dev/tests) and Postgres, and nothing queries
    inside them.
    """

    __tablename__ = "market_intelligence"
    __table_args__ = (
        CheckConstraint(_in("priority", MARKET_INTELLIGENCE_PRIORITIES),
                        name="ck_market_intelligence_priority"),
        Index("ix_market_intelligence_priority", "priority"),
        Index("ix_market_intelligence_domain", "company_domain"),
        Index("ix_market_intelligence_evaluated", "evaluated_at"),
        Index("ix_market_intelligence_run", "run_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    company_name: Mapped[str] = mapped_column(String(255), default="")
    company_domain: Mapped[str] = mapped_column(String(255), default="")
    website: Mapped[str] = mapped_column(String(512), default="")
    source: Mapped[str] = mapped_column(String(60), default="")
    # The strongest (most specific) category, or "" when nothing matched — an
    # unclassifiable company is a real, reviewable state, never labelled "Other".
    primary_classification: Mapped[str] = mapped_column(String(120), default="")
    classifications: Mapped[str] = mapped_column(Text, default="[]")
    technologies: Mapped[str] = mapped_column(Text, default="[]")
    signals: Mapped[str] = mapped_column(Text, default="[]")
    signal_types: Mapped[str] = mapped_column(Text, default="[]")
    classification_count: Mapped[int] = mapped_column(Integer, default=0)
    technology_count: Mapped[int] = mapped_column(Integer, default=0)
    signal_count: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[str] = mapped_column(String(12), default="low")
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    factors: Mapped[str] = mapped_column(Text, default="[]")
    reasons: Mapped[str] = mapped_column(Text, default="[]")
    explanation: Mapped[str] = mapped_column(Text, default="")
    # Which rules produced this row. A stored priority is only reproducible against
    # the pack version that assigned it.
    rule_pack: Mapped[str] = mapped_column(String(60), default="")
    rule_pack_version: Mapped[str] = mapped_column(String(40), default="")
    enrichment: Mapped[str] = mapped_column(Text, default="{}")
    run_id: Mapped[str] = mapped_column(String(80), default="")
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class NotificationDelivery(Base):
    """One delivery attempt of one notification to one recipient.

    Written by :mod:`backend.notifications.service` for every recipient on every
    channel — the audit trail behind ``pipeline_executions.notification_status``,
    which only carries the run-level rollup. Kept channel-neutral (``provider`` is a
    free string) so Teams/Slack/webhook deliveries land in the same table.

    ``run_id`` is a plain string, not a FK: notifications are also emitted for events
    that have no ``pipeline_executions`` row (a run that crashed before insert), and a
    delivery record must survive its run being pruned.
    """

    __tablename__ = "notification_deliveries"
    __table_args__ = (
        CheckConstraint(_in("status", NOTIFICATION_DELIVERY_STATUSES), name="ck_notif_delivery_status"),
        Index("ix_notif_delivery_run", "run_id"),
        Index("ix_notif_delivery_created", "created_at"),
        Index("ix_notif_delivery_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(80), default="")
    event_type: Mapped[str] = mapped_column(String(40), default="run_summary")
    channel: Mapped[str] = mapped_column(String(20), default="email")
    provider: Mapped[str] = mapped_column(String(40), default="")
    recipient: Mapped[str] = mapped_column(String(320), default="")
    audience: Mapped[str] = mapped_column(String(10), default="all")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PipelineExecution(Base):
    """Run-level record of one Standard Run — a full ``run all`` fired by the
    scheduler (trigger='scheduled') or manually (trigger='manual').

    Higher level than :class:`PipelineRun` (which stays one row PER STAGE, grouped by
    ``pipeline_id``): this is the single row the Run History UI lists. ``run_id`` here
    equals the stages' ``pipeline_id`` so the two join. Per-engine stats + platform
    totals are snapshotted into JSON so history reads need no re-aggregation, and the
    Outlook-notification outcome is recorded here (it never blocks the pipeline)."""

    __tablename__ = "pipeline_executions"
    __table_args__ = (
        CheckConstraint(_in("trigger", EXECUTION_TRIGGERS), name="ck_pexec_trigger"),
        CheckConstraint(_in("status", EXECUTION_STATUSES), name="ck_pexec_status"),
        Index("ix_pexec_started", "started_at"),
        Index("ix_pexec_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)  # == pipeline_runs.pipeline_id
    trigger: Mapped[str] = mapped_column(String(20), default="manual")
    scheduled_slot: Mapped[str | None] = mapped_column(String(10), nullable=True)  # e.g. "09:00"
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    # Per-engine stats: [{component,status,processed,created,updated,review,duration_ms,errors,notes}]
    stages: Mapped[list] = mapped_column(JSON, default=list)
    # Platform totals snapshot: {companies,opportunities,decision_makers,jobs,leads_scored}
    totals: Mapped[dict] = mapped_column(JSON, default=dict)
    notification_status: Mapped[str] = mapped_column(String(20), default="pending")
    notification_detail: Mapped[str] = mapped_column(Text, default="")
    notified_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RunEngineRecord(Base):
    """One lightweight reference per canonical record a Standard Run's engine touched
    (migration 0053). Powers the Run Details per-engine drill-down: given a run + an
    engine, exactly which records that run processed, and how (created/updated/…).

    A REFERENCE, not a copy — ``entity_table`` + ``entity_id`` join back to the
    canonical row for display; ``detail`` holds only the run-specific facts a later
    join can't recover (e.g. a lead's score at run time). ``run_id`` equals the
    ``pipeline_executions.run_id`` (== ``pipeline_runs.pipeline_id``) that produced it,
    so isolation is by construction: filtering on (run_id, engine) can never leak
    another run's records."""

    __tablename__ = "run_engine_records"
    __table_args__ = (
        Index("ix_rer_run_engine", "run_id", "engine"),
        Index("ix_rer_run", "run_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Soft link (text) — no FK at the ORM layer so SQLite review DBs and tests stay
    # simple; the SQL migration adds the real FK + ON DELETE CASCADE on Postgres.
    run_id: Mapped[str] = mapped_column(String(80), nullable=False)
    engine: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_table: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    operation: Mapped[str] = mapped_column(String(20), nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ReviewAction(Base):
    """Audit trail for review-queue resolutions (approve / merge / reject / alias)."""

    __tablename__ = "review_actions"
    __table_args__ = (Index("ix_review_actions_review", "review_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # approve|merge|reject|create_alias
    actor: Mapped[str] = mapped_column(String(120), default="api")
    from_domain: Mapped[str] = mapped_column(String(255), default="")
    to_domain: Mapped[str] = mapped_column(String(255), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# =====================================================================
# Account + workflow tables (mirror 0007_users.sql … 0010_dm_contacts.sql)
# =====================================================================
class User(Base):
    """A platform user. Identity via Microsoft Entra ID (Azure AD) — see
    backend/security.py::verify_microsoft_id_token + backend/services.py::login_with_microsoft.

    ``status`` drives the account lifecycle (pending→active, disabled, rejected,
    soft-deleted); ``is_active`` is kept as the fast "may authenticate" gate and is
    held consistent with status (True only when status == 'active'). Accounts are
    never hard-deleted — ``deleted`` soft-deletes (PII scrubbed, row retained)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(_in("role", USER_ROLES), name="ck_users_role"),
        CheckConstraint(_in("status", USER_STATUSES), name="ck_users_status"),
        Index("ix_users_role", "role"),
        Index("ix_users_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    # The immutable Google subject id from a prior auth mechanism (direct Google SSO,
    # then Supabase-brokered Google OAuth). No longer written to — superseded by
    # microsoft_oid below — but left in place rather than dropped (nothing reads it
    # either; harmless).
    google_sub: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    # The immutable Microsoft Entra object id (the ID token's `oid` claim, falling back
    # to `sub`). Nullable + unique: existing accounts predate this column, and NULL !=
    # NULL under a unique index on both SQLite and Postgres, so any number of legacy
    # rows may have it unset without colliding. Preferred over email for lookup once
    # populated, since email can change at the identity provider.
    microsoft_oid: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    picture: Mapped[str] = mapped_column(String(1024), default="")
    role: Mapped[str] = mapped_column(String(16), default="member")
    # New accounts default to 'active' so direct creation (dev bypass / tests / seeds)
    # is immediately usable; the SSO path explicitly creates non-admins as 'pending'.
    status: Mapped[str] = mapped_column(String(16), default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    login_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # First-party email/password auth (migration 0041), from the mechanism prior to
    # Microsoft Entra ID. No longer written to or read by any code path — left in
    # place rather than dropped, matching how google_sub was handled after the
    # previous auth-mechanism swap.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Forced the password-change flow under the password-auth mechanism. No longer
    # meaningful (there's no password to force a change of) — left in place unused.
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)


class UserAuditEvent(Base):
    """Append-only audit trail of account lifecycle + admin user-management actions
    (registered, login, approved, rejected, enabled, disabled, role_changed, deleted)."""

    __tablename__ = "user_audit_events"
    __table_args__ = (
        CheckConstraint(_in("action", USER_AUDIT_ACTIONS), name="ck_user_audit_action"),
        Index("ix_user_audit_target", "target_user_id", "created_at"),
        Index("ix_user_audit_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    target_email: Mapped[str] = mapped_column(String(320), default="")
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_email: Mapped[str] = mapped_column(String(320), default="")
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class LeadAssignment(Base):
    """A company (lead) assigned to a user, with a pipeline status. Owned by the platform."""

    __tablename__ = "lead_assignments"
    __table_args__ = (
        UniqueConstraint("company_domain", "user_id", name="uq_assignment_company_user"),
        CheckConstraint(_in("status", ASSIGNMENT_STATUSES), name="ck_assignment_status"),
        Index("ix_assignments_user", "user_id"),
        Index("ix_assignments_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_domain: Mapped[str] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="assigned")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class LeadAssignmentEvent(Base):
    """Audit trail for assignment changes (assign / reassign / unassign / status / note)."""

    __tablename__ = "lead_assignment_events"
    __table_args__ = (Index("ix_assignment_events_company", "company_domain"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    company_domain: Mapped[str] = mapped_column(String(255), default="")
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    from_value: Mapped[str] = mapped_column(String(255), default="")
    to_value: Mapped[str] = mapped_column(String(255), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CompanyNote(Base):
    """A free-text analyst note on a company; feeds the per-company activity timeline."""

    __tablename__ = "company_notes"
    __table_args__ = (Index("ix_company_notes_domain", "company_domain"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_domain: Mapped[str] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), nullable=False
    )
    author_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    author_email: Mapped[str] = mapped_column(String(320), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class DecisionMakerContact(Base):
    """Analyst-entered PROFESSIONAL contact details for a decision maker — work
    email / phone only (never personal home / email / phone). Platform-owned."""

    __tablename__ = "decision_maker_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_maker_id: Mapped[int] = mapped_column(
        ForeignKey("decision_makers.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    work_email: Mapped[str] = mapped_column(String(320), default="")
    work_phone: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    added_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    added_by_email: Mapped[str] = mapped_column(String(320), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class DecisionMakerNote(Base):
    """A collaboration note on a decision maker. Four tiers (``note_type``), shown
    in the order admin → manager → team → personal:

    * ``admin`` — authority guidance created by admins only; pinned first;
      visible to everyone.
    * ``manager`` — authority guidance created by admins/managers; below admin;
      visible to everyone.
    * ``team`` — a shared note any authenticated user may add; visible to everyone
      (managers may also curate/remove).
    * ``personal`` — private to its author. Any user may create one; only the
      author may edit/delete it. Never shown to other users.

    Replaces the single ``decision_maker_contacts.notes`` blob (which is retained
    for backward compatibility but no longer surfaced in the UI)."""

    __tablename__ = "decision_maker_notes"
    __table_args__ = (
        CheckConstraint(_in("note_type", DM_NOTE_TYPES), name="ck_dm_note_type"),
        Index("ix_dm_notes_dm", "decision_maker_id"),
        Index("ix_dm_notes_author", "created_by"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_maker_id: Mapped[int] = mapped_column(
        ForeignKey("decision_makers.id", ondelete="CASCADE"), nullable=False
    )
    note_type: Mapped[str] = mapped_column(String(16), default="personal")
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    author_email: Mapped[str] = mapped_column(String(320), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


# ===========================================================================
# Outreach module (native) — an engagement *cycle* layered on top of the
# existing companies / decision_makers / lead_scores / engagement_recommendations.
# These tables hold ONLY outreach-specific state; intelligence is read from the
# platform tables (no duplication).
# ===========================================================================
class OutreachLead(Base):
    """One outreach/engagement cycle for a company (1:1 with companies).

    Score, grade, priority, signals and the recommended pitch are NOT stored here
    — they are read live from lead_scores / engagement_recommendations / etc. This
    row owns only the pipeline state: stage, owner, chosen service line, the
    qualifying contact, and the next action."""

    __tablename__ = "outreach_leads"
    __table_args__ = (
        CheckConstraint(_in("stage", OUTREACH_STAGES), name="ck_outreach_stage"),
        CheckConstraint(_in("source", OUTREACH_LEAD_SOURCES), name="ck_outreach_lead_source"),
        # service_interest is nullable; NULL passes a SQL IN-check.
        CheckConstraint(_in("service_interest", OUTREACH_SERVICE_LINES), name="ck_outreach_service"),
        Index("ix_outreach_leads_stage", "stage"),
        Index("ix_outreach_leads_owner", "owner_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_domain: Mapped[str] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), nullable=False, unique=True
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    primary_dm_id: Mapped[int | None] = mapped_column(
        ForeignKey("decision_makers.id", ondelete="SET NULL"), nullable=True
    )
    stage: Mapped[str] = mapped_column(String(32), default="research_complete")
    service_interest: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="discovery")
    qualification_reason: Mapped[str] = mapped_column(Text, default="")
    qualified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class OutreachTemplate(Base):
    """A deterministic, ``{{variable}}``-based email template (no LLM)."""

    __tablename__ = "outreach_templates"
    __table_args__ = (Index("ix_outreach_templates_active", "is_active"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="")
    subject: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class OutreachMessage(Base):
    """An email through its lifecycle: draft → pending_approval → approved → sent
    (mock) → replied. Inbound replies are stored as direction='inbound' rows."""

    __tablename__ = "outreach_messages"
    __table_args__ = (
        CheckConstraint(_in("status", OUTREACH_MESSAGE_STATUSES), name="ck_outreach_msg_status"),
        CheckConstraint(_in("direction", OUTREACH_MESSAGE_DIRECTIONS), name="ck_outreach_msg_dir"),
        Index("ix_outreach_msgs_lead", "outreach_lead_id"),
        Index("ix_outreach_msgs_status", "status"),
        Index("ix_outreach_msgs_thread", "thread_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    outreach_lead_id: Mapped[int] = mapped_column(
        ForeignKey("outreach_leads.id", ondelete="CASCADE"), nullable=False
    )
    decision_maker_id: Mapped[int | None] = mapped_column(
        ForeignKey("decision_makers.id", ondelete="SET NULL"), nullable=True
    )
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("outreach_templates.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    direction: Mapped[str] = mapped_column(String(12), default="outbound")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    to_email: Mapped[str] = mapped_column(String(320), default="")
    from_email: Mapped[str] = mapped_column(String(320), default="")
    subject: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    thread_id: Mapped[str] = mapped_column(String(80), default="")
    failed_reason: Mapped[str] = mapped_column(Text, default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Phase 2: scheduling + delivery tracking
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bounced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    provider_message_id: Mapped[str] = mapped_column(String(200), default="", index=True)
    # Phase 3: conversation engine + message state
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_conversations.id", ondelete="SET NULL"), nullable=True
    )
    parent_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("outreach_messages.id", ondelete="SET NULL"), nullable=True
    )
    body_html: Mapped[str] = mapped_column(Text, default="")
    folder: Mapped[str] = mapped_column(String(20), default="inbox")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    is_trashed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_important: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class OutreachActivity(Base):
    """Append-only activity timeline / audit log for one outreach lead."""

    __tablename__ = "outreach_activities"
    __table_args__ = (
        CheckConstraint(_in("type", OUTREACH_ACTIVITY_TYPES), name="ck_outreach_activity_type"),
        Index("ix_outreach_activities_lead", "outreach_lead_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    outreach_lead_id: Mapped[int] = mapped_column(
        ForeignKey("outreach_leads.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_email: Mapped[str] = mapped_column(String(320), default="")
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class OutreachTask(Base):
    """A structured follow-up task linked to an outreach lead / company / DM."""

    __tablename__ = "outreach_tasks"
    __table_args__ = (
        CheckConstraint(_in("status", OUTREACH_TASK_STATUSES), name="ck_task_status"),
        CheckConstraint(_in("priority", OUTREACH_TASK_PRIORITIES), name="ck_task_priority"),
        Index("ix_outreach_tasks_lead", "outreach_lead_id"),
        Index("ix_outreach_tasks_assigned", "assigned_to"),
        Index("ix_outreach_tasks_status", "status"),
        Index("ix_outreach_tasks_due", "due_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    company_domain: Mapped[str | None] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="SET NULL"), nullable=True
    )
    decision_maker_id: Mapped[int | None] = mapped_column(
        ForeignKey("decision_makers.id", ondelete="SET NULL"), nullable=True
    )
    outreach_lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("outreach_leads.id", ondelete="CASCADE"), nullable=True
    )
    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    completed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class OutreachMeeting(Base):
    """A meeting / call record linked to an outreach lead."""

    __tablename__ = "outreach_meetings"
    __table_args__ = (
        CheckConstraint(_in("meeting_type", OUTREACH_MEETING_TYPES), name="ck_meeting_type"),
        CheckConstraint(
            f"outcome = '' OR {_in('outcome', OUTREACH_MEETING_OUTCOMES)}",
            name="ck_meeting_outcome",
        ),
        Index("ix_outreach_meetings_lead", "outreach_lead_id"),
        Index("ix_outreach_meetings_scheduled", "scheduled_at"),
        Index("ix_outreach_meetings_domain", "company_domain"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    outreach_lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("outreach_leads.id", ondelete="CASCADE"), nullable=True
    )
    company_domain: Mapped[str | None] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="SET NULL"), nullable=True
    )
    decision_maker_id: Mapped[int | None] = mapped_column(
        ForeignKey("decision_makers.id", ondelete="SET NULL"), nullable=True
    )
    meeting_type: Mapped[str] = mapped_column(String(16), default="call")
    title: Mapped[str] = mapped_column(String(512), default="")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    participants: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    outcome: Mapped[str] = mapped_column(String(16), default="")
    next_action: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class EmailProviderAccount(Base):
    """Per-user email provider configuration (Phase 2 email architecture)."""

    __tablename__ = "email_provider_accounts"
    __table_args__ = (
        CheckConstraint(_in("provider_type", EMAIL_PROVIDER_TYPES), name="ck_provider_type"),
        CheckConstraint(_in("connection_status", EMAIL_CONNECTION_STATUSES), name="ck_provider_status"),
        CheckConstraint(_in("sync_status", GMAIL_SYNC_STATUSES), name="ck_gmail_sync_status"),
        Index("ix_email_provider_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    provider_type: Mapped[str] = mapped_column(String(20), default="mock")
    connection_status: Mapped[str] = mapped_column(String(20), default="pending")
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    # Phase 4: Gmail sync state
    email_address: Mapped[str] = mapped_column(String(512), default="")
    oauth_state: Mapped[str] = mapped_column(Text, default="")  # CSRF state token
    sync_cursor: Mapped[str | None] = mapped_column(Text, nullable=True)  # Gmail history ID
    sync_status: Mapped[str] = mapped_column(String(20), default="idle")
    sync_error: Mapped[str] = mapped_column(Text, default="")
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class EmailAttachment(Base):
    """File attachment linked to an outreach message (Phase 2 email architecture)."""

    __tablename__ = "email_attachments"
    __table_args__ = (
        CheckConstraint(_in("status", EMAIL_ATTACHMENT_STATUSES), name="ck_attachment_status"),
        Index("ix_email_attachments_msg", "outreach_message_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    outreach_message_id: Mapped[int] = mapped_column(
        ForeignKey("outreach_messages.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="uploaded")
    content: Mapped[str] = mapped_column(Text, default="")  # Base64-encoded for SQLite storage
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ======================================================================
# Phase 3 — Conversation & Inbox Engine
# ======================================================================

class EmailConversation(Base):
    """Groups related messages into a conversation thread (provider-independent)."""

    __tablename__ = "email_conversations"
    __table_args__ = (
        Index("ix_email_conv_lead", "outreach_lead_id"),
        Index("ix_email_conv_domain", "company_domain"),
        Index("ix_email_conv_last", "last_message_at"),
        Index("ix_email_conv_thread", "thread_id"),
        Index("ix_email_conv_folder", "folder"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    outreach_lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("outreach_leads.id", ondelete="SET NULL"), nullable=True
    )
    company_domain: Mapped[str | None] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="SET NULL"), nullable=True
    )
    decision_maker_id: Mapped[int | None] = mapped_column(
        ForeignKey("decision_makers.id", ondelete="SET NULL"), nullable=True
    )
    subject: Mapped[str] = mapped_column(String(1000), default="")
    # No index=True here: __table_args__ already declares ix_email_conv_thread on this
    # column, and that named index is the only one the migration creates. Both together
    # made create_all() (SQLite/dev/tests) build a second, identical index that
    # production has never had — model/migration drift, and a double write on insert.
    thread_id: Mapped[str] = mapped_column(String(80), default="")
    folder: Mapped[str] = mapped_column(String(20), default="inbox")
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    unread_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    is_trashed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class EmailLabel(Base):
    """Provider-independent label (system or user-defined)."""

    __tablename__ = "email_labels"
    __table_args__ = (
        CheckConstraint(_in("color", EMAIL_LABEL_COLORS), name="ck_label_color"),
        Index("ix_email_labels_creator", "created_by"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    color: Mapped[str] = mapped_column(String(16), default="gray")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ConversationLabel(Base):
    """Junction table: many-to-many between conversations and labels."""

    __tablename__ = "conversation_labels"
    __table_args__ = (
        UniqueConstraint("conversation_id", "label_id", name="uq_conv_label"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("email_conversations.id", ondelete="CASCADE"), nullable=False
    )
    label_id: Mapped[int] = mapped_column(
        ForeignKey("email_labels.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ===========================================================================
# Enterprise CRM — Phase 1: Campaign & Sequence Management (migration 0024)
# ===========================================================================

class Campaign(Base):
    """An outreach campaign grouping companies/DMs under a common goal."""

    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint(_in("status", CAMPAIGN_STATUSES), name="ck_campaign_status"),
        CheckConstraint(_in("campaign_type", CAMPAIGN_TYPES), name="ck_campaign_type"),
        Index("ix_campaigns_owner", "owner_id"),
        Index("ix_campaigns_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    campaign_type: Mapped[str] = mapped_column(String(32), default="cold_outreach")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    goal: Mapped[str] = mapped_column(Text, default="")
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CampaignMember(Base):
    """One company (and optionally a DM/opportunity/lead) enrolled in a campaign."""

    __tablename__ = "campaign_members"
    __table_args__ = (
        CheckConstraint(_in("engagement_status", CAMPAIGN_MEMBER_STATUSES), name="ck_member_status"),
        CheckConstraint(
            f"campaign_outcome = '' OR {_in('campaign_outcome', CAMPAIGN_OUTCOMES)}",
            name="ck_member_outcome",
        ),
        UniqueConstraint("campaign_id", "company_domain", name="uq_campaign_member_domain"),
        Index("ix_campaign_members_campaign", "campaign_id"),
        Index("ix_campaign_members_domain", "company_domain"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    company_domain: Mapped[str | None] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), nullable=True
    )
    decision_maker_id: Mapped[int | None] = mapped_column(
        ForeignKey("decision_makers.id", ondelete="SET NULL"), nullable=True
    )
    opportunity_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunities.opportunity_id", ondelete="SET NULL"), nullable=True
    )
    outreach_lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("outreach_leads.id", ondelete="SET NULL"), nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    current_stage: Mapped[str] = mapped_column(String(32), default="pending")
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    engagement_status: Mapped[str] = mapped_column(String(20), default="active")
    campaign_outcome: Mapped[str] = mapped_column(String(20), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class OutreachSequence(Base):
    """A reusable multi-step outreach sequence (template of steps)."""

    __tablename__ = "outreach_sequences"
    __table_args__ = (Index("ix_outreach_sequences_active", "is_active"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class SequenceStep(Base):
    """One step in an OutreachSequence (ordered, action-typed, delay-based)."""

    __tablename__ = "sequence_steps"
    __table_args__ = (
        CheckConstraint(_in("action", SEQUENCE_STEP_ACTIONS), name="ck_step_action"),
        UniqueConstraint("sequence_id", "step_order", name="uq_step_order"),
        Index("ix_sequence_steps_seq", "sequence_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey("outreach_sequences.id", ondelete="CASCADE"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    delay_days: Mapped[int] = mapped_column(Integer, default=0)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("outreach_templates.id", ondelete="SET NULL"), nullable=True
    )
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class SequenceEnrollment(Base):
    """A lead enrolled in a sequence (tracks progress through steps)."""

    __tablename__ = "sequence_enrollments"
    __table_args__ = (
        CheckConstraint(_in("status", SEQUENCE_ENROLLMENT_STATUSES), name="ck_enrollment_status"),
        Index("ix_enrollments_sequence", "sequence_id"),
        Index("ix_enrollments_lead", "outreach_lead_id"),
        Index("ix_enrollments_status", "status"),
        Index("ix_enrollments_next", "next_step_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey("outreach_sequences.id", ondelete="CASCADE"), nullable=False
    )
    campaign_member_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaign_members.id", ondelete="CASCADE"), nullable=True
    )
    outreach_lead_id: Mapped[int] = mapped_column(
        ForeignKey("outreach_leads.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="active")
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    next_step_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enrolled_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class SequenceStepExecution(Base):
    """One executed (or pending/skipped) instance of a SequenceStep for an enrollment."""

    __tablename__ = "sequence_step_executions"
    __table_args__ = (
        CheckConstraint(_in("status", SEQUENCE_STEP_STATUSES), name="ck_exec_status"),
        Index("ix_step_execs_enrollment", "enrollment_id"),
        Index("ix_step_execs_status", "status"),
        Index("ix_step_execs_scheduled", "scheduled_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("sequence_enrollments.id", ondelete="CASCADE"), nullable=False
    )
    step_id: Mapped[int] = mapped_column(
        ForeignKey("sequence_steps.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outreach_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("outreach_messages.id", ondelete="SET NULL"), nullable=True
    )
    outreach_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("outreach_tasks.id", ondelete="SET NULL"), nullable=True
    )
    outreach_meeting_id: Mapped[int | None] = mapped_column(
        ForeignKey("outreach_meetings.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# =====================================================================
# Enterprise CRM Phase 2 — Pipeline & Deal Management
# =====================================================================

class CrmPipeline(Base):
    """A named sales pipeline. One pipeline = one Kanban board."""

    __tablename__ = "crm_pipelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CrmPipelineStage(Base):
    """An ordered stage within a pipeline."""

    __tablename__ = "crm_pipeline_stages"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "stage_order", name="uq_pipeline_stage_order"),
        CheckConstraint(_in("stage_type", DEAL_PIPELINE_STAGE_TYPES), name="ck_stage_type"),
        Index("ix_crm_stages_pipeline", "pipeline_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("crm_pipelines.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stage_type: Mapped[str] = mapped_column(String(20), default="open")
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)
    probability: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CrmDeal(Base):
    """A CRM deal tracking a potential sale through a pipeline."""

    __tablename__ = "crm_deals"
    __table_args__ = (
        CheckConstraint(_in("currency", DEAL_CURRENCIES), name="ck_deal_currency"),
        CheckConstraint(_in("forecast_category", DEAL_FORECAST_CATEGORIES), name="ck_deal_forecast"),
        CheckConstraint("probability >= 0 AND probability <= 100", name="ck_deal_probability"),
        Index("ix_crm_deals_company", "company_domain"),
        Index("ix_crm_deals_stage", "stage_id"),
        Index("ix_crm_deals_owner", "owner_id"),
        Index("ix_crm_deals_pipeline", "pipeline_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_domain: Mapped[str] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="CASCADE"), nullable=False
    )
    opportunity_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunities.opportunity_id", ondelete="SET NULL"), nullable=True
    )
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("crm_pipelines.id", ondelete="CASCADE"), nullable=False
    )
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("crm_pipeline_stages.id", ondelete="RESTRICT"), nullable=False
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    probability: Mapped[int] = mapped_column(Integer, default=0)
    forecast_category: Mapped[str] = mapped_column(String(20), default="pipeline")
    expected_close_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    lost_reason: Mapped[str] = mapped_column(String(255), default="")
    won_reason: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CrmDealStageHistory(Base):
    """Tracks every stage transition for a deal (stage velocity + audit)."""

    __tablename__ = "crm_deal_stage_history"
    __table_args__ = (
        Index("ix_deal_history_deal", "deal_id"),
        Index("ix_deal_history_stage", "to_stage_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deal_id: Mapped[int] = mapped_column(
        ForeignKey("crm_deals.id", ondelete="CASCADE"), nullable=False
    )
    from_stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL"), nullable=True
    )
    to_stage_id: Mapped[int] = mapped_column(
        ForeignKey("crm_pipeline_stages.id", ondelete="CASCADE"), nullable=False
    )
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_in_stage_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# =====================================================================
# Enterprise CRM Phase 3 — Team Collaboration & Work Management
# =====================================================================

class CrmAssignment(Base):
    """Polymorphic role assignment: any user can hold a role on any entity."""

    __tablename__ = "crm_assignments"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "user_id", "role",
                         name="uq_crm_assignment"),
        CheckConstraint(_in("entity_type", COLLAB_ENTITY_TYPES), name="ck_assign_entity_type"),
        CheckConstraint(_in("role", COLLAB_ROLES), name="ck_assign_role"),
        Index("ix_crm_assignments_user", "user_id"),
        Index("ix_crm_assignments_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)  # int or str PK as text
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="assignee")
    assigned_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CrmAssignmentHistory(Base):
    """Append-only audit trail for assignment changes."""

    __tablename__ = "crm_assignment_history"
    __table_args__ = (
        CheckConstraint(_in("action", COLLAB_ASSIGNMENT_ACTIONS), name="ck_assign_action"),
        Index("ix_assign_history_entity", "entity_type", "entity_id"),
        Index("ix_assign_history_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(20), default="assignee")
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CrmComment(Base):
    """Internal comment on an entity, with optional threading and @mentions."""

    __tablename__ = "crm_comments"
    __table_args__ = (
        CheckConstraint(_in("entity_type", COLLAB_ENTITY_TYPES), name="ck_comment_entity_type"),
        Index("ix_crm_comments_entity", "entity_type", "entity_id"),
        Index("ix_crm_comments_author", "author_id"),
        Index("ix_crm_comments_parent", "parent_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mentions: Mapped[list] = mapped_column(JSON, default=list)  # list of user_id ints
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("crm_comments.id", ondelete="CASCADE"), nullable=True
    )
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CrmNotification(Base):
    """Per-user in-app notification."""

    __tablename__ = "crm_notifications"
    __table_args__ = (
        CheckConstraint(_in("notif_type", COLLAB_NOTIF_TYPES), name="ck_notif_type"),
        Index("ix_crm_notifs_user_unread", "user_id", "is_read"),
        Index("ix_crm_notifs_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notif_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    entity_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CrmSavedView(Base):
    """A saved CRM view (filters + columns + sort) for deals, campaigns, etc."""

    __tablename__ = "crm_saved_views"
    __table_args__ = (
        CheckConstraint(_in("entity_type", SAVED_VIEW_ENTITY_TYPES), name="ck_view_entity"),
        Index("ix_crm_views_owner", "owner_id"),
        Index("ix_crm_views_shared", "is_shared"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    sort_by: Mapped[str] = mapped_column(String(64), default="")
    sort_dir: Mapped[str] = mapped_column(String(4), default="desc")
    columns: Mapped[list] = mapped_column(JSON, default=list)
    grouping: Mapped[str] = mapped_column(String(64), default="")
    search: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


# =====================================================================
# Enterprise CRM Phase 4 — Customer Success & Account Management
# =====================================================================

class CsAccount(Base):
    """Customer account — the top-level entity for Customer Success."""

    __tablename__ = "cs_accounts"
    __table_args__ = (
        CheckConstraint(_in("status", CS_ACCOUNT_STATUSES), name="ck_cs_acct_status"),
        CheckConstraint(_in("tier", CS_ACCOUNT_TIERS), name="ck_cs_acct_tier"),
        Index("ix_cs_accounts_domain", "company_domain"),
        Index("ix_cs_accounts_owner", "owner_id"),
        Index("ix_cs_accounts_status", "status"),
        Index("ix_cs_accounts_renewal", "renewal_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_domain: Mapped[str | None] = mapped_column(
        ForeignKey("companies.company_domain", ondelete="SET NULL"), nullable=True
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active")
    tier: Mapped[str] = mapped_column(String(20), default="mid_market")
    industry: Mapped[str] = mapped_column(String(100), default="")
    arr: Mapped[float] = mapped_column(Float, default=0.0)
    mrr: Mapped[float] = mapped_column(Float, default=0.0)
    contract_value: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    renewal_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lifecycle_stage: Mapped[str] = mapped_column(String(20), default="customer")
    notes: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CsContact(Base):
    """Customer stakeholder linked to a CsAccount."""

    __tablename__ = "cs_contacts"
    __table_args__ = (
        CheckConstraint(_in("role", CS_CONTACT_ROLES), name="ck_cs_contact_role"),
        Index("ix_cs_contacts_account", "account_id"),
        Index("ix_cs_contacts_email", "email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("cs_accounts.id", ondelete="CASCADE"), nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), default="")
    last_name: Mapped[str] = mapped_column(String(100), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(20), default="primary")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CsHealthScore(Base):
    """Point-in-time health snapshot for a customer account."""

    __tablename__ = "cs_health_scores"
    __table_args__ = (
        CheckConstraint(_in("grade", CS_HEALTH_GRADES), name="ck_cs_health_grade"),
        CheckConstraint(_in("trend", CS_HEALTH_TRENDS), name="ck_cs_health_trend"),
        Index("ix_cs_health_account", "account_id"),
        Index("ix_cs_health_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("cs_accounts.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, default=0.0)       # 0–100
    grade: Mapped[str] = mapped_column(String(2), default="C")
    trend: Mapped[str] = mapped_column(String(10), default="stable")
    # Signal sub-scores (all 0–100)
    product_adoption: Mapped[float] = mapped_column(Float, default=0.0)
    meeting_activity: Mapped[float] = mapped_column(Float, default=0.0)
    email_activity: Mapped[float] = mapped_column(Float, default=0.0)
    opportunity_activity: Mapped[float] = mapped_column(Float, default=0.0)
    open_issues: Mapped[float] = mapped_column(Float, default=0.0)
    renewal_status: Mapped[float] = mapped_column(Float, default=0.0)
    executive_engagement: Mapped[float] = mapped_column(Float, default=0.0)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CsLifecycleEvent(Base):
    """Append-only record of lifecycle stage transitions."""

    __tablename__ = "cs_lifecycle_events"
    __table_args__ = (
        CheckConstraint(_in("stage", CS_LIFECYCLE_STAGES), name="ck_cs_lc_stage"),
        Index("ix_cs_lc_account", "account_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("cs_accounts.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(20), nullable=False)
    from_stage: Mapped[str] = mapped_column(String(20), default="")
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CsContract(Base):
    """Contract associated with a customer account."""

    __tablename__ = "cs_contracts"
    __table_args__ = (
        CheckConstraint(_in("status", CS_CONTRACT_STATUSES), name="ck_cs_contract_status"),
        Index("ix_cs_contracts_account", "account_id"),
        Index("ix_cs_contracts_end", "end_date"),
        Index("ix_cs_contracts_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("cs_accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    value: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    renewal_probability: Mapped[float] = mapped_column(Float, default=0.5)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CsSuccessPlan(Base):
    """Success plan with goals and milestones for a customer account."""

    __tablename__ = "cs_success_plans"
    __table_args__ = (
        CheckConstraint(_in("status", CS_PLAN_STATUSES), name="ck_cs_plan_status"),
        Index("ix_cs_plans_account", "account_id"),
        Index("ix_cs_plans_owner", "owner_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("cs_accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    goals: Mapped[list] = mapped_column(JSON, default=list)       # list of {goal, target_date}
    notes: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CsMilestone(Base):
    """Milestone within a success plan."""

    __tablename__ = "cs_milestones"
    __table_args__ = (
        CheckConstraint(_in("status", CS_MILESTONE_STATUSES), name="ck_cs_ms_status"),
        Index("ix_cs_milestones_plan", "plan_id"),
        Index("ix_cs_milestones_account", "account_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("cs_success_plans.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("cs_accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CsRisk(Base):
    """Risk item tracked against a customer account."""

    __tablename__ = "cs_risks"
    __table_args__ = (
        CheckConstraint(_in("severity", CS_RISK_SEVERITIES), name="ck_cs_risk_severity"),
        CheckConstraint(_in("status", CS_RISK_STATUSES), name="ck_cs_risk_status"),
        Index("ix_cs_risks_account", "account_id"),
        Index("ix_cs_risks_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("cs_accounts.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(10), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="open")
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


# =====================================================================
# Enterprise CRM Phase 5 — Revenue Operations, Forecasting & Executive Analytics
# =====================================================================

class RevenueTarget(Base):
    """A revenue target/quota for the company, a role-team, or an individual owner."""

    __tablename__ = "revenue_targets"
    __table_args__ = (
        CheckConstraint(_in("scope", REVOPS_TARGET_SCOPES), name="ck_revtarget_scope"),
        CheckConstraint(_in("period_type", REVOPS_PERIOD_TYPES), name="ck_revtarget_period"),
        Index("ix_revenue_targets_owner", "owner_id"),
        Index("ix_revenue_targets_pipeline", "pipeline_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(20), default="company")
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("crm_pipelines.id", ondelete="CASCADE"), nullable=True
    )
    period_type: Mapped[str] = mapped_column(String(20), default="monthly")
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class ForecastSnapshot(Base):
    """A point-in-time capture of a forecasted amount, used for accuracy tracking."""

    __tablename__ = "forecast_snapshots"
    __table_args__ = (
        CheckConstraint(_in("period_type", REVOPS_PERIOD_TYPES), name="ck_snapshot_period"),
        CheckConstraint(_in("category", REVOPS_FORECAST_SNAPSHOT_CATEGORIES), name="ck_snapshot_category"),
        Index("ix_forecast_snapshots_pipeline", "pipeline_id"),
        Index("ix_forecast_snapshots_period", "period_type", "period_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_id: Mapped[int | None] = mapped_column(
        ForeignKey("crm_pipelines.id", ondelete="CASCADE"), nullable=True
    )
    period_type: Mapped[str] = mapped_column(String(20), default="monthly")
    period_key: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(20), default="pipeline")
    forecasted_amount: Mapped[float] = mapped_column(Float, default=0.0)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# =====================================================================
# Enterprise CRM Phase 6 — Workflow Automation & Business Process Engine
# =====================================================================

class Workflow(Base):
    """A reusable, versioned workflow definition: trigger + conditions + actions."""

    __tablename__ = "workflows"
    __table_args__ = (
        CheckConstraint(_in("status", WORKFLOW_STATUSES), name="ck_workflow_status"),
        CheckConstraint(_in("trigger_event", WORKFLOW_TRIGGER_EVENTS), name="ck_workflow_trigger"),
        Index("ix_workflows_trigger", "trigger_event"),
        Index("ix_workflows_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    trigger_event: Mapped[str] = mapped_column(String(40), nullable=False)
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    actions: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class WorkflowExecution(Base):
    """Automation history: one row per workflow evaluated-and-run against an entity."""

    __tablename__ = "workflow_executions"
    __table_args__ = (
        CheckConstraint(_in("status", WORKFLOW_EXECUTION_STATUSES), name="ck_wfexec_status"),
        Index("ix_wfexec_workflow", "workflow_id"),
        Index("ix_wfexec_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    trigger_event: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="success")
    actions_executed: Mapped[list] = mapped_column(JSON, default=list)
    error_detail: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)


class ApprovalRequest(Base):
    """An approval gate for large deals, discounts, contract changes, or escalations."""

    __tablename__ = "approval_requests"
    __table_args__ = (
        CheckConstraint(_in("approval_type", WORKFLOW_APPROVAL_TYPES), name="ck_approval_type"),
        CheckConstraint(_in("status", WORKFLOW_APPROVAL_STATUSES), name="ck_approval_status"),
        Index("ix_approvals_status", "status"),
        Index("ix_approvals_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    approval_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    requested_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approver_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(10), default="pending")
    decision_reason: Mapped[str] = mapped_column(Text, default="")
    workflow_execution_id: Mapped[int | None] = mapped_column(
        ForeignKey("workflow_executions.id", ondelete="SET NULL"), nullable=True
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SlaPolicy(Base):
    """A named SLA policy: due-by window + optional escalation."""

    __tablename__ = "sla_policies"
    __table_args__ = (
        Index("ix_sla_policies_entity", "entity_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), default="")
    trigger_event: Mapped[str] = mapped_column(String(40), default="")
    due_hours: Mapped[int] = mapped_column(Integer, default=24)
    escalate_after_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    escalate_to_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class SlaTracker(Base):
    """One tracked instance of an SLA policy against a specific entity."""

    __tablename__ = "sla_trackers"
    __table_args__ = (
        CheckConstraint(_in("status", WORKFLOW_SLA_STATUSES), name="ck_sla_tracker_status"),
        Index("ix_sla_trackers_status", "status"),
        Index("ix_sla_trackers_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("sla_policies.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(30), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="on_track")
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    breached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# =====================================================================
# Enterprise CRM Phase 7 — Custom Objects, Forms & No-Code Platform
# =====================================================================

class CustomObject(Base):
    """A configurable, user-defined CRM object (metadata only — records live in CustomRecord)."""

    __tablename__ = "custom_objects"
    __table_args__ = (
        CheckConstraint(_in("status", CUSTOM_OBJECT_STATUSES), name="ck_custom_object_status"),
        UniqueConstraint("api_name", name="uq_custom_object_api_name"),
        Index("ix_custom_objects_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CustomField(Base):
    """A configurable field definition on a CustomObject."""

    __tablename__ = "custom_fields"
    __table_args__ = (
        CheckConstraint(_in("field_type", CUSTOM_FIELD_TYPES), name="ck_custom_field_type"),
        UniqueConstraint("object_id", "api_name", name="uq_custom_field_api_name"),
        Index("ix_custom_fields_object", "object_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_id: Mapped[int] = mapped_column(
        ForeignKey("custom_objects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    default_value: Mapped[object | None] = mapped_column(JSON, nullable=True)
    validation: Mapped[dict] = mapped_column(JSON, default=dict)
    picklist_options: Mapped[list] = mapped_column(JSON, default=list)
    lookup_object_id: Mapped[int | None] = mapped_column(
        ForeignKey("custom_objects.id", ondelete="SET NULL"), nullable=True
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CustomForm(Base):
    """A reusable form layout (sections/fields/conditional visibility) for a CustomObject."""

    __tablename__ = "custom_forms"
    __table_args__ = (
        Index("ix_custom_forms_object", "object_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_id: Mapped[int] = mapped_column(
        ForeignKey("custom_objects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    layout: Mapped[dict] = mapped_column(JSON, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CustomRecord(Base):
    """One dynamic record of a CustomObject. Field values live in `data`, keyed by field api_name."""

    __tablename__ = "custom_records"
    __table_args__ = (
        Index("ix_custom_records_object", "object_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_id: Mapped[int] = mapped_column(
        ForeignKey("custom_objects.id", ondelete="CASCADE"), nullable=False
    )
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Compliance soft-delete (Phase 9): flagged rather than hard-deleted when a legal
    # hold / retention policy applies. Excluded from normal listing by default.
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CustomRecordAudit(Base):
    """Append-only audit trail of CustomRecord create/update/delete events."""

    __tablename__ = "custom_record_audit"
    __table_args__ = (
        CheckConstraint(_in("action", CUSTOM_RECORD_AUDIT_ACTIONS), name="ck_custom_record_audit_action"),
        Index("ix_custom_record_audit_record", "record_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        ForeignKey("custom_records.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    field_changes: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CustomDataJob(Base):
    """CSV import/export job for a CustomObject, with partial-success reporting."""

    __tablename__ = "custom_data_jobs"
    __table_args__ = (
        CheckConstraint(_in("job_type", CUSTOM_DATA_JOB_TYPES), name="ck_custom_job_type"),
        CheckConstraint(_in("status", CUSTOM_DATA_JOB_STATUSES), name="ck_custom_job_status"),
        Index("ix_custom_data_jobs_object", "object_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_id: Mapped[int] = mapped_column(
        ForeignKey("custom_objects.id", ondelete="CASCADE"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# =====================================================================
# Enterprise CRM Phase 8 — AI Intelligence & Copilot
# =====================================================================

class AiInsight(Base):
    """A deterministic, rules-generated insight about a deal/customer/opportunity/etc."""

    __tablename__ = "ai_insights"
    __table_args__ = (
        CheckConstraint(_in("insight_type", AI_INSIGHT_TYPES), name="ck_ai_insight_type"),
        CheckConstraint(_in("severity", AI_INSIGHT_SEVERITIES), name="ck_ai_insight_severity"),
        CheckConstraint(_in("confidence", CONFIDENCE_LEVELS), name="ck_ai_insight_confidence"),
        CheckConstraint(_in("status", AI_INSIGHT_STATUSES), name="ck_ai_insight_status"),
        Index("ix_ai_insights_type", "insight_type"),
        Index("ix_ai_insights_status", "status"),
        Index("ix_ai_insights_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    insight_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(10), default="medium")
    confidence: Mapped[str] = mapped_column(String(10), default="medium")
    status: Mapped[str] = mapped_column(String(10), default="active")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AiRecommendation(Base):
    """A deterministic, rules-generated action recommendation."""

    __tablename__ = "ai_recommendations"
    __table_args__ = (
        CheckConstraint(_in("recommendation_type", AI_RECOMMENDATION_TYPES), name="ck_ai_rec_type"),
        CheckConstraint(_in("status", AI_RECOMMENDATION_STATUSES), name="ck_ai_rec_status"),
        Index("ix_ai_recs_type", "recommendation_type"),
        Index("ix_ai_recs_status", "status"),
        Index("ix_ai_recs_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recommendation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    status: Mapped[str] = mapped_column(String(10), default="pending")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class AiRiskScore(Base):
    """A deterministic risk score for an entity (stalled deal, at-risk customer, etc.)."""

    __tablename__ = "ai_risk_scores"
    __table_args__ = (
        CheckConstraint(_in("risk_type", AI_RISK_TYPES), name="ck_ai_risk_type"),
        CheckConstraint(_in("severity", AI_INSIGHT_SEVERITIES), name="ck_ai_risk_severity"),
        Index("ix_ai_risks_type", "risk_type"),
        Index("ix_ai_risks_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    risk_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[str] = mapped_column(String(10), default="medium")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AiEngagementScore(Base):
    """A computed engagement score for a customer/company, from activity/meeting/task data."""

    __tablename__ = "ai_engagement_scores"
    __table_args__ = (
        CheckConstraint(_in("trend", CS_HEALTH_TRENDS), name="ck_ai_engagement_trend"),
        Index("ix_ai_engagement_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(30), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    email_activity_score: Mapped[float] = mapped_column(Float, default=0.0)
    meeting_activity_score: Mapped[float] = mapped_column(Float, default=0.0)
    task_completion_score: Mapped[float] = mapped_column(Float, default=0.0)
    trend: Mapped[str] = mapped_column(String(10), default="stable")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AiBriefing(Base):
    """A generated executive briefing snapshot (revenue/pipeline/risk/expansion/renewal/workflow)."""

    __tablename__ = "ai_briefings"
    __table_args__ = (
        Index("ix_ai_briefings_generated", "generated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period: Mapped[str] = mapped_column(String(20), default="")
    sections: Mapped[dict] = mapped_column(JSON, default=dict)
    generated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AiCopilotQuery(Base):
    """Usage log of Copilot summary requests, for Copilot-usage analytics."""

    __tablename__ = "ai_copilot_queries"
    __table_args__ = (
        CheckConstraint(_in("query_type", AI_COPILOT_QUERY_TYPES), name="ck_ai_copilot_type"),
        Index("ix_ai_copilot_type", "query_type"),
        Index("ix_ai_copilot_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    response_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# =====================================================================
# Enterprise CRM Phase 9 — Enterprise Administration, Security & Compliance
# =====================================================================

class Organization(Base):
    """The tenant/organization profile. Typically a single active row on this platform."""

    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_organization_slug"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    industry: Mapped[str] = mapped_column(String(100), default="")
    size: Mapped[str] = mapped_column(String(30), default="")
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    feature_flags: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class OrgUnit(Base):
    """A business unit / department / team within an organization (one type-discriminated hierarchy)."""

    __tablename__ = "org_units"
    __table_args__ = (
        CheckConstraint(_in("unit_type", ORG_UNIT_TYPES), name="ck_org_unit_type"),
        Index("ix_org_units_org", "organization_id"),
        Index("ix_org_units_parent", "parent_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("org_units.id", ondelete="SET NULL"), nullable=True
    )
    lead_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class OrgUnitMember(Base):
    """A user's membership (and role) within an org unit."""

    __tablename__ = "org_unit_members"
    __table_args__ = (
        CheckConstraint(_in("role", ORG_UNIT_MEMBER_ROLES), name="ck_org_unit_member_role"),
        UniqueConstraint("unit_id", "user_id", name="uq_org_unit_member"),
        Index("ix_org_unit_members_unit", "unit_id"),
        Index("ix_org_unit_members_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("org_units.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(10), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class SystemSetting(Base):
    """Generic key/value platform configuration, one row per (category, key)."""

    __tablename__ = "system_settings"
    __table_args__ = (
        CheckConstraint(_in("category", SETTINGS_CATEGORIES), name="ck_system_setting_category"),
        UniqueConstraint("category", "key", name="uq_system_setting_key"),
        Index("ix_system_settings_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class SecurityPolicy(Base):
    """One configurable security policy (password/session/login/ip-allowlist/lockout/MFA)."""

    __tablename__ = "security_policies"
    __table_args__ = (
        CheckConstraint(_in("policy_type", SECURITY_POLICY_TYPES), name="ck_security_policy_type"),
        UniqueConstraint("policy_type", name="uq_security_policy_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_type: Mapped[str] = mapped_column(String(20), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class AuditEvent(Base):
    """Immutable, insert-only cross-cutting audit trail (auth/admin/permissions/workflow/config/AI/export)."""

    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(_in("category", AUDIT_CATEGORIES), name="ck_audit_event_category"),
        Index("ix_audit_events_category", "category"),
        Index("ix_audit_events_actor", "actor_id"),
        Index("ix_audit_events_entity", "entity_type", "entity_id"),
        Index("ix_audit_events_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_email: Mapped[str] = mapped_column(String(320), default="")
    entity_type: Mapped[str] = mapped_column(String(30), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ComplianceRecord(Base):
    """A legal hold, consent record, or data export/deletion request."""

    __tablename__ = "compliance_records"
    __table_args__ = (
        CheckConstraint(_in("record_type", COMPLIANCE_RECORD_TYPES), name="ck_compliance_type"),
        CheckConstraint(_in("status", COMPLIANCE_STATUSES), name="ck_compliance_status"),
        Index("ix_compliance_type", "record_type"),
        Index("ix_compliance_status", "status"),
        Index("ix_compliance_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(10), default="pending")
    requested_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApiKey(Base):
    """A platform API key. Only key_hash + key_prefix are stored — the raw key is shown once."""

    __tablename__ = "api_keys"
    __table_args__ = (
        CheckConstraint(_in("status", API_KEY_STATUSES), name="ck_api_key_status"),
        UniqueConstraint("key_hash", name="uq_api_key_hash"),
        Index("ix_api_keys_owner", "owner_id"),
        Index("ix_api_keys_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), default="")
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(10), default="active")
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# =====================================================================
# Enterprise CRM Phase 10 — Integration Platform & Developer Ecosystem
# =====================================================================

class Integration(Base):
    """A registered third-party (or internal) integration entry."""

    __tablename__ = "integrations"
    __table_args__ = (
        CheckConstraint(_in("category", INTEGRATION_CATEGORIES), name="ck_integration_category"),
        CheckConstraint(_in("status", INTEGRATION_STATUSES), name="ck_integration_status"),
        CheckConstraint(_in("health_status", INTEGRATION_HEALTH_STATUSES), name="ck_integration_health"),
        Index("ix_integrations_category", "category"),
        Index("ix_integrations_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), default="")
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending_setup")
    version: Mapped[str] = mapped_column(String(30), default="1.0.0")
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    health_status: Mapped[str] = mapped_column(String(10), default="unknown")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class Webhook(Base):
    """An outbound webhook subscription to one Event Bus event_type (or '*' for all)."""

    __tablename__ = "webhooks"
    __table_args__ = (
        CheckConstraint(_in("status", WEBHOOK_STATUSES), name="ck_webhook_status"),
        Index("ix_webhooks_event_type", "event_type"),
        Index("ix_webhooks_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    target_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    secret: Mapped[str] = mapped_column(String(128), default="")
    retry_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(10), default="enabled")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class WebhookDelivery(Base):
    """One delivery attempt-history row for a webhook against a published event."""

    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        CheckConstraint(_in("status", WEBHOOK_DELIVERY_STATUSES), name="ck_webhook_delivery_status"),
        Index("ix_webhook_deliveries_webhook", "webhook_id"),
        Index("ix_webhook_deliveries_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    webhook_id: Mapped[int] = mapped_column(ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(10), default="pending")
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    error_detail: Mapped[str] = mapped_column(Text, default="")
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class OAuthCredential(Base):
    """A registered OAuth client credential for an external provider. Registration only —
    no live token exchange is performed (see integration_service module docstring)."""

    __tablename__ = "oauth_credentials"
    __table_args__ = (
        CheckConstraint(_in("status", OAUTH_CREDENTIAL_STATUSES), name="ck_oauth_cred_status"),
        Index("ix_oauth_credentials_owner", "owner_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), default="")
    client_secret_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="active")
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IntegrationEvent(Base):
    """The Event Bus log: one immutable row per published internal event."""

    __tablename__ = "integration_events"
    __table_args__ = (
        CheckConstraint(_in("category", EVENT_BUS_CATEGORIES), name="ck_integration_event_category"),
        Index("ix_integration_events_category", "category"),
        Index("ix_integration_events_type", "event_type"),
        Index("ix_integration_events_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Connector(Base):
    """A reusable connector definition (HTTP/REST/webhook/scheduled) with lifecycle state."""

    __tablename__ = "connectors"
    __table_args__ = (
        CheckConstraint(_in("connector_type", CONNECTOR_TYPES), name="ck_connector_type"),
        CheckConstraint(_in("status", CONNECTOR_STATUSES), name="ck_connector_status"),
        Index("ix_connectors_type", "connector_type"),
        Index("ix_connectors_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(20), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    schedule_cron: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(10), default="active")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[str] = mapped_column(String(10), default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ConnectorRun(Base):
    """One execution-history row for a connector run."""

    __tablename__ = "connector_runs"
    __table_args__ = (
        CheckConstraint(_in("status", CONNECTOR_RUN_STATUSES), name="ck_connector_run_status"),
        Index("ix_connector_runs_connector", "connector_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connector_id: Mapped[int] = mapped_column(ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="running")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    result_detail: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Plugin(Base):
    """A registered plugin: metadata, declared permissions, and the hooks it listens on."""

    __tablename__ = "plugins"
    __table_args__ = (
        CheckConstraint(_in("status", PLUGIN_STATUSES), name="ck_plugin_status"),
        UniqueConstraint("name", "version", name="uq_plugin_name_version"),
        Index("ix_plugins_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(30), default="1.0.0")
    plugin_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    execution_hooks: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(10), default="enabled")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class PluginExecution(Base):
    """One execution-hook invocation log row. Deterministic: plugins carry no arbitrary
    executable code, so an 'execution' is a recorded, permission-checked hook dispatch —
    see integration_service.trigger_plugin_hook."""

    __tablename__ = "plugin_executions"
    __table_args__ = (
        CheckConstraint(_in("status", PLUGIN_EXECUTION_STATUSES), name="ck_plugin_exec_status"),
        Index("ix_plugin_executions_plugin", "plugin_id"),
        Index("ix_plugin_executions_hook", "hook_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plugin_id: Mapped[int] = mapped_column(ForeignKey("plugins.id", ondelete="CASCADE"), nullable=False)
    hook_name: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="success")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# =====================================================================
# Enterprise CRM Phase 11 — Enterprise Search & Knowledge Platform
# =====================================================================

class SavedSearch(Base):
    """A named, re-runnable search query (optionally favorited / shared)."""

    __tablename__ = "saved_searches"
    __table_args__ = (
        Index("ix_saved_searches_owner", "owner_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    query: Mapped[dict] = mapped_column(JSON, default=dict)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class SearchHistory(Base):
    """One row per executed search — powers Recent Searches + Search Analytics."""

    __tablename__ = "search_history"
    __table_args__ = (
        Index("ix_search_history_user", "user_id"),
        Index("ix_search_history_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    query_text: Mapped[str] = mapped_column(String(500), default="")
    entity_types: Mapped[list] = mapped_column(JSON, default=list)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    response_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class KbCategory(Base):
    """A knowledge-base category (self-referential hierarchy, like OrgUnit)."""

    __tablename__ = "kb_categories"
    __table_args__ = (
        Index("ix_kb_categories_parent", "parent_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("kb_categories.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class KbArticle(Base):
    """A knowledge-base article with a draft -> pending_approval -> published -> archived lifecycle."""

    __tablename__ = "kb_articles"
    __table_args__ = (
        CheckConstraint(_in("status", KB_ARTICLE_STATUSES), name="ck_kb_article_status"),
        Index("ix_kb_articles_category", "category_id"),
        Index("ix_kb_articles_status", "status"),
        Index("ix_kb_articles_owner", "owner_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("kb_categories.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KbArticleVersion(Base):
    """Snapshot of an article's title/body taken immediately before an edit that changed either."""

    __tablename__ = "kb_article_versions"
    __table_args__ = (
        Index("ix_kb_article_versions_article", "article_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("kb_articles.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    edited_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class KbAttachment(Base):
    """Attachment metadata on a knowledge article. ponytail: metadata only (filename/content
    type/size), same scope call as Phase 7's CSV import — no binary storage layer exists in
    this platform yet; upgrade path is an object-storage-backed file field."""

    __tablename__ = "kb_attachments"
    __table_args__ = (
        Index("ix_kb_attachments_article", "article_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("kb_articles.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class KbArticleView(Base):
    """One row per article view — powers Article Views / Article Usage analytics."""

    __tablename__ = "kb_article_views"
    __table_args__ = (
        Index("ix_kb_article_views_article", "article_id"),
        Index("ix_kb_article_views_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("kb_articles.id", ondelete="CASCADE"), nullable=False)
    viewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# =====================================================================
# Enterprise CRM Phase 12 — Data Warehouse & Advanced Business Intelligence
# =====================================================================

class WarehouseSnapshot(Base):
    """A point-in-time historical snapshot of one metric_type's aggregate figures."""

    __tablename__ = "warehouse_snapshots"
    __table_args__ = (
        CheckConstraint(_in("metric_type", WAREHOUSE_METRIC_TYPES), name="ck_warehouse_metric_type"),
        Index("ix_warehouse_snapshots_type", "metric_type"),
        Index("ix_warehouse_snapshots_date", "snapshot_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_type: Mapped[str] = mapped_column(String(20), nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Kpi(Base):
    """A configurable KPI definition with an optional target."""

    __tablename__ = "kpis"
    __table_args__ = (
        CheckConstraint(_in("category", KPI_CATEGORIES), name="ck_kpi_category"),
        UniqueConstraint("name", name="uq_kpi_name"),
        Index("ix_kpis_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class KpiValue(Base):
    """One historical value observation for a KPI."""

    __tablename__ = "kpi_values"
    __table_args__ = (
        Index("ix_kpi_values_kpi", "kpi_id"),
        Index("ix_kpi_values_recorded", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kpi_id: Mapped[int] = mapped_column(ForeignKey("kpis.id", ondelete="CASCADE"), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CustomReport(Base):
    """A saved, buildable report definition (entity + filters + grouping)."""

    __tablename__ = "custom_reports"
    __table_args__ = (
        CheckConstraint(_in("status", REPORT_STATUSES), name="ck_report_status"),
        Index("ix_custom_reports_owner", "owner_id"),
        Index("ix_custom_reports_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    group_by: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(10), default="draft")
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ReportSchedule(Base):
    """A recurring delivery schedule for a CustomReport."""

    __tablename__ = "report_schedules"
    __table_args__ = (
        CheckConstraint(_in("frequency", REPORT_SCHEDULE_FREQUENCIES), name="ck_report_schedule_freq"),
        Index("ix_report_schedules_report", "report_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("custom_reports.id", ondelete="CASCADE"), nullable=False)
    frequency: Mapped[str] = mapped_column(String(10), nullable=False)
    recipient_emails: Mapped[list] = mapped_column(JSON, default=list)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ScheduledReportRun(Base):
    """Delivery history for a ReportSchedule tick (Report History)."""

    __tablename__ = "scheduled_report_runs"
    __table_args__ = (
        CheckConstraint(_in("status", SCHEDULED_REPORT_RUN_STATUSES), name="ck_scheduled_run_status"),
        Index("ix_scheduled_report_runs_schedule", "schedule_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("report_schedules.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="pending")
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[str] = mapped_column(Text, default="")
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ============================================================ Machine Learning Foundation
# Infrastructure for a future recommendation model (feature store, embeddings cache,
# user-feedback dataset, and versioning registries). NO classifier/model is trained
# here; these tables only capture and version the inputs. None of it is wired into the
# Standard Run / scheduler — feature generation is incremental + cached and runs on demand.
class MlFeatureRow(Base):
    """Feature-store cache: one computed feature vector per entity + feature version.

    ``source_hash`` is a digest of the raw inputs the features were built from, so an
    incremental refresh can skip an entity whose inputs are unchanged (no recompute).
    The SAME builder produces these for both training and online inference.
    """

    __tablename__ = "ml_feature_rows"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "feature_version", name="uq_ml_feature_row"),
        Index("ix_ml_feature_rows_version", "feature_version"),
        CheckConstraint(_in("entity_type", ML_ENTITY_TYPES), name="ck_ml_feature_entity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(20), default="company")
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    feature_version: Mapped[str] = mapped_column(String(40), default="fs-1")
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    source_hash: Mapped[str] = mapped_column(String(64), default="")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RoleEmbedding(Base):
    """Cached semantic embedding for a decision-maker role/title.

    Keyed by ``title_hash`` (a hash of the normalized title) so an unchanged title is
    never re-embedded. Backend + model name are recorded so a later upgrade (e.g.
    swapping the hash fallback for all-MiniLM-L6-v2) is explicit and cache-busting.
    """

    __tablename__ = "role_embeddings"
    __table_args__ = (
        UniqueConstraint("title_hash", "model_name", name="uq_role_embedding"),
        Index("ix_role_embeddings_hash", "title_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title_norm: Mapped[str] = mapped_column(String(512), default="")
    model_name: Mapped[str] = mapped_column(String(80), default="")
    dim: Mapped[int] = mapped_column(Integer, default=0)
    vector: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class UserInteraction(Base):
    """User feedback / interaction event, stored SEPARATELY from opportunity data.

    Captures thumbs up/down, export, contact, ignore against any entity, with a
    configurable ``sample_weight`` the training-dataset builder uses later. This is the
    labelled-feedback source for a future model — nothing is trained here.
    """

    __tablename__ = "user_interactions"
    __table_args__ = (
        CheckConstraint(_in("interaction_type", ML_INTERACTION_TYPES), name="ck_ml_interaction_type"),
        CheckConstraint(_in("entity_type", ML_ENTITY_TYPES), name="ck_ml_interaction_entity"),
        Index("ix_user_interactions_entity", "entity_type", "entity_id"),
        Index("ix_user_interactions_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email: Mapped[str] = mapped_column(String(320), default="")
    interaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), default="opportunity")
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    company_domain: Mapped[str] = mapped_column(String(255), default="")
    sample_weight: Mapped[float] = mapped_column(Float, default=1.0)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MlFeatureVersion(Base):
    """Feature-versioning registry: the spec (feature names/order) for a version."""

    __tablename__ = "ml_feature_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    spec: Mapped[dict] = mapped_column(JSON, default=dict)
    feature_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MlModel(Base):
    """Model registry + metadata (versioning). Infrastructure only — no classifier is
    trained yet; this records what WOULD be produced (name/version/status/metrics)."""

    __tablename__ = "ml_models"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_ml_model_version"),
        CheckConstraint(_in("status", ML_MODEL_STATUSES), name="ck_ml_model_status"),
        Index("ix_ml_models_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), default="lead_recommender")
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    model_type: Mapped[str] = mapped_column(String(60), default="")
    feature_version: Mapped[str] = mapped_column(String(40), default="")
    artifact_path: Mapped[str] = mapped_column(String(512), default="")
    # Serialized model (base64 joblib) so a candidate can be loaded for inference /
    # promotion without a filesystem; feature_importance drives explainability (0046).
    artifact: Mapped[str] = mapped_column(Text, default="")
    feature_importance: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    model_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MlModelEvent(Base):
    """Audit trail for the model registry: trained / promoted / rejected / rolled_back."""

    __tablename__ = "ml_model_events"
    __table_args__ = (
        Index("ix_ml_model_events_model", "model_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("ml_models.id", ondelete="SET NULL"), nullable=True)
    model_version: Mapped[str] = mapped_column(String(40), default="")
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    actor_email: Mapped[str] = mapped_column(String(320), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MlRecommendation(Base):
    """Offline inference output: a model's recommendation probability for an entity,
    stored ALONGSIDE (never inside) the existing lead score. The dashboard keeps using
    lead_scores; this is a separate, additive signal."""

    __tablename__ = "ml_recommendations"
    __table_args__ = (
        UniqueConstraint("model_version", "entity_type", "entity_id", name="uq_ml_recommendation"),
        Index("ix_ml_recommendations_domain", "company_domain"),
        Index("ix_ml_recommendations_model", "model_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("ml_models.id", ondelete="SET NULL"), nullable=True)
    model_version: Mapped[str] = mapped_column(String(40), default="")
    entity_type: Mapped[str] = mapped_column(String(20), default="company")
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    company_domain: Mapped[str] = mapped_column(String(255), default="")
    probability: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MlTrainingRun(Base):
    """Training-run metadata (dataset version, window, feature version, params, metrics).

    Recorded by the dataset builder (status='dataset_built') and, later, by training.
    """

    __tablename__ = "ml_training_runs"
    __table_args__ = (
        Index("ix_ml_training_runs_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("ml_models.id", ondelete="SET NULL"), nullable=True)
    dataset_version: Mapped[str] = mapped_column(String(60), default="")
    feature_version: Mapped[str] = mapped_column(String(40), default="")
    window_days: Mapped[int] = mapped_column(Integer, default=0)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    positive_count: Mapped[int] = mapped_column(Integer, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="dataset_built")
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
