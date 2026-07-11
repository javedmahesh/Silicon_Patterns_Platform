"""Recompute person-level leadership-movement signals (P-task 8).

Derives director+ movement (promotions, role changes, executive hires/departures,
board appointments, founder changes, reshuffles) from each decision maker's own
LinkedIn career history, plus any `Leadership Change` blog opportunities, and
writes them to the `leadership_signals` table. Idempotent (per-source rebuild),
no re-crawl.

    python scripts/derive_leadership_signals.py                 # rebuild + summary
    python scripts/derive_leadership_signals.py --window 36     # widen the recency window
    python scripts/derive_leadership_signals.py --no-blog       # LinkedIn history only
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from leadership_signals.derive import DEFAULT_WINDOW_MONTHS, rebuild
from master_db.local import make_session_factory
from master_db.models import LeadershipSignal


def _arg_int(argv: list[str], flag: str, default: int) -> int:
    if flag in argv:
        try:
            return int(argv[argv.index(flag) + 1])
        except (IndexError, ValueError):
            pass
    return default


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    window = _arg_int(argv, "--window", DEFAULT_WINDOW_MONTHS)
    include_blog = "--no-blog" not in argv

    Session = make_session_factory("master_local.db")
    with Session() as s:
        counts = rebuild(s, window_months=window, include_blog=include_blog)
        rows = list(s.scalars(select(LeadershipSignal)))
        by_type = Counter(r.movement_type for r in rows)
        by_band = Counter(r.seniority_band for r in rows)
        by_conf = Counter(r.confidence for r in rows)
        resolved = sum(1 for r in rows if r.company_domain)

    print(f"Rebuilt leadership_signals (window={window}mo, blog={'on' if include_blog else 'off'}): "
          f"{counts['total']} signals "
          f"({counts['linkedin_history']} linkedin_history, {counts['blog_event']} blog_event).")
    print(f"  company-resolved: {resolved}/{counts['total']}")
    print(f"  by movement_type: {dict(by_type.most_common())}")
    print(f"  by seniority_band: {dict(by_band.most_common())}")
    print(f"  by confidence:    {dict(by_conf.most_common())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
