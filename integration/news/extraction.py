"""AI Opportunity Extraction — deterministic, evidence-grounded, multi-signal.

Reuses the platform's existing "AI" philosophy (rules-based, no external LLM — the
same approach as ai_service / engagement / lead scoring) to turn one article into
one *or several* structured opportunities.

For each detected business event it produces the rich intelligence the Opportunities
detail panel shows: executive summary, AI summary, why-this-matters, business impact,
technologies / products / people / organizations / countries / keywords, opportunity
type + subtype, confidence + per-factor breakdown, source credibility, and the AI
reasoning trail.

Everything here is a pure function of the article — no DB, no network, fully testable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from integration.news.project_intel import (
    SUBSUMES_GENERIC,
    extract_project_events,
    project_geography,
    project_priority,
)

# ---------------------------------------------------------------- vocabularies
# Event categories -> trigger phrases. One article can match several (multi-signal:
# e.g. "acquires X and expands into Y while hiring" -> ACQUISITION + EXPANSION + HIRING).
_EVENT_TRIGGERS: dict[str, tuple[str, ...]] = {
    "ACQUISITION": ("acquire", "acquisition", "acquired", "acquires", "buyout",
                    "takeover", "to buy", "merger", "merges with", "merge with"),
    "FUNDING": ("raise", "raised", "raises", "funding", "series a", "series b",
                "series c", "series d", "seed round", "venture round", "investment round",
                "valuation", "led the round", "million in funding", "billion in funding"),
    "IPO": ("ipo", "initial public offering", "goes public", "files to go public",
            "public listing", "lists on the"),
    "PRODUCT_LAUNCH": ("launch", "launches", "launched", "unveil", "unveils", "unveiled",
                       "announces the", "introduces", "new chip", "new processor",
                       "tape-out", "tapes out", "taped out", "releases", "debuts"),
    "EXPANSION": ("expand", "expands", "expansion", "new office", "new facility",
                  "new fab", "new plant", "opens", "opening", "enters the", "entering the",
                  "sets up", "new campus", "new r&d center", "new r&d centre"),
    "HIRING": ("hiring", "hires", "to hire", "expanding its team", "expanding team",
               "headcount", "recruiting", "new roles", "adding engineers", "ramping up hiring",
               "grow its team"),
    "PARTNERSHIP": ("partner", "partners", "partnership", "collaborate", "collaboration",
                    "alliance", "joint venture", "teams up", "teaming up", "signs deal",
                    "signed a deal", "strategic agreement"),
    "EXECUTIVE_HIRE": ("appoints", "appointed", "names as", "joins as", "hired as",
                       "welcomes", "new ceo", "new cto", "new cfo", "new coo",
                       "as chief", "as president", "as vice president", "as head of"),
    "LEADERSHIP_CHANGE": ("steps down", "stepping down", "resigns", "resigned", "departs",
                          "departure", "promoted to", "promotion", "succeeds", "to retire",
                          "retires", "replaced by"),
    "CONTRACT_WIN": ("wins contract", "awarded", "selected by", "design win", "secures order",
                     "wins order", "chosen to supply"),
}

# Subtype refinement (first matching trigger's category-specific label).
_SUBTYPE_HINTS: dict[str, tuple[tuple[str, str], ...]] = {
    "FUNDING": (("seed", "SEED"), ("series a", "SERIES_A"), ("series b", "SERIES_B"),
                ("series c", "SERIES_C"), ("series d", "SERIES_D"), ("billion", "MEGA_ROUND")),
    "PRODUCT_LAUNCH": (("chip", "SILICON"), ("processor", "SILICON"), ("gpu", "SILICON"),
                       ("soc", "SILICON"), ("tape", "TAPEOUT"), ("platform", "PLATFORM"),
                       ("software", "SOFTWARE"), ("ip", "IP_CORE")),
    "EXPANSION": (("fab", "MANUFACTURING"), ("plant", "MANUFACTURING"), ("r&d", "RND"),
                  ("office", "OFFICE"), ("india", "GEO"), ("europe", "GEO"), ("asia", "GEO")),
    "ACQUISITION": (("merger", "MERGER"), ("buyout", "BUYOUT")),
}

# Curated semiconductor technology vocabulary (lowercased match, canonical display).
_TECH_VOCAB: dict[str, str] = {
    "rtl": "RTL", "asic": "ASIC", "fpga": "FPGA", "soc": "SoC", "eda": "EDA",
    "risc-v": "RISC-V", "risc v": "RISC-V", "arm": "Arm", "x86": "x86", "gpu": "GPU",
    "cpu": "CPU", "npu": "NPU", "tpu": "TPU", "dsp": "DSP", "chiplet": "Chiplet",
    "hbm": "HBM", "ddr5": "DDR5", "ddr": "DDR", "pcie": "PCIe", "cxl": "CXL",
    "photonics": "Photonics", "silicon photonics": "Silicon Photonics",
    "3nm": "3nm", "5nm": "5nm", "7nm": "7nm", "2nm": "2nm", "euv": "EUV",
    "packaging": "Advanced Packaging", "verification": "Verification",
    "physical design": "Physical Design", "dft": "DFT", "sta": "STA",
    "analog": "Analog", "mixed-signal": "Mixed-Signal", "rf": "RF",
    "ai accelerator": "AI Accelerator", "machine learning": "Machine Learning",
    "automotive": "Automotive", "power management": "Power Management",
}

# Countries the industry cares about (extend freely — additive).
_COUNTRIES: tuple[str, ...] = (
    "United States", "USA", "US", "India", "China", "Taiwan", "South Korea", "Korea",
    "Japan", "Germany", "France", "United Kingdom", "UK", "Israel", "Singapore",
    "Netherlands", "Ireland", "Canada", "Vietnam", "Malaysia",
)
_COUNTRY_CANON = {c.lower(): ("United States" if c in ("USA", "US") else
                              "United Kingdom" if c == "UK" else
                              "South Korea" if c == "Korea" else c) for c in _COUNTRIES}

# Corporate suffixes that mark an organization token.
_ORG_SUFFIX = re.compile(
    r"\b([A-Z][A-Za-z0-9&.\-]+(?:\s+[A-Z][A-Za-z0-9&.\-]+){0,3}\s+"
    r"(?:Inc|Corp|Corporation|Ltd|LLC|Technologies|Semiconductor|Semiconductors|"
    r"Systems|Labs|Microelectronics|Micro|Group|Holdings))\b"
)
_PERSON = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)\b")
_MONEY = re.compile(r"\$\s?\d[\d,.]*\s?(?:billion|million|bn|m|b|k)?", re.I)

# Base opportunity score by event type (0..100) — matches the existing blog scale.
_BASE_SCORE: dict[str, int] = {
    "ACQUISITION": 82, "FUNDING": 80, "IPO": 78, "PRODUCT_LAUNCH": 70,
    "EXPANSION": 72, "HIRING": 66, "PARTNERSHIP": 68, "EXECUTIVE_HIRE": 60,
    "LEADERSHIP_CHANGE": 58, "CONTRACT_WIN": 74, "COMPANY_NEWS": 50,
    # New Semiconductor Project Intelligence (integration/news/project_intel.py) — a
    # concrete company-level project is a strong, actionable buying signal.
    "NEW_CHIP_PROGRAM": 84, "NEW_ASIC_SOC": 84, "TAPEOUT": 86, "DESIGN_WIN": 82,
    "DESIGN_CENTER": 80, "RND_CENTER": 78, "FAB_NEW": 82, "FAB_EXPANSION": 74,
    "OSAT_ATMP": 76, "CAPACITY_EXPANSION": 70, "FACILITY_EXPANSION": 68,
}

_WHY_TEMPLATES: dict[str, str] = {
    "ACQUISITION": "An acquisition reshapes the company's roadmap and engineering needs — "
                   "a strong trigger to engage the newly combined team.",
    "FUNDING": "Fresh capital typically funds headcount and new silicon programs — an "
               "early window to reach a scaling engineering org.",
    "IPO": "Going public raises scrutiny and accelerates hiring/product cadence — a "
           "high-visibility engagement moment.",
    "PRODUCT_LAUNCH": "A new product signals an active design cycle and downstream "
                      "verification/physical-design demand.",
    "EXPANSION": "Geographic or capacity expansion creates new local engineering demand — "
                 "often ahead of public job posts.",
    "HIRING": "Visible hiring is a direct demand signal for engineering services and tools.",
    "PARTNERSHIP": "A partnership opens a warm, multi-account engagement path via a shared "
                   "program.",
    "EXECUTIVE_HIRE": "A new senior leader often re-evaluates vendors and tooling in their "
                      "first quarters.",
    "LEADERSHIP_CHANGE": "Leadership turnover shifts priorities and budgets — worth tracking "
                         "for the next buying cycle.",
    "CONTRACT_WIN": "A new design win drives immediate execution capacity needs.",
    "COMPANY_NEWS": "Notable company activity worth monitoring for follow-on signals.",
    "NEW_CHIP_PROGRAM": "A new chip program means an active design cycle — a prime window for "
                        "design, verification, and IP engagement.",
    "NEW_ASIC_SOC": "A new ASIC/SoC program drives ASIC/SoC engineering, verification, and "
                    "physical-design demand.",
    "TAPEOUT": "A tapeout / first silicon signals an advanced program with immediate "
               "verification, DFT, and bring-up needs.",
    "DESIGN_WIN": "A design win commits a delivery schedule — near-term engineering-capacity demand.",
    "DESIGN_CENTER": "A new design center is a build-out of local engineering capacity — a strong "
                     "staffing and services signal, often ahead of public job posts.",
    "RND_CENTER": "A new R&D/engineering center signals investment in local design capability.",
    "FAB_NEW": "A new fab is a multi-year build with equipment, packaging/test, and engineering ramp.",
    "FAB_EXPANSION": "A fab expansion adds capacity and the engineering to support it.",
    "OSAT_ATMP": "An OSAT/ATMP project drives packaging, test, and assembly-engineering demand.",
    "CAPACITY_EXPANSION": "A capacity expansion signals rising volume and supporting engineering needs.",
    "FACILITY_EXPANSION": "A facility expansion is corporate growth worth monitoring for follow-on programs.",
}

_IMPACT_TEMPLATES: dict[str, str] = {
    "ACQUISITION": "Consolidated R&D and integration work; potential tool/flow standardization.",
    "FUNDING": "Budget unlocked for headcount, EDA tooling, and outsourced design.",
    "IPO": "Increased compliance + delivery pressure; expanded engineering investment.",
    "PRODUCT_LAUNCH": "Active tape-out / verification workload around the new product line.",
    "EXPANSION": "New-site staffing and infrastructure ramp.",
    "HIRING": "Near-term engineering capacity gap the company is actively filling.",
    "PARTNERSHIP": "Joint program execution spanning both organizations.",
    "EXECUTIVE_HIRE": "Likely tooling/vendor review under new leadership.",
    "LEADERSHIP_CHANGE": "Roadmap and budget re-prioritization.",
    "CONTRACT_WIN": "Committed delivery timeline requiring added capacity.",
    "COMPANY_NEWS": "General signal; monitor for a concrete follow-on trigger.",
    "NEW_CHIP_PROGRAM": "Active design/verification workload around the new silicon.",
    "NEW_ASIC_SOC": "ASIC/SoC design, verification, and physical-design workload.",
    "TAPEOUT": "Immediate verification/DFT/bring-up workload; program is advanced.",
    "DESIGN_WIN": "Committed program execution and delivery capacity.",
    "DESIGN_CENTER": "New-site engineering staffing and vendor/tooling selection.",
    "RND_CENTER": "New-site R&D staffing and infrastructure ramp.",
    "FAB_NEW": "Multi-year equipment, packaging/test, and engineering ramp.",
    "FAB_EXPANSION": "Added capacity with supporting engineering.",
    "OSAT_ATMP": "Packaging/test/assembly-engineering demand.",
    "CAPACITY_EXPANSION": "Rising volume and supporting engineering needs.",
    "FACILITY_EXPANSION": "Site-level growth; monitor for follow-on programs.",
}


@dataclass
class ExtractedSignal:
    """One structured opportunity extracted from an article."""

    opportunity_type: str
    opportunity_subtype: str = ""
    executive_summary: str = ""
    ai_summary: str = ""
    why_this_matters: str = ""
    business_impact: str = ""
    ai_reasoning: str = ""
    technologies: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    people: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    confidence: int = 0
    confidence_breakdown: dict[str, int] = field(default_factory=dict)
    source_credibility: int = 0
    opportunity_score: int = 0
    effective_opportunity_score: int = 0
    lead_readiness_score: int = 0
    # New Project Intelligence extras (blank for non-project signals): article-derived
    # location, buying-intent tier, whether this is a structured project event, and the
    # DM role families a later manual contact-discovery pass should target.
    geography: str = ""
    priority_tier: str = ""
    is_project: bool = False
    role_families: list[str] = field(default_factory=list)

    def salient_entities(self) -> list[str]:
        """Entities used for the dedup fingerprint (order-independent identity of the event)."""
        return (self.technologies + self.products + self.people + self.organizations)[:6]


def _find_matches(text_lc: str, triggers: tuple[str, ...]) -> list[str]:
    return [t for t in triggers if t in text_lc]


def _extract_technologies(text: str) -> list[str]:
    tl = text.lower()
    hits: list[str] = []
    for needle, canon in _TECH_VOCAB.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", tl) and canon not in hits:
            hits.append(canon)
    return hits


def _extract_countries(text: str) -> list[str]:
    out: list[str] = []
    for c in _COUNTRIES:
        if re.search(rf"\b{re.escape(c)}\b", text) and _COUNTRY_CANON[c.lower()] not in out:
            out.append(_COUNTRY_CANON[c.lower()])
    return out


_ORG_TOKENS = {"inc", "corp", "corporation", "ltd", "llc", "technologies", "semiconductor",
               "semiconductors", "systems", "labs", "microelectronics", "micro", "group",
               "holdings", "the", "a"}


def _extract_people(text: str, company_name: str, orgs: list[str]) -> list[str]:
    org_lc = [o.lower() for o in orgs] + ([company_name.lower()] if company_name else [])
    out: list[str] = []
    for m in _PERSON.finditer(text):
        name = m.group(1).strip()
        low = name.lower()
        if any(low in o or o in low for o in org_lc):        # part of an org name
            continue
        if any(tok in _ORG_TOKENS for tok in low.split()):   # carries a corporate token
            continue
        if name not in out:
            out.append(name)
    return out[:6]


# Words that end a headline's leading company phrase (verbs/connectors), so
# "NVIDIA Launches New GPU" -> "NVIDIA" and "Acme Semiconductor Raises $50M" ->
# "Acme Semiconductor" even in Title Case (every word capitalized).
_COMPANY_STOPWORDS = frozenset({
    "raises", "raise", "raised", "launches", "launch", "launched", "acquires", "acquire",
    "acquired", "unveils", "unveil", "unveiled", "announces", "announce", "announced",
    "expands", "expand", "expanded", "hires", "hire", "hiring", "partners", "partner",
    "names", "name", "named", "appoints", "appoint", "appointed", "completes", "complete",
    "completed", "wins", "win", "won", "opens", "open", "opened", "invests", "invest",
    "plans", "plan", "reports", "report", "secures", "secure", "secured", "taps", "adds",
    "add", "sets", "buys", "buy", "closes", "close", "gets", "joins", "join", "teams",
    "debuts", "debut", "files", "file", "lists", "list", "to", "and", "for", "with", "in",
    "on", "at", "the", "a", "is", "are", "will", "has", "have", "amid", "after", "as",
})
_CONNECTORS = frozenset({"&", "and", "of"})
_PROPER = re.compile(r"^(?:[A-Z][\w.&+-]*|[A-Z]{2,})$")


def extract_primary_company(title: str, orgs: list[str]) -> str:
    """Best-guess company for a free-text news article (RSS headline has no company
    field). Prefers a suffixed organization; else the leading proper-noun phrase of
    the headline, bounded by the first verb/connector and capped at 4 tokens."""
    if orgs:
        return orgs[0]
    tokens = (title or "").strip().split()
    out: list[str] = []
    for tok in tokens[:6]:
        low = tok.strip(",:;").lower()
        if low in _COMPANY_STOPWORDS:
            break
        if low in _CONNECTORS and out:
            out.append(tok)
            continue
        if _PROPER.match(tok.strip(",:;")):
            out.append(tok.strip(",:;"))
            if len(out) >= 4:
                break
        else:
            break
    # drop a dangling connector ("Acme &" -> "Acme")
    while out and out[-1].lower() in _CONNECTORS:
        out.pop()
    return " ".join(out).strip()


def _extract_orgs(text: str, company_name: str) -> list[str]:
    out: list[str] = []
    if company_name:
        out.append(company_name)
    for m in _ORG_SUFFIX.finditer(text):
        org = m.group(1).strip()
        if org not in out:
            out.append(org)
    return out[:6]


def _credibility(source_type: str, source_tier: int, publisher: str) -> int:
    """Source credibility 0..100 from tier/type/publisher (higher = more trusted)."""
    if source_tier and source_tier > 0:
        base = max(20, 100 - (source_tier - 1) * 20)   # tier1=100, tier2=80, tier3=60...
    else:
        base = {"rss": 70, "google_alerts": 55, "file": 65, "company_news": 60}.get(
            (source_type or "").lower(), 55)
    known = ("reuters", "bloomberg", "ee times", "semiengineering", "anandtech",
             "the verge", "techcrunch", "wsj", "financial times")
    if publisher and any(k in publisher.lower() for k in known):
        base = min(100, base + 10)
    return int(base)


def _confidence(event_type: str, in_title: bool, entity_count: int, has_money: bool,
                source_cred: int, body_len: int) -> tuple[int, dict[str, int]]:
    breakdown = {
        "title_signal": 90 if in_title else 45,
        "entity_richness": min(100, 30 + entity_count * 14),
        "specificity": (70 if has_money else 40) + (20 if body_len > 240 else 0),
        "source_credibility": source_cred,
    }
    breakdown["specificity"] = min(100, breakdown["specificity"])
    # Weighted blend — title + credibility matter most.
    overall = round(
        0.32 * breakdown["title_signal"]
        + 0.22 * breakdown["entity_richness"]
        + 0.20 * breakdown["specificity"]
        + 0.26 * breakdown["source_credibility"]
    )
    return int(overall), breakdown


def _summaries(event_type: str, company_name: str, title: str, body: str,
               techs: list[str], money: str) -> tuple[str, str]:
    company = company_name or "The company"
    label = event_type.replace("_", " ").title()
    exec_summary = f"{company}: {label}." + (f" {title.strip()}" if title else "")
    bits = [f"{company} — {label.lower()} detected"]
    if money:
        bits.append(f"({money.strip()})")
    if techs:
        bits.append("involving " + ", ".join(techs[:3]))
    first_sentence = re.split(r"(?<=[.!?])\s", body.strip())[0] if body.strip() else ""
    ai_summary = " ".join(bits).strip() + (f". {first_sentence}" if first_sentence else ".")
    return exec_summary.strip(), ai_summary.strip()


def extract_opportunities(article: dict[str, Any]) -> list[ExtractedSignal]:
    """Extract 1..N structured opportunities from one normalized *article*.

    Multi-signal: every distinct business event found in the text becomes its own
    ``ExtractedSignal`` (all linked back to this article by the engine). If the
    article carries a pre-typed feed row (``_feed_row`` with ``opportunity_type``),
    that type is always included so file-fed rows never lose their classification.
    """
    title = (article.get("title") or "").strip()
    body = (article.get("body") or "").strip()
    company_name = (article.get("company_name") or "").strip()
    source_type = (article.get("source_type") or article.get("adapter_type") or "").strip()
    publisher = (article.get("publisher") or "").strip()
    feed_row = article.get("_feed_row") or {}
    try:
        source_tier = int(feed_row.get("source_tier") or 0)
    except (TypeError, ValueError):
        source_tier = 0

    full = f"{title}. {body}".strip()
    text_lc = full.lower()
    title_lc = title.lower()

    # 1) Which event types fired? (multi-signal)
    fired: list[str] = []
    for event_type, triggers in _EVENT_TRIGGERS.items():
        if _find_matches(text_lc, triggers):
            fired.append(event_type)
    # Honor a pre-classified feed type even if no trigger matched the free text.
    # Normalize display labels to canonical form ("Product Launch" -> "PRODUCT_LAUNCH")
    # so it dedups against a trigger-detected canonical type instead of doubling up.
    feed_type = re.sub(r"[\s\-]+", "_", (feed_row.get("opportunity_type")
                                         or feed_row.get("news_type") or "").strip().upper())
    if feed_type and feed_type not in fired:
        fired.insert(0, feed_type)

    # 1b) Structured New Project Intelligence (precise, evidence-gated). A project event
    # is MORE precise than the generic type it subsumes, so we suppress the generic one
    # for this article (one real event -> one opportunity, not two — §12). Project types
    # lead so they rank first.
    project_events = extract_project_events(title, body)
    project_by_type = {e.event_type: e for e in project_events}
    subsumed: set[str] = set()
    for etype in project_by_type:
        subsumed.update(SUBSUMES_GENERIC.get(etype, ()))
    fired = [f for f in fired if f not in subsumed and f not in project_by_type]
    fired = list(project_by_type.keys()) + fired
    if not fired:
        fired = ["COMPANY_NEWS"]

    geography = project_geography(full)

    # 2) Entities (shared across every signal from this article).
    techs = _extract_technologies(full)
    if feed_row.get("technology_mentioned"):
        seen_lc = {t.lower() for t in techs}
        for t in re.split(r"[;,]", str(feed_row["technology_mentioned"])):
            t = t.strip()
            if t and t.lower() not in seen_lc:   # case-insensitive: keep canonical casing
                techs.append(t)
                seen_lc.add(t.lower())
    countries = _extract_countries(full)
    if feed_row.get("country"):
        cc = str(feed_row["country"]).strip()
        if cc and cc not in countries:
            countries.append(cc)
    orgs = _extract_orgs(full, company_name)
    if feed_row.get("partner_company"):
        pc = str(feed_row["partner_company"]).strip()
        if pc and pc not in orgs:
            orgs.append(pc)
    people = _extract_people(full, company_name, orgs)
    if feed_row.get("person_name"):
        pn = str(feed_row["person_name"]).strip()
        if pn and pn not in people:
            people.insert(0, pn)
    products = []
    if feed_row.get("product_mentioned"):
        products = [p.strip() for p in re.split(r"[;,]", str(feed_row["product_mentioned"])) if p.strip()]
    money_m = _MONEY.search(full)
    money = money_m.group(0) if money_m else ""
    source_cred = _credibility(source_type, source_tier, publisher)

    signals: list[ExtractedSignal] = []
    for event_type in fired:
        project = project_by_type.get(event_type)
        # A structured project event is concrete by construction — treat it as a
        # title-strength signal; a scale figure ($/capacity) strengthens it further.
        in_title = bool(project) or bool(_find_matches(title_lc, _EVENT_TRIGGERS.get(event_type, ())))
        entity_count = len(techs) + len(products) + len(people) + len(orgs)
        has_scale = bool(money) or bool(project and project.has_scale)
        confidence, breakdown = _confidence(
            event_type, in_title, entity_count, has_scale, source_cred, len(body))

        # keywords: this event's fired triggers + top techs.
        kw = list(dict.fromkeys(
            _find_matches(text_lc, _EVENT_TRIGGERS.get(event_type, ()))[:3] + techs[:4]))

        exec_s, ai_s = _summaries(event_type, company_name, title, body, techs, money)
        subtype = _subtype_for(event_type, text_lc)
        base = _BASE_SCORE.get(event_type, 50)
        # confidence scales the effective score a little (evidence-weighted).
        effective = int(base * (0.6 + 0.4 * confidence / 100))
        reasoning = _reasoning(event_type, in_title, entity_count, has_scale, source_cred, subtype)
        if project:   # provenance: the exact sentence the project event came from
            reasoning += f" Project evidence: \"{project.evidence}\"."

        signals.append(ExtractedSignal(
            opportunity_type=event_type,
            opportunity_subtype=subtype,
            executive_summary=exec_s,
            ai_summary=ai_s,
            why_this_matters=_WHY_TEMPLATES.get(event_type, _WHY_TEMPLATES["COMPANY_NEWS"]),
            business_impact=_IMPACT_TEMPLATES.get(event_type, _IMPACT_TEMPLATES["COMPANY_NEWS"]),
            ai_reasoning=reasoning,
            technologies=techs, products=products, people=people, organizations=orgs,
            countries=countries, keywords=kw,
            confidence=confidence, confidence_breakdown=breakdown, source_credibility=source_cred,
            opportunity_score=base, effective_opportunity_score=effective,
            lead_readiness_score=int((base + confidence) / 2),
            geography=geography,
            is_project=bool(project),
            # provisional priority (company tier unknown here); the engine recomputes
            # with the resolved company's tier. Non-project signals carry no tier.
            priority_tier=(project_priority(None, event_type, geography) if project else ""),
            role_families=list(project.role_families) if project else [],
        ))
    return signals


def _subtype_for(event_type: str, text_lc: str) -> str:
    for needle, label in _SUBTYPE_HINTS.get(event_type, ()):
        if needle in text_lc:
            return label
    return ""


def _reasoning(event_type: str, in_title: bool, entity_count: int, has_money: bool,
               source_cred: int, subtype: str) -> str:
    parts = [f"Classified as {event_type}"]
    if subtype:
        parts.append(f"/{subtype}")
    parts.append(
        f" — trigger phrase found in {'title' if in_title else 'body'}; "
        f"{entity_count} entities extracted; "
        f"{'monetary figure present; ' if has_money else ''}"
        f"source credibility {source_cred}/100."
    )
    return "".join(parts)


def demo() -> None:
    """Self-check: multi-signal extraction + rich fields. Run: python -m integration.news.extraction"""
    article = {
        "title": "Acme Semiconductor acquires RivalChip and expands its India R&D team",
        "body": ("Acme Semiconductor Inc announced it will acquire RivalChip for $1.2 billion "
                 "and open a new R&D center in Bengaluru, India, hiring 200 RTL and verification "
                 "engineers. CEO Jane Doe said the RISC-V roadmap accelerates."),
        "company_name": "Acme Semiconductor",
        "source_type": "rss", "publisher": "EE Times",
    }
    sigs = extract_opportunities(article)
    types = {s.opportunity_type for s in sigs}
    assert "ACQUISITION" in types, types
    # "open a new R&D center" is now the precise RND_CENTER project event (supersedes the
    # generic EXPANSION), and it carries geography + a high priority (India, startup-ish).
    assert "RND_CENTER" in types and "EXPANSION" not in types, types
    assert "HIRING" in types, types            # multi-signal: 3+ events from one article
    rnd = next(s for s in sigs if s.opportunity_type == "RND_CENTER")
    assert rnd.is_project and rnd.geography == "Bengaluru, India" and rnd.priority_tier == "high", rnd
    assert rnd.role_families, rnd.role_families
    acq = next(s for s in sigs if s.opportunity_type == "ACQUISITION")
    assert "RISC-V" in acq.technologies, acq.technologies
    assert "India" in acq.countries, acq.countries
    assert acq.confidence > 0 and acq.confidence_breakdown, acq.confidence_breakdown
    assert acq.executive_summary and acq.why_this_matters and acq.ai_reasoning
    assert "Jane Doe" in acq.people, acq.people
    print(f"OK — {len(sigs)} signals: {sorted(types)}; rnd geo={rnd.geography} "
          f"priority={rnd.priority_tier} roles={rnd.role_families}")


if __name__ == "__main__":  # pragma: no cover
    demo()
