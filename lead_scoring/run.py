r"""Run lead scoring over the master DB. From the Silicon_Patterns_Platform folder:

    python -m lead_scoring.run                 # scores master_local.db
    python -m lead_scoring.run path\to\other.db

Reads the formula from ``config/lead_scoring.json`` (tunable). Prints a summary.
"""
from __future__ import annotations

import sys
from pathlib import Path

from lead_scoring.config import ScoringConfig
from lead_scoring.service import score_all
from master_db.local import make_session_factory

DEFAULT_DB = Path(__file__).resolve().parent.parent / "master_local.db"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    db_path = Path(argv[0]) if argv else DEFAULT_DB
    if not db_path.exists():
        print(f"ERROR: master DB not found at {db_path}. Run the backfill first.")
        return 2

    cfg = ScoringConfig.load()
    Session = make_session_factory(db_path)
    with Session() as s:
        summary = score_all(s, cfg)

    print(f"Scored {summary.scored} companies with model '{cfg.model_version}'.")
    print(f"Grade distribution: {summary.grade_counts}")
    print(f"Companies with all 4 inputs: {summary.full_data_companies}")
    print("Top 10:")
    for domain, name, score, grade, _ in summary.top[:10]:
        print(f"  {grade:<2} {score:>5.1f}  {name or domain}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
