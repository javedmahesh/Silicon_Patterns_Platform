"""Purge competitor "service provider" companies + their dependent data.

Service providers (IT / design-services firms) are the team's competitors; the
platform doesn't keep them. This deletes every ``SERVICE_PROVIDER`` company (and any
known competitor domain from ``config/employer_seeds.json``) plus the rows that hang
off it — decision makers, jobs, demand signals, rollups, opportunities, lead scores,
sources, aliases — and any review-queue rows pointing at those domains.

    python scripts/purge_service_providers.py            # dry run: report only
    python scripts/purge_service_providers.py --apply     # actually delete

Idempotent. Honors ``DATABASE_URL`` (Postgres) else the local SQLite master DB. New
ingestions can't re-add these (blocked in the resolver / Industry ingestor / seeds).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from config.enums import EXCLUDED_PROSPECT_TYPES
from integration.competitors import excluded_domains
from master_db.models import (
    Company,
    CompanyAlias,
    CompanyRollup,
    CompanySource,
    DecisionMaker,
    DemandSignal,
    Job,
    LeadScore,
    Opportunity,
    ResolutionReviewQueue,
)

# Every table that references a company by domain (delete these before the company).
_DEPENDENTS = [
    (DecisionMaker, DecisionMaker.company_domain),
    (Job, Job.company_domain),
    (DemandSignal, DemandSignal.company_domain),
    (CompanyRollup, CompanyRollup.company_domain),
    (Opportunity, Opportunity.company_domain),
    (LeadScore, LeadScore.company_domain),
    (CompanySource, CompanySource.company_domain),
    (CompanyAlias, CompanyAlias.company_domain),
]


def collect_targets(session: Session) -> list[str]:
    """Domains of SERVICE_PROVIDER companies + any known competitor domain present."""
    conds = [Company.prospect_type.in_(EXCLUDED_PROSPECT_TYPES)]
    excl = list(excluded_domains())
    if excl:
        conds.append(Company.company_domain.in_(excl))
    return [d for (d,) in session.execute(select(Company.company_domain).where(or_(*conds))).all()]


def purge(session: Session, *, apply: bool = False) -> dict:
    """Report (and optionally delete) competitor companies + dependents.

    Returns ``{"domains": [...], "dependents": {table: n}, "review_queue": n}``.
    """
    domains = collect_targets(session)
    report: dict = {"domains": domains, "dependents": {}, "review_queue": 0}
    if not domains:
        return report

    for model, col in _DEPENDENTS:
        report["dependents"][model.__tablename__] = (
            session.scalar(select(func.count()).select_from(model).where(col.in_(domains))) or 0
        )
    rq_filter = or_(
        ResolutionReviewQueue.suggested_domain.in_(domains),
        ResolutionReviewQueue.resolved_domain.in_(domains),
    )
    report["review_queue"] = (
        session.scalar(select(func.count()).select_from(ResolutionReviewQueue).where(rq_filter)) or 0
    )

    if apply:
        for model, col in _DEPENDENTS:
            session.execute(delete(model).where(col.in_(domains)))
        session.execute(delete(ResolutionReviewQueue).where(rq_filter))
        session.execute(delete(Company).where(Company.company_domain.in_(domains)))
        session.commit()
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Purge competitor service-provider companies.")
    ap.add_argument("--apply", action="store_true", help="actually delete (default: dry run)")
    args = ap.parse_args()

    from backend.config import get_settings
    from backend.database import Database

    db = Database(get_settings())
    try:
        with db.sessionmaker() as session:
            report = purge(session, apply=args.apply)
            domains = report["domains"]
            print(f"Target competitor companies: {len(domains)}")
            if not domains:
                print("Nothing to purge.")
                return
            for table, n in report["dependents"].items():
                print(f"  {n:>5}  {table}")
            print(f"  {report['review_queue']:>5}  resolution_review_queue")
            print(f"  {len(domains):>5}  companies")
            for d in sorted(domains):
                print(f"      - {d}")
            print("\n" + ("Purged." if args.apply else "Dry run — re-run with --apply to delete."))
    finally:
        db.dispose()


if __name__ == "__main__":
    main()
