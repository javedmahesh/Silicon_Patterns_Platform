"""Recompute the Sales-Pitch / Engagement recommendation per company (P-task 9).

Reads each company's signals (opportunities, leadership, demand/jobs, technology,
partnerships, funding, company type, decision makers) and writes a likely business
need + Silicon Patterns offering + one-line pitch + confidence + rationale to the
`engagement_recommendations` table. Evidence-grounded, deterministic, no re-crawl.

    python scripts/recommend_engagements.py            # rebuild + summary
    python scripts/recommend_engagements.py --show 8    # also print a few example pitches
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from engagement.recommend import rebuild
from master_db.local import make_session_factory
from master_db.models import EngagementRecommendation


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    show = 0
    if "--show" in argv:
        try:
            show = int(argv[argv.index("--show") + 1])
        except (IndexError, ValueError):
            show = 5

    Session = make_session_factory("master_local.db")
    with Session() as s:
        counts = rebuild(s)
        rows = list(s.scalars(select(EngagementRecommendation).order_by(EngagementRecommendation.confidence.desc())))
        by_offering = Counter(r.offering for r in rows)
        by_conf = Counter(r.confidence_label for r in rows)
        examples = rows[:show]

    print(f"Rebuilt engagement_recommendations: {counts['total']} companies with a pitch.")
    print(f"  by confidence: {dict(by_conf.most_common())}")
    print(f"  by offering:   {dict(by_offering.most_common())}")
    for r in examples:
        print(f"\n[{r.company_domain}]  ({r.confidence_label} {r.confidence})")
        print(f"  Need:     {r.business_need}")
        print(f"  Offering: {r.offering}")
        print(f"  Pitch:    \"{r.pitch}\"")
        print(f"  Why:      {'; '.join(r.rationale[:4])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
