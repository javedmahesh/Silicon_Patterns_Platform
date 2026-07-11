"""Person-level leadership-movement intelligence (P-task 8).

Derives director-level-and-above movement signals (promotion, role change,
executive hire/departure, board appointment, founder change, reshuffle) and
stores them in the ``leadership_signals`` table. Two feeders:

* ``derive.from_decision_makers`` — LinkedIn career history (works on existing
  data; the person-level backbone).
* ``derive.from_blog_events``     — Leadership Change opportunities (populates
  once the Blog Crawler crawls them).

This is a *platform derivation* over people-domain data — not a new engine, and
it never touches the Blog Crawler or the binary ``decision_makers.seniority``.
"""
from leadership_signals.seniority import classify_seniority, rank

__all__ = ["classify_seniority", "rank"]
