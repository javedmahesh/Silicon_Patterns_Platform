"""The director+ seniority gate for leadership signals.

``classify_seniority(title)`` maps a free-text job title to a seniority *band*
and a role *function*, or ``None`` when the title is below director level (i.e.
manager-level or an individual contributor). This is the single chokepoint that
enforces the task's scope:

    IN  → Director, Senior Director, VP/SVP/EVP, C-level, President, Founder /
          Co-Founder, Managing Director, Board roles, and Heads of
          Engineering / Product / Technology / Business Development.
    OUT → Manager, Senior Manager, Lead, Principal, Staff, Associate/Assistant
          Director, and all individual-contributor titles.

It is intentionally separate from ``decision_makers.seniority`` (a coarse binary
flag that even counts "manager" as senior) — that field is left untouched.
"""
from __future__ import annotations

import re

# Ordered low → high so ``rank`` can compare two roles for a promotion.
_RANK: dict[str, int] = {
    "director": 1,
    "head_of": 2,
    "senior_director": 2,
    "vp": 3,
    "svp": 4,
    "evp": 5,
    "managing_director": 5,
    "president": 6,
    "c_level": 6,
    "founder": 6,
}

# Heads we track (the task names exactly these four functions).
_TRACKED_HEAD_FUNCTIONS = ("engineering", "product", "technology", "business_development")

_C_ABBREVS = r"\b(ceo|cto|cfo|coo|cmo|cio|ciso|cpo|cro|cdo|cso|cxo|cao|cco|cto/founder)\b"
_BOARD = re.compile(
    r"\b(board of directors|board member|board observer|advisory board|"
    r"board of advisors|independent director|non[ -]?executive director)\b"
)


def _norm(title: str | None) -> str:
    """Lower-case, punctuation → spaces, collapsed, and space-padded so word
    patterns can match on boundaries (``co-founder`` → `` co founder ``)."""
    flat = re.sub(r"[^a-z0-9 ]+", " ", (title or "").lower())
    return f" {re.sub(r'[ ]+', ' ', flat).strip()} "


def _detect_function(t: str) -> str:
    if re.search(r"\b(engineering|engineer|silicon|hardware|vlsi|asic|soc|rtl|chip|r d|research)\b", t):
        return "engineering"
    if re.search(r"\bproduct\b", t):
        return "product"
    if re.search(r"\b(technology|technical|cto)\b", t):
        return "technology"
    if re.search(r"\b(business development|biz dev|sales|revenue|commercial|go to market|gtm|marketing|growth)\b", t):
        return "business_development"
    if re.search(r"\b(operations|operating|coo)\b", t):
        return "operations"
    if re.search(r"\b(finance|financial|cfo|accounting)\b", t):
        return "finance"
    return "general"


def classify_seniority(title: str | None) -> tuple[str, str] | None:
    """Return ``(seniority_band, role_function)`` for director+ titles, else ``None``.

    Matched most-senior / most-specific first so ordering edge cases resolve
    correctly ("vice president" is a VP not a President, "managing/senior
    director" outrank a plain "director", "evp/svp" outrank "vp").
    """
    t = _norm(title)
    if not t.strip():
        return None
    func = _detect_function(t)

    # C-level: an actual "Chief … Officer" or a C-abbrev (not "Chief Architect").
    if re.search(r"\bchief\b.*\bofficer\b", t) or re.search(_C_ABBREVS, t):
        return ("c_level", func)
    # President (but "Vice President" is a VP, handled below).
    if re.search(r"\bpresident\b", t) and not re.search(r"\bvice president\b", t):
        return ("president", func)
    # Founder / Co-Founder (not "founding engineer").
    if re.search(r"\b(co founder|cofounder|founder)\b", t):
        return ("founder", func)
    # Managing Director (before the plain "director" check).
    if re.search(r"\bmanaging director\b", t):
        return ("managing_director", func)
    # EVP / SVP (before VP).
    if re.search(r"\bevp\b", t) or re.search(r"\bexecutive vice president\b", t):
        return ("evp", func)
    if re.search(r"\bsvp\b", t) or re.search(r"\bsenior vice president\b", t):
        return ("svp", func)
    # VP / Vice President (excluding AVP = associate VP).
    if (re.search(r"\bvp\b", t) or re.search(r"\bvice president\b", t)) and not re.search(r"\bavp\b", t):
        return ("vp", func)
    # Senior Director (before the plain "director" check).
    if re.search(r"\b(senior|sr) director\b", t):
        return ("senior_director", func)
    # Board roles map to director-level with a 'board' function.
    if _BOARD.search(t):
        return ("director", "board")
    # Plain Director (excluding associate/assistant/deputy director — below scope).
    if re.search(r"\bdirector\b", t) and not re.search(r"\b(associate|assistant|deputy) director\b", t):
        return ("director", func)
    # Heads of Engineering / Product / Technology / Business Development only.
    if re.search(r"\bhead of\b", t) and func in _TRACKED_HEAD_FUNCTIONS:
        return ("head_of", func)

    # Everything else — manager-level and ICs — is out of scope.
    return None


def rank(band: str) -> int:
    """Numeric ladder position; higher = more senior. Unknown → 0."""
    return _RANK.get(band, 0)
