"""Merge one company into another (review-queue "merge" action).

Re-points all child rows from *source_domain* to *target_domain*, resolving the
constraints that make this non-trivial:
  * opportunities / decision_makers — globally-unique PKs -> straight re-point.
  * jobs — UNIQUE(company_domain, job_url): drop source jobs whose url already
    exists at target, move the rest.
  * demand_signals / company_rollups / lead_scores — 1:1 (PK = domain): move the
    source's row only if the target has none, else drop the source's.
  * company_aliases / company_sources — re-point; record source name -> target.
Then delete the (stub) source company. Caller wraps this in a transaction.
"""
from __future__ import annotations

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from integration.normalizer import name_key
from master_db.models import (
    CompanyAlias,
    CompanyRollup,
    CompanySource,
    Company,
    DecisionMaker,
    DemandSignal,
    Job,
    LeadScore,
    Opportunity,
)


def merge_company(session: Session, source_domain: str, target_domain: str) -> dict[str, int]:
    """Merge *source_domain* into *target_domain*. Returns moved-row counts."""
    if source_domain == target_domain:
        raise ValueError("source and target are the same domain")
    src = session.get(Company, source_domain)
    tgt = session.get(Company, target_domain)
    if src is None:
        raise ValueError(f"source company '{source_domain}' not found")
    if tgt is None:
        raise ValueError(f"target company '{target_domain}' not found")

    moved = {"opportunities": 0, "jobs": 0, "decision_makers": 0, "jobs_deduped": 0}

    # --- globally-unique-PK children: straight re-point ---
    moved["opportunities"] = session.execute(
        update(Opportunity).where(Opportunity.company_domain == source_domain)
        .values(company_domain=target_domain)
    ).rowcount or 0
    moved["decision_makers"] = session.execute(
        update(DecisionMaker).where(DecisionMaker.company_domain == source_domain)
        .values(company_domain=target_domain)
    ).rowcount or 0

    # --- jobs: respect UNIQUE(company_domain, job_url) ---
    target_urls = set(session.scalars(
        select(Job.job_url).where(Job.company_domain == target_domain)
    ).all())
    for job in session.scalars(select(Job).where(Job.company_domain == source_domain)).all():
        if job.job_url in target_urls:
            session.delete(job)
            moved["jobs_deduped"] += 1
        else:
            job.company_domain = target_domain
            moved["jobs"] += 1
    session.flush()

    # --- 1:1 rollups: move only if target lacks them ---
    for model in (DemandSignal, CompanyRollup, LeadScore):
        if session.get(model, source_domain) is None:
            continue
        if session.get(model, target_domain) is None:
            session.execute(
                update(model).where(model.company_domain == source_domain)
                .values(company_domain=target_domain)
            )
        else:
            session.execute(delete(model).where(model.company_domain == source_domain))
    session.flush()

    # --- aliases + provenance ---
    session.execute(delete(CompanyAlias).where(CompanyAlias.company_domain == source_domain))
    key = name_key(src.company_name)
    if key and session.scalar(
        select(CompanyAlias).where(CompanyAlias.name_key == key, CompanyAlias.company_domain == target_domain)
    ) is None:
        session.add(CompanyAlias(alias=src.company_name, name_key=key,
                                 company_domain=target_domain, source="merge"))
    session.execute(
        update(CompanySource).where(CompanySource.company_domain == source_domain)
        .values(company_domain=target_domain)
    )
    session.flush()

    # --- drop the now-empty source company ---
    session.delete(src)
    session.flush()
    return moved
