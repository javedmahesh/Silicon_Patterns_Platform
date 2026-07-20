"""New Semiconductor Project Intelligence — precise, content-driven project-event
extraction that layers on the existing News Collection Engine (no parallel pipeline).

Turns a news/RSS/Google-Alerts article into structured *project* events (a new chip
program, a tapeout, a design win, a design/R&D center, a new/expanding fab, an
OSAT/ATMP or capacity/facility expansion) — but only when the article carries
evidence of a CONCRETE, company-level project. Generic market commentary
("the semiconductor market is expanding", "AI chips are expected to grow",
"India could become a design hub") is rejected: the patterns require a concrete
action on a concrete project object, and a speculation/opinion guard drops
"could / expected to / believes / aims to eventually …" framings.

Pure functions, no DB, no network — fully unit-testable. Reuses
``leadership_signals.priority.extract_geography`` (India-aware, article-evidence-only)
for geography so there is one geography extractor across the platform.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from leadership_signals.priority import extract_geography, is_india_relevant

# ---------------------------------------------------------------- taxonomy
PROJECT_EVENT_TYPES: tuple[str, ...] = (
    "NEW_CHIP_PROGRAM", "NEW_ASIC_SOC", "TAPEOUT", "DESIGN_WIN", "DESIGN_CENTER",
    "RND_CENTER", "FAB_NEW", "FAB_EXPANSION", "OSAT_ATMP", "CAPACITY_EXPANSION",
    "FACILITY_EXPANSION",
)

# Decision-maker role families relevant to each project type (§8) — used to guide
# LATER, manual contact discovery. Never triggers Apify/DM Intelligence itself.
PROJECT_ROLE_FAMILIES: dict[str, tuple[str, ...]] = {
    "NEW_CHIP_PROGRAM": ("CTO", "VP Engineering", "VP Silicon", "Head of ASIC/SoC", "VLSI Leadership"),
    "NEW_ASIC_SOC": ("CTO", "VP Engineering", "VP Silicon", "Head of ASIC/SoC", "VLSI Leadership"),
    "TAPEOUT": ("CTO", "VP Engineering", "VP Silicon", "Head of ASIC/SoC", "VLSI Leadership"),
    "DESIGN_WIN": ("CTO", "VP Engineering", "VP Silicon", "Head of ASIC/SoC"),
    "DESIGN_CENTER": ("Engineering Leadership", "R&D Leadership", "Site Leadership", "Procurement/Sourcing"),
    "RND_CENTER": ("Engineering Leadership", "R&D Leadership", "Site Leadership", "Procurement/Sourcing"),
    "FAB_NEW": ("Manufacturing Leadership", "Operations", "Packaging/Test", "Procurement/Sourcing"),
    "FAB_EXPANSION": ("Manufacturing Leadership", "Operations", "Packaging/Test", "Procurement/Sourcing"),
    "OSAT_ATMP": ("Manufacturing Leadership", "Operations", "Packaging/Test", "Procurement/Sourcing"),
    "CAPACITY_EXPANSION": ("Manufacturing Leadership", "Operations", "Procurement/Sourcing"),
    "FACILITY_EXPANSION": ("Manufacturing Leadership", "Operations", "Site Leadership"),
}

# Generic News-extraction types each project type is MORE PRECISE than — the generic
# one is suppressed for THIS article when the project type fires, so one real event
# yields one opportunity, not two (§12).
SUBSUMES_GENERIC: dict[str, tuple[str, ...]] = {
    "NEW_CHIP_PROGRAM": ("PRODUCT_LAUNCH",), "NEW_ASIC_SOC": ("PRODUCT_LAUNCH",),
    "TAPEOUT": ("PRODUCT_LAUNCH",), "DESIGN_WIN": ("CONTRACT_WIN",),
    "DESIGN_CENTER": ("EXPANSION",), "RND_CENTER": ("EXPANSION",),
    "FAB_NEW": ("EXPANSION",), "FAB_EXPANSION": ("EXPANSION",),
    "OSAT_ATMP": ("EXPANSION",), "CAPACITY_EXPANSION": ("EXPANSION",),
    "FACILITY_EXPANSION": ("EXPANSION",),
}

# High buying-intent project types — they directly imply demand for design /
# verification / ASIC-SoC / IP / EDA / packaging / manufacturing / specialist
# engineering services, so they are HIGH regardless of company size (§7).
_HIGH_INTENT_TYPES = frozenset({
    "NEW_CHIP_PROGRAM", "NEW_ASIC_SOC", "TAPEOUT", "DESIGN_WIN",
    "DESIGN_CENTER", "RND_CENTER", "FAB_NEW", "OSAT_ATMP",
})
_STARTUP_TIERS = frozenset({"STARTUP", "SCALEUP"})

# ---------------------------------------------------------------- precision guards
# Speculative / opinion framing → NOT a concrete project. Deliberately excludes
# announced-intent verbs ("plans to build", "to open", "is investing to expand"),
# which ARE real projects.
_SPECULATION = re.compile(
    r"\b(could|might|may\s+(?:become|be|see|reach)|would\s+(?:become|be)|"
    r"expected\s+to|is\s+expected|are\s+expected|predict|forecast|projected\s+to|"
    r"potential(?:ly)?|likely\s+to|hopes?\s+to|believe|anticipat|"
    r"aims?\s+to\s+eventually|set\s+to\s+potentially|on\s+track\s+to)\b",
    re.I,
)
# Generic non-company subjects — a sentence about "the market/industry/sector/demand"
# (or a country) rather than a company doing something concrete.
_GENERIC_SUBJECT = re.compile(
    r"^\s*(the\s+)?(semiconductor\s+|chip\s+|global\s+)?"
    r"(market|industry|sector|demand|ecosystem|economy|region|country|government|world)\b",
    re.I,
)
# A plausible company actor: a capitalized token / acronym that isn't a sentence-start
# stopword or a geography. Cheap proxy — the engine still resolves the real company.
_PROPER = re.compile(r"\b([A-Z][A-Za-z0-9&.\-]{1,}(?:\s+[A-Z][A-Za-z0-9&.\-]+){0,3})\b")
_NON_COMPANY = frozenset({
    "the", "a", "an", "india", "china", "taiwan", "usa", "us", "u.s.", "europe", "asia",
    "bengaluru", "bangalore", "hyderabad", "noida", "chennai", "pune", "gujarat",
    "japan", "korea", "germany", "it", "its", "this", "that", "new", "ai",
})
# Semiconductor-domain context required for otherwise-generic facility/capacity events.
_SEMI_CONTEXT = re.compile(
    r"\b(semiconductor|chip|silicon|wafer|fab|foundry|asic|soc|processor|"
    r"accelerator|ic|packaging|osat|atmp|nm\b|node)", re.I,
)

# ---------------------------------------------------------------- event patterns
# Each: (compiled pattern, event_type). Patterns require verb+object concreteness.
def _p(rx: str) -> re.Pattern:
    return re.compile(rx, re.I)


_PROJECT_PATTERNS: list[tuple[re.Pattern, str]] = [
    # design / R&D / engineering centers
    (_p(r"\b(open|opens|opened|opening|set(?:s|ting)?\s+up|establish(?:es|ed|ing)?|"
        r"launch(?:es|ed|ing)?|inaugurat\w+|build(?:s|ing)?|to\s+(?:open|set\s+up|build))\b"
        r"[^.]*?\b(design\s+cent(?:er|re)|design\s+hub|chip\s+design\s+cent(?:er|re))\b"), "DESIGN_CENTER"),
    (_p(r"\b(open|opens|opened|opening|set(?:s|ting)?\s+up|establish(?:es|ed|ing)?|"
        r"launch(?:es|ed|ing)?|inaugurat\w+|build(?:s|ing)?|to\s+(?:open|set\s+up|build))\b"
        r"[^.]*?\b(r&d\s+cent(?:er|re)|research\s+(?:and\s+development\s+)?cent(?:er|re)|"
        r"engineering\s+cent(?:er|re))\b"), "RND_CENTER"),
    # tapeout / first silicon
    (_p(r"\b(tape[- ]?out|tapes?\s+out|taped\s+out|first\s+silicon|silicon\s+back|"
        r"to\s+tape\s+out|tape\s+out\s+its)\b"), "TAPEOUT"),
    # design win
    (_p(r"\b(design\s+win|design-win|secur\w+\s+(?:a\s+)?design\s+win|win(?:s|ning)?\s+(?:a\s+)?design\s+win|"
        r"selected\s+to\s+(?:design|supply|develop)|chosen\s+to\s+(?:design|develop|supply)|"
        r"awarded\s+[^.]*?\b(?:chip|silicon|asic|soc)\b)\b"), "DESIGN_WIN"),
    # new ASIC / SoC program (more specific — checked before generic chip program)
    (_p(r"\b(develop\w*|design\w*|build\w*|creat\w*|working\s+on|tape\s+out|to\s+(?:develop|design|build))\b"
        r"[^.]*?\b(asic|soc|system[- ]on[- ]chip|custom\s+chip|custom\s+silicon)\b"), "NEW_ASIC_SOC"),
    # new chip / processor / accelerator program
    (_p(r"\b(develop\w*|design\w*|build\w*|creat\w*|working\s+on|to\s+(?:develop|design|build)|"
        r"begins?\s+(?:development|design)\s+of)\b"
        r"[^.]*?\b(new\s+)?(chip|processor|accelerator|gpu|npu|cpu|microprocessor|ai\s+chip)\b"), "NEW_CHIP_PROGRAM"),
    # OSAT / ATMP / assembly-test
    (_p(r"\b(osat|atmp|assembly\s+and\s+test|assembly,?\s+test|packaging\s+and\s+test|"
        r"outsourced\s+semiconductor\s+assembly|ate\s+facility|test\s+and\s+packaging)\b"), "OSAT_ATMP"),
    # new fab / foundry
    (_p(r"\b(build|building|construct\w*|open|opens|opened|opening|new|set(?:s|ting)?\s+up|"
        r"break(?:s|ing)?\s+ground|to\s+build|plans?\s+to\s+build)\b"
        r"[^.]*?\b((?:semiconductor|chip|wafer)\s+)?(fab|foundry|wafer\s+fab|"
        r"fabrication\s+(?:plant|facility)|gigafab|terafab)\b"), "FAB_NEW"),
    # fab expansion
    (_p(r"\b(expand\w*|boost\w*|ramp\w*|scal\w+|increas\w+|add(?:s|ing)?)\b"
        r"[^.]*?\b((?:semiconductor|chip|wafer)\s+)?(fab|foundry|fabrication)\b"
        r"|(fab|foundry)\s+expansion"), "FAB_EXPANSION"),
    # capacity expansion
    (_p(r"\b(expand\w*|increas\w+|boost\w*|ramp\w*|add(?:s|ing)?|double\w*|triple\w*)\b"
        r"[^.]*?\b(production|manufacturing|wafer|chip|packaging)?\s*capacity\b"
        r"|capacity\s+expansion"), "CAPACITY_EXPANSION"),
    # facility / plant / site expansion
    (_p(r"\b(expand\w*|new|open\w*|build\w*)\b"
        r"[^.]*?\b(manufacturing|production|semiconductor|packaging)\s+(facility|plant|site|campus)\b"
        r"|facility\s+expansion"), "FACILITY_EXPANSION"),
]

# A monetary/scale marker strengthens a project (used for confidence, not required).
_MONEY = re.compile(r"\$\s?\d[\d,.]*\s?(?:billion|million|bn|m|b)\b|\b\d+\s?(?:billion|million|bn)\b", re.I)


@dataclass
class ProjectEvent:
    event_type: str
    evidence: str = ""            # the sentence the event was extracted from (provenance)
    has_scale: bool = False       # a $ / capacity figure was present (stronger signal)
    role_families: tuple[str, ...] = field(default_factory=tuple)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def _has_company_actor(sentence: str) -> bool:
    """True if the sentence has a plausible company subject (a proper noun that isn't a
    geography/common word). Rejects market/industry/country-level commentary."""
    if _GENERIC_SUBJECT.search(sentence):
        return False
    for m in _PROPER.finditer(sentence):
        tok = m.group(1).strip()
        if tok.lower().split()[0] not in _NON_COMPANY:
            return True
    return False


def extract_project_events(title: str, body: str) -> list[ProjectEvent]:
    """Precise, evidence-gated project events from an article. Empty when the article
    is generic commentary or lacks a concrete company-level project."""
    events: dict[str, ProjectEvent] = {}   # de-dupe by type within one article
    for sentence in _sentences(f"{title}. {body}"):
        if _SPECULATION.search(sentence):
            continue                                  # speculative / opinion → not concrete
        if not _has_company_actor(sentence):
            continue                                  # market/country commentary → reject
        for pattern, etype in _PROJECT_PATTERNS:
            if not pattern.search(sentence):
                continue
            # facility/capacity are generic unless the article is clearly semiconductor.
            if etype in ("FACILITY_EXPANSION", "CAPACITY_EXPANSION") and not _SEMI_CONTEXT.search(
                    f"{title}. {sentence}"):
                continue
            if etype not in events:
                events[etype] = ProjectEvent(
                    event_type=etype, evidence=sentence[:300],
                    has_scale=bool(_MONEY.search(sentence)),
                    role_families=PROJECT_ROLE_FAMILIES.get(etype, ()),
                )
    # NEW_ASIC_SOC is a specialization of NEW_CHIP_PROGRAM — if both fired on the same
    # article, keep only the more specific one (avoid a redundant pair).
    if "NEW_ASIC_SOC" in events and "NEW_CHIP_PROGRAM" in events:
        events.pop("NEW_CHIP_PROGRAM", None)
    return list(events.values())


def project_priority(company_tier: str | None, event_type: str, geography: str | None) -> str:
    """Reusable buying-intent tier for a project event (§7). Never discards — the
    lowest tier is still collected. India relevance and startup/scaleup companies lift
    to high; the high-intent event types are high on their own; the softer expansion
    types are medium unless startup/India."""
    tier = (company_tier or "").upper()
    if tier in _STARTUP_TIERS:
        return "high"
    if is_india_relevant(geography):
        return "high"
    if event_type in _HIGH_INTENT_TYPES:
        return "high"
    if event_type in ("FAB_EXPANSION", "CAPACITY_EXPANSION", "FACILITY_EXPANSION"):
        return "medium"
    return "low"


# Geography reuses the single platform extractor (India-aware, article-evidence-only).
project_geography = extract_geography
