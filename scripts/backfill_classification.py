"""Backfill UNKNOWN company classification from already-ingested engine rows.

Industry Discovery owns `companies.company_tier` / `prospect_type` /
`compliance_flag`, but companies that entered the universe via the Blog / Career /
LinkedIn engines (resolver stubs) never got a tier. Their *opportunity* rows,
however, already carry `company_tier` / `prospect_type` / `compliance_flag` (the
Blog Crawler emits them). This propagates that existing, on-disk classification up
to the company record — **only filling UNKNOWN/blank fields, never overwriting a
known Industry Discovery value**. No re-crawl; idempotent.

    python scripts/backfill_classification.py            # dry-run (default)
    python scripts/backfill_classification.py --apply     # write changes
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from master_db.local import make_session_factory
from master_db.models import Company, Opportunity

_FIELDS = ("company_tier", "prospect_type", "compliance_flag")


def _blank(value: str | None) -> bool:
    return (value or "").strip().upper() in ("", "UNKNOWN")


def backfill(session: Session, apply: bool = False) -> list[tuple[str, dict]]:
    """Fill blank/UNKNOWN classification on each company from its opportunity rows.

    Returns a list of ``(company_domain, {field: value})`` proposed changes.
    """
    changes: list[tuple[str, dict]] = []
    for company in session.scalars(select(Company)).all():
        if not any(_blank(getattr(company, f)) for f in _FIELDS):
            continue
        opps = session.scalars(
            select(Opportunity).where(Opportunity.company_domain == company.company_domain)
        ).all()
        if not opps:
            continue
        patch: dict[str, str] = {}
        for field in _FIELDS:
            if not _blank(getattr(company, field)):
                continue  # never overwrite a known value
            votes = [getattr(o, field) for o in opps if not _blank(getattr(o, field))]
            if votes:
                patch[field] = Counter(v.strip().upper() for v in votes).most_common(1)[0][0]
        if patch:
            changes.append((company.company_domain, patch))
            if apply:
                for field, value in patch.items():
                    setattr(company, field, value)
    if apply:
        session.commit()
    return changes


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    apply = "--apply" in argv
    Session = make_session_factory("master_local.db")
    with Session() as s:
        changes = backfill(s, apply=apply)
    verb = "Filled" if apply else "Would fill"
    print(f"{verb} classification for {len(changes)} companies "
          f"({'applied' if apply else 'dry-run — pass --apply to write'}).")
    for domain, patch in changes[:25]:
        print(f"  {domain:<28} {patch}")
    if not apply and changes:
        print("\nRe-run with --apply, then `python -m lead_scoring.run` to re-score.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
