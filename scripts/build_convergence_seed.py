"""Engine convergence — export a Career-engine seed of companies that still lack
hiring-demand data.

The four engines historically ran over *disjoint* company sets, so almost no company
has all signals (companies with decision makers have no demand, and vice-versa) and the
lead scores stay low. This script closes that gap: it exports the master companies that
have NO demand signal yet (which includes every people-rich employer) into the Career
Scraper's seed format, so you can re-crawl demand over the SAME companies — converging
all engines on one universe and unlocking multi-signal A/B leads.

    # from Silicon_Patterns_Platform/
    python scripts/build_convergence_seed.py                 # companies missing demand
    python scripts/build_convergence_seed.py --all           # every non-stub company
    python scripts/build_convergence_seed.py --out seed.csv  # custom output path

Output columns match Career's career_companies_large.csv: Company Name, Website, Country,
Category. This script only READS the master DB and writes a CSV — it never modifies any
engine. See HOW_TO_RUN.md ("Engine convergence") for the full re-run recipe.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from master_db.models import Company, DemandSignal  # noqa: E402


def _session():
    url = os.environ.get("DATABASE_URL", "").strip()
    if url and not url.startswith("sqlite"):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        return sessionmaker(bind=create_engine(url, future=True, pool_pre_ping=True), future=True)()
    from master_db.local import make_session_factory

    db = ROOT / "master_local.db"
    if not db.exists():
        print(f"master DB not found at {db} — run the pipeline first (python -m orchestrator.cli run all).")
        raise SystemExit(2)
    return make_session_factory(db)()


def main() -> None:
    ap = argparse.ArgumentParser(description="Export a Career-engine convergence seed.")
    ap.add_argument("--out", default="convergence_career_seed.csv", help="output CSV path")
    ap.add_argument("--all", action="store_true", help="emit every non-stub company, not only those missing demand")
    args = ap.parse_args()

    with _session() as s:
        have_demand = set(s.scalars(select(DemandSignal.company_domain)))
        rows: list[tuple[str, str, str, str]] = []
        for c in s.scalars(select(Company).where(Company.is_stub.is_(False))):
            if not args.all and c.company_domain in have_demand:
                continue
            website = c.website or (f"https://{c.company_domain}" if c.company_domain else "")
            rows.append(
                (
                    c.company_name or c.company_domain,
                    website,
                    c.country or "",
                    c.industry_category or c.technology_focus or "",
                )
            )

    out = Path(args.out)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Company Name", "Website", "Country", "Category"])
        writer.writerows(sorted(set(rows)))

    print(f"wrote {len(set(rows))} companies -> {out.resolve()}")
    print("next: run the Career Scraper over this seed (see HOW_TO_RUN.md -> 'Engine convergence').")


if __name__ == "__main__":
    main()
