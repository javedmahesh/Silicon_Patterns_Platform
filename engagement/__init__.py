"""Sales-pitch / engagement recommendation engine (P-task 9).

Turns a company's own already-ingested intelligence — opportunities, leadership
signals, hiring/demand (per-discipline job mix), technology, partnerships,
funding, company type, decision makers — into:

  * a likely **business need**,
  * the matching **Silicon Patterns offering**,
  * a concise **one-line sales pitch**,

plus a **confidence** score and a **rationale** listing the evidence used. It is
evidence-grounded and deterministic (no LLM, no marketing boilerplate): every
pitch is backed by specific signals, and a company with no signals gets none.
Recomputed every refresh by the `engagement` orchestrator stage.
"""
from engagement.recommend import MODEL_VERSION, OFFERINGS, rebuild, recommend_all, recommend_for_company

__all__ = ["MODEL_VERSION", "OFFERINGS", "rebuild", "recommend_all", "recommend_for_company"]
