"""Feature Store — convert existing platform intelligence into ML features.

ONE deterministic feature builder, reused for both training and online inference. It
reuses the platform's existing aggregates (the same cross-engine rollups the Lead
Scorer reads) and adds news / signal-age / decay / technology-tag / role-embedding
features. Nothing here modifies source data or touches the scheduler.

Performance:
  * batch-loads every aggregate once (no per-company N+1),
  * caches feature rows in ``ml_feature_rows`` keyed by a ``source_hash`` of the raw
    inputs, so an incremental refresh skips companies whose inputs are unchanged
    (recomputed at most once per UTC day so time-decay/age stay fresh),
  * reuses the cached role embeddings (unchanged titles are never re-embedded).
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from integration.news import dedup
from master_db.models import (
    Company,
    CompanyRollup,
    DecisionMaker,
    DemandSignal,
    LeadScore,
    MlFeatureRow,
    Opportunity,
)
from ml import decay as decay_mod
from ml import embeddings as emb
from ml import feedback

logger = logging.getLogger("ml.features")

# Bump to invalidate the feature cache (new row set built). Kept in code + registered
# in ml_feature_versions; the runtime value can be overridden via settings.
FEATURE_VERSION = "fs-1"

_TIER_RANK = {"STARTUP": 1, "SCALEUP": 2, "ESTABLISHED": 3, "INCUMBENT": 4, "UNKNOWN": 0}
_GRADE_RANK = {"A+": 6, "A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "": 0}


def _days_since(date_str: str, now: datetime) -> float | None:
    dt = dedup._parse_date(date_str or "")
    if dt is None:
        return None
    return max(0.0, (now - dt).total_seconds() / 86400.0)


@dataclass
class _Bundle:
    """Batch-loaded raw inputs shared across every company's feature build."""

    now: datetime
    half_lives: dict[str, int]
    companies: dict[str, Company] = field(default_factory=dict)
    opps: dict[str, list[Opportunity]] = field(default_factory=dict)
    demand: dict[str, DemandSignal] = field(default_factory=dict)
    rollup: dict[str, CompanyRollup] = field(default_factory=dict)
    dms: dict[str, list[DecisionMaker]] = field(default_factory=dict)
    leadscore: dict[str, LeadScore] = field(default_factory=dict)
    engagement: dict[str, dict[str, int]] = field(default_factory=dict)
    role_vectors: dict[str, list[float]] = field(default_factory=dict)  # title -> embedding
    embedding_dim: int = 384


def load_bundle(session: Session, settings, *, domains: list[str] | None = None) -> _Bundle:
    """Load every aggregate once (batch). Embeds all distinct DM titles via the cache."""
    now = datetime.now(timezone.utc)
    b = _Bundle(now=now, half_lives=settings.decay_half_lives(),
                embedding_dim=settings.ml_embedding_dim)

    comp_q = select(Company)
    if domains is not None:
        comp_q = comp_q.where(Company.company_domain.in_(domains))
    b.companies = {c.company_domain: c for c in session.scalars(comp_q)}
    keys = set(b.companies)

    for o in session.scalars(select(Opportunity)):
        if o.company_domain in keys:
            b.opps.setdefault(o.company_domain, []).append(o)
    b.demand = {d.company_domain: d for d in session.scalars(select(DemandSignal)) if d.company_domain in keys}
    b.rollup = {r.company_domain: r for r in session.scalars(select(CompanyRollup)) if r.company_domain in keys}
    for dm in session.scalars(select(DecisionMaker).where(DecisionMaker.company_domain.isnot(None))):
        if dm.company_domain in keys:
            b.dms.setdefault(dm.company_domain, []).append(dm)
    b.leadscore = {s.company_domain: s for s in session.scalars(select(LeadScore)) if s.company_domain in keys}
    b.engagement = {k: v for k, v in feedback.engagement_counts(session).items() if k in keys}

    titles = sorted({(dm.current_title or dm.headline or "").strip()
                     for dms in b.dms.values() for dm in dms if (dm.current_title or dm.headline)})
    if titles:
        b.role_vectors = emb.embed_titles(session, titles, settings)
    return b


def _source_hash(b: _Bundle, domain: str) -> str:
    """Digest of the raw inputs for a company — unchanged inputs => identical hash."""
    c = b.companies[domain]
    payload = {
        "company": [c.company_tier, c.prospect_type, c.compliance_flag, c.industry_category,
                    c.sub_category, c.technology_focus, c.website],
        "opps": sorted([(o.opportunity_id, o.opportunity_type, o.effective_opportunity_score,
                         o.published_date, o.lifecycle_status) for o in b.opps.get(domain, [])]),
        "demand": (b.demand[domain].demand_score, b.demand[domain].total_engineering_jobs)
        if domain in b.demand else None,
        "dms": sorted([(dm.id, dm.current_title, dm.seniority,
                        dm.agent_score if dm.agent_score is not None else dm.match_score)
                       for dm in b.dms.get(domain, [])]),
        "lead": (b.leadscore[domain].lead_score, b.leadscore[domain].grade) if domain in b.leadscore else None,
        "engagement": b.engagement.get(domain),
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def build_company_features(domain: str, b: _Bundle) -> dict:
    """Deterministic feature dict for one company from the shared bundle."""
    c = b.companies[domain]
    opps = b.opps.get(domain, [])
    d = b.demand.get(domain)
    r = b.rollup.get(domain)
    dms = b.dms.get(domain, [])
    ls = b.leadscore.get(domain)
    eng = b.engagement.get(domain, {"positive": 0, "negative": 0, "total": 0})

    # opportunity / news + signal age + decay + tech tags (from opportunities)
    eff_scores = [float(o.effective_opportunity_score or 0) for o in opps]
    ages = [a for o in opps if (a := _days_since(o.published_date, b.now)) is not None]
    decay_items = [(o.opportunity_type, float(o.effective_opportunity_score or 0),
                    _days_since(o.published_date, b.now) or 0.0) for o in opps]
    df = decay_mod.decay_features(decay_items, b.half_lives)

    tech_tags: set[str] = set()
    if c.technology_focus:
        tech_tags.update(t.strip() for t in c.technology_focus.replace(";", ",").split(",") if t.strip())
    for o in opps:
        for t in (o.technologies or []):
            if t:
                tech_tags.add(str(t).strip())

    # decision-maker + role-embedding features (mean role vector for the company)
    dm_titles = [(dm.current_title or dm.headline or "").strip() for dm in dms]
    dm_vectors = [b.role_vectors[t] for t in dm_titles if t in b.role_vectors]
    role_mean = emb.mean_vector(dm_vectors, b.embedding_dim)
    dm_scores = [float(dm.agent_score if dm.agent_score is not None else dm.match_score) for dm in dms]

    return {
        # --- company features ---
        "company_tier_rank": _TIER_RANK.get(c.company_tier or "UNKNOWN", 0),
        "prospect_type": c.prospect_type or "UNKNOWN",
        "compliance_ok": 1 if c.compliance_flag == "APPROVED" else 0,
        "has_website": 1 if c.website else 0,
        # --- industry classifications ---
        "industry_category": c.industry_category or "",
        "sub_category": c.sub_category or "",
        # --- opportunity + news features ---
        "num_opportunities": len(opps),
        "max_effective_opportunity_score": max(eff_scores) if eff_scores else 0.0,
        "mean_opportunity_score": round(sum(eff_scores) / len(eff_scores), 4) if eff_scores else 0.0,
        "distinct_opportunity_types": len({o.opportunity_type for o in opps if o.opportunity_type}),
        "news_active_count": df.active_count,
        # --- signal age ---
        "newest_signal_age_days": round(min(ages), 2) if ages else -1.0,
        "oldest_signal_age_days": round(max(ages), 2) if ages else -1.0,
        # --- dynamic time decay (generated feature) ---
        "decay_layoffs": df.per_category["layoffs"],
        "decay_hiring": df.per_category["hiring"],
        "decay_projects": df.per_category["projects"],
        "decay_funding": df.per_category["funding"],
        "decay_overall_max": df.overall_max,
        "decay_overall_mean": df.overall_mean,
        # --- career features ---
        "total_engineering_jobs": int(d.total_engineering_jobs) if d else 0,
        "demand_score": float(d.demand_score) if d else 0.0,
        "normalized_demand_score": float(d.normalized_demand_score) if d else 0.0,
        "demand_readiness": float(d.lead_readiness_score) if d else 0.0,
        "rollup_readiness": float(r.lead_readiness_score) if r else 0.0,
        # --- decision maker features ---
        "dm_count": len(dms),
        "senior_dm_count": sum(1 for dm in dms if dm.seniority == "senior"),
        "avg_dm_score": round(sum(dm_scores) / len(dm_scores), 4) if dm_scores else 0.0,
        # --- lead score (existing model output, reused as a feature) ---
        "lead_score": float(ls.lead_score) if ls else 0.0,
        "lead_grade_rank": _GRADE_RANK.get(ls.grade if ls else "", 0),
        "opportunity_subscore": float(ls.opportunity_subscore) if ls else 0.0,
        "demand_subscore": float(ls.demand_subscore) if ls else 0.0,
        "readiness_subscore": float(ls.readiness_subscore) if ls else 0.0,
        "dm_subscore": float(ls.dm_subscore) if ls else 0.0,
        "coverage": int(ls.coverage) if ls else 0,
        # --- historical engagement (feedback) ---
        "engagement_positive": eng["positive"],
        "engagement_negative": eng["negative"],
        "engagement_total": eng["total"],
        # --- technology tags (list) + role embedding (list) ---
        "tech_tag_count": len(tech_tags),
        "tech_tags": sorted(tech_tags),
        "dm_role_embedding_mean": role_mean,
    }


# feature names that are plain scalars (for the versioning spec / dataset columns).
def feature_spec() -> list[str]:
    return [
        "company_tier_rank", "compliance_ok", "has_website",
        "num_opportunities", "max_effective_opportunity_score", "mean_opportunity_score",
        "distinct_opportunity_types", "news_active_count",
        "newest_signal_age_days", "oldest_signal_age_days",
        "decay_layoffs", "decay_hiring", "decay_projects", "decay_funding",
        "decay_overall_max", "decay_overall_mean",
        "total_engineering_jobs", "demand_score", "normalized_demand_score",
        "demand_readiness", "rollup_readiness",
        "dm_count", "senior_dm_count", "avg_dm_score",
        "lead_score", "lead_grade_rank", "opportunity_subscore", "demand_subscore",
        "readiness_subscore", "dm_subscore", "coverage",
        "engagement_positive", "engagement_negative", "engagement_total", "tech_tag_count",
    ]


@dataclass
class BatchResult:
    feature_version: str
    computed: int = 0
    reused: int = 0
    total: int = 0
    features: dict[str, dict] = field(default_factory=dict)


def build_features_batch(session: Session, settings, *, domains: list[str] | None = None,
                         incremental: bool = True, persist: bool = True) -> BatchResult:
    """Build (and optionally cache) features for every company.

    Incremental: a company whose ``source_hash`` matches its cached row AND was computed
    today is reused (not recomputed) — so repeat/scheduled refreshes do near-zero work
    when nothing changed. Set ``incremental=False`` to force a full rebuild."""
    version = settings.ml_feature_version or FEATURE_VERSION
    b = load_bundle(session, settings, domains=domains)
    res = BatchResult(feature_version=version, total=len(b.companies))

    existing: dict[str, MlFeatureRow] = {}
    if (incremental or persist) and b.companies:
        rows = session.scalars(
            select(MlFeatureRow).where(
                MlFeatureRow.entity_type == "company",
                MlFeatureRow.feature_version == version,
                MlFeatureRow.entity_id.in_(list(b.companies)),
            )
        ).all()
        existing = {r.entity_id: r for r in rows}

    today = b.now.date()
    for domain in b.companies:
        shash = _source_hash(b, domain)
        prev = existing.get(domain)
        if (incremental and prev is not None and prev.source_hash == shash
                and prev.computed_at and _as_utc(prev.computed_at).date() == today):
            res.reused += 1
            res.features[domain] = prev.features
            continue
        feats = build_company_features(domain, b)
        res.features[domain] = feats
        res.computed += 1
        if persist:
            if prev is None:
                session.add(MlFeatureRow(entity_type="company", entity_id=domain,
                                         feature_version=version, features=feats,
                                         source_hash=shash, computed_at=b.now))
            else:
                prev.features, prev.source_hash, prev.computed_at = feats, shash, b.now
    if persist:
        session.flush()
    logger.info("features %s: computed=%d reused=%d total=%d", version, res.computed, res.reused, res.total)
    return res


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
