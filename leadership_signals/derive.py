"""Derive person-level leadership-movement signals.

Two feeders write ``leadership_signals`` rows:

* :func:`from_decision_makers` — Phase 1, the backbone. Walks each decision
  maker's own ``profile_data`` career history (``positions``/``experience`` with
  ``position`` titles + ``startDate``/``endDate``), gates to director+ via
  :func:`leadership_signals.seniority.classify_seniority`, and emits recent
  movement (joins, departures, promotions, role changes, founder/board changes).
* :func:`from_blog_events` — Phase 2. Best-effort extraction of person + role +
  movement from ``Leadership Change`` opportunities (yields data once the Blog
  Crawler crawls them).

Company resolution reuses the read-only ``company_aliases`` lookup pattern from
:mod:`integration.reresolve` (``name_key`` → alias → domain); an unresolved
historical employer keeps a NULL domain, the documented LinkedIn exception.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from integration.normalizer import name_key
from leadership_signals.priority import extract_geography, priority_tier
from leadership_signals.seniority import classify_seniority, rank
from master_db.models import Company, CompanyAlias, DecisionMaker, DecisionMakerSnapshot, LeadershipSignal, Opportunity
from sync.dm_sync import PlatformDecisionMakerIndex
from sync.normalization import norm_person_name, norm_title

DEFAULT_WINDOW_MONTHS = 36   # "recent leadership movement" horizon; configurable via the driver
_RESHUFFLE_WINDOW_MONTHS = 6

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Date helpers (LinkedIn dates are {"text": "...", "year": 2024, "month": "Dec"})
# --------------------------------------------------------------------------- #
def _ym(obj) -> tuple[int, int] | None:
    if not isinstance(obj, dict):
        return None
    year = obj.get("year")
    if year:
        raw_month = str(obj.get("month", "")).strip().lower()[:3]
        try:
            return (int(year), _MONTHS.get(raw_month, 1))
        except (TypeError, ValueError):
            return None
    text = str(obj.get("text", "")).strip().lower()
    m = re.search(r"([a-z]{3})[a-z]*\s+(\d{4})", text)
    if m:
        return (int(m.group(2)), _MONTHS.get(m.group(1), 1))
    m = re.search(r"\b(\d{4})\b", text)
    if m:
        return (int(m.group(1)), 1)
    return None


def _is_present(obj) -> bool:
    return isinstance(obj, dict) and str(obj.get("text", "")).strip().lower() in ("present", "current")


def _now_ym(now: datetime | None) -> tuple[int, int]:
    dt = now or _utcnow()
    return (dt.year, dt.month)


def _months_ago(ym: tuple[int, int], now_ym: tuple[int, int]) -> int:
    return (now_ym[0] - ym[0]) * 12 + (now_ym[1] - ym[1])


def _within(ym: tuple[int, int] | None, now_ym: tuple[int, int], window: int) -> bool:
    if ym is None:
        return False
    return -1 <= _months_ago(ym, now_ym) <= window   # small future slack for data noise


def _age_days(ym: tuple[int, int] | None, now_ym: tuple[int, int]) -> int:
    if ym is None:
        return -1
    try:
        return max(0, (date(*now_ym, 1) - date(*ym, 1)).days)
    except ValueError:
        return -1


def _ymstr(ym: tuple[int, int] | None) -> str:
    return f"{ym[0]:04d}-{ym[1]:02d}" if ym else ""


# --------------------------------------------------------------------------- #
# Phase 1 — LinkedIn career history
# --------------------------------------------------------------------------- #
def _positions(profile: dict) -> list[dict]:
    seq = profile.get("positions") or profile.get("experience") or []
    out: list[dict] = []
    if not isinstance(seq, list):
        return out
    for e in seq:
        if not isinstance(e, dict):
            continue
        title = str(e.get("position") or e.get("title") or e.get("jobTitle") or "").strip()
        company = str(e.get("companyName") or e.get("company") or "").strip()
        start = _ym(e.get("startDate"))
        end_obj = e.get("endDate")
        present = end_obj is None or _is_present(end_obj)
        if title and start is not None:
            out.append({
                "title": title, "company": company, "start": start,
                "end": None if present else _ym(end_obj), "present": present,
            })
    return out


def _summary(mtype: str, person: str, from_title: str, to_title: str, company: str) -> str:
    at = f" at {company}" if company else ""
    phrases = {
        "promotion": f"{person} promoted from {from_title} to {to_title}{at}",
        "role_change": f"{person} moved from {from_title} to {to_title}{at}",
        "new_executive_hire": f"{person} joined as {to_title}{at}",
        "executive_departure": f"{person} departed as {to_title}{at}",
        "board_appointment": f"{person} appointed to the board as {to_title}{at}",
        "founder_change": f"{person} — {to_title}{at}",
        "executive_reshuffle": f"Leadership reshuffle{at}",
    }
    return phrases.get(mtype, f"{person} — {to_title}{at}").strip()


def _mk(person: dict, p: dict, mtype: str, domain: str | None, now_ym: tuple[int, int],
        *, from_title: str = "", effective: tuple[int, int] | None = None) -> dict:
    eff = effective or p["start"]
    confidence = "high" if (domain and eff) else ("medium" if eff else "low")
    band = p["band"] or "director"
    raw = "|".join([
        person.get("linkedin_url") or person["person_name"],
        name_key(p["company"]) or p["company"].lower(), mtype, _ymstr(eff), p["title"].lower(),
    ])
    return {
        "signal_id": hashlib.sha1(raw.encode("utf-8")).hexdigest()[:32],
        "company_domain": domain,
        "company_name": p["company"],
        "decision_maker_id": person.get("dm_id"),
        "linkedin_url": person.get("linkedin_url", ""),
        "person_name": person["person_name"],
        "movement_type": mtype,
        "from_title": from_title,
        "to_title": p["title"],
        "seniority_band": band,
        "role_function": p["func"] or "",
        "effective_date": _ymstr(eff),
        "event_age_days": _age_days(eff, now_ym),
        "confidence": confidence,
        "source": "linkedin_history",
        "source_ref": person.get("linkedin_url", ""),
        "summary": _summary(mtype, person["person_name"], from_title, p["title"], p["company"]),
    }


def signals_from_person(person: dict, positions: list[dict], resolve, now_ym: tuple[int, int],
                        window: int) -> list[dict]:
    """Pure logic: positions + a ``resolve(company_name) -> domain|None`` callable
    → list of signal dicts. Kept DB-free so it is unit-testable in isolation."""
    rows: list[dict] = []
    for p in positions:
        bf = classify_seniority(p["title"])
        rows.append({**p, "band": bf[0] if bf else None, "func": bf[1] if bf else ""})

    out: list[dict] = []
    consumed: set[int] = set()     # the later role of a transition (already emitted)
    superseded: set[int] = set()   # the earlier role — ended internally, NOT a departure

    # Same-company transitions → promotion / role change.
    by_company: dict[str, list[tuple[int, dict]]] = {}
    for idx, p in enumerate(rows):
        by_company.setdefault(name_key(p["company"]) or p["company"].lower(), []).append((idx, p))
    for group in by_company.values():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda ip: ip[1]["start"])
        for (ai, a), (bi, b) in zip(ordered, ordered[1:]):
            if b["band"] is None or a["title"].strip().lower() == b["title"].strip().lower():
                continue
            if not _within(b["start"], now_ym, window):
                continue
            ra, rb = (rank(a["band"]) if a["band"] else 0), rank(b["band"])
            mtype = "promotion" if rb > ra else "role_change"
            out.append(_mk(person, b, mtype, resolve(b["company"]), now_ym, from_title=a["title"]))
            consumed.add(bi)
            superseded.add(ai)

    # Per-position singletons (joins / departures / founder / board).
    for idx, p in enumerate(rows):
        if p["band"] is None or idx in consumed:
            continue
        domain = resolve(p["company"])
        if p["band"] == "founder" and _within(p["start"], now_ym, window):
            out.append(_mk(person, p, "founder_change", domain, now_ym))
        elif p["func"] == "board" and _within(p["start"], now_ym, window):
            out.append(_mk(person, p, "board_appointment", domain, now_ym))
        elif p["present"] and _within(p["start"], now_ym, window):
            out.append(_mk(person, p, "new_executive_hire", domain, now_ym))
        elif not p["present"] and idx not in superseded and _within(p["end"], now_ym, window):
            # A role that ended without a same-company successor → the person left.
            out.append(_mk(person, p, "executive_departure", domain, now_ym, effective=p["end"]))
    return out


def _make_resolver(session: Session):
    cache: dict[str, str | None] = {}

    def resolve(company_name: str | None) -> str | None:
        key = name_key(company_name or "")
        if not key:
            return None
        if key not in cache:
            # Read-only: an explicit alias first, then a catalogued company by name_key.
            domain = session.scalar(select(CompanyAlias.company_domain).where(CompanyAlias.name_key == key))
            if domain is None:
                domain = session.scalar(select(Company.company_domain).where(Company.name_key == key))
            cache[key] = domain
        return cache[key]

    return resolve


def from_decision_makers(session: Session, *, window_months: int = DEFAULT_WINDOW_MONTHS,
                         now: datetime | None = None) -> list[dict]:
    now_ym = _now_ym(now)
    resolve = _make_resolver(session)
    signals: list[dict] = []
    for dm in session.scalars(select(DecisionMaker)):
        profile = dm.profile_data if isinstance(dm.profile_data, dict) else {}
        positions = _positions(profile)
        if not positions:
            continue
        name = f"{dm.first_name} {dm.last_name}".strip() or _person_from_headline(dm.headline) or "Unknown"
        person = {"linkedin_url": dm.linkedin_url, "person_name": name, "dm_id": dm.id}
        signals.extend(signals_from_person(person, positions, resolve, now_ym, window_months))
    signals = _dedup(signals)
    return signals + _reshuffles(signals, now_ym)


def _person_from_headline(headline: str | None) -> str:
    head = (headline or "").split(" at ")[0].split("|")[0].strip()
    return head if 0 < len(head) <= 60 else ""


def _reshuffles(signals: list[dict], now_ym: tuple[int, int]) -> list[dict]:
    """Aggregate: ≥2 distinct director+ moves at one resolved company within a
    short window → a company-level ``executive_reshuffle`` marker."""
    by_domain: dict[str, list[dict]] = {}
    for s in signals:
        if s["company_domain"] and s["movement_type"] in (
            "new_executive_hire", "executive_departure", "promotion", "role_change"
        ) and 0 <= s["event_age_days"] <= _RESHUFFLE_WINDOW_MONTHS * 31:
            by_domain.setdefault(s["company_domain"], []).append(s)
    out: list[dict] = []
    for domain, group in by_domain.items():
        people = {s["person_name"] for s in group}
        if len(people) < 2:
            continue
        recent = min(group, key=lambda s: s["event_age_days"])
        raw = f"reshuffle|{domain}|{recent['effective_date']}"
        out.append({
            "signal_id": hashlib.sha1(raw.encode("utf-8")).hexdigest()[:32],
            "company_domain": domain, "company_name": recent["company_name"],
            "decision_maker_id": None, "linkedin_url": "",
            "person_name": f"{len(people)} executives", "movement_type": "executive_reshuffle",
            "from_title": "", "to_title": "", "seniority_band": "director", "role_function": "",
            "effective_date": recent["effective_date"], "event_age_days": recent["event_age_days"],
            "confidence": "medium", "source": "linkedin_history", "source_ref": "",
            "summary": f"Leadership reshuffle at {recent['company_name']}: "
                       f"{len(people)} director+ moves in ~6 months",
        })
    return out


# --------------------------------------------------------------------------- #
# Phase 2 — Blog Crawler leadership events (best-effort extraction)
# --------------------------------------------------------------------------- #
_PERSON = r"([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){0,3})"
_ROLE = r"([A-Za-z][\w /&-]{2,40})"
# Every literal verb/connector is wrapped in a SCOPED case-insensitive group `(?i:…)`
# rather than compiling the whole pattern with re.I: real headlines are Title Case
# ("Acme Appoints Jane Doe As Its New CTO"), but `_PERSON`'s `[A-Z]` anchor must stay
# case-SENSITIVE or "the company appoints a new ceo" would extract "the" as a person.
_AS = r"(?i:\s+as\s+)"
_QUAL = r"(?i:its\s+|the\s+|new\s+|interim\s+)*"     # "as its new interim CTO"
_LEAD_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(rf"\b(?i:appoints?)\s+{_PERSON}{_AS}{_QUAL}{_ROLE}"), "new_executive_hire"),
    (re.compile(rf"\b(?i:names?)\s+{_PERSON}{_AS}{_QUAL}{_ROLE}"), "new_executive_hire"),
    (re.compile(rf"\b(?i:hires?)\s+{_PERSON}{_AS}{_QUAL}{_ROLE}"), "new_executive_hire"),
    (re.compile(rf"{_PERSON}\s+(?i:is\s+)?(?i:hired){_AS}{_QUAL}{_ROLE}"), "new_executive_hire"),
    # "… has been appointed (as) CTO" — the passive form, as common in headlines as the
    # active. The auxiliary is REQUIRED: it forces `_PERSON` (greedy, and "Has Been" is
    # itself Title Case) to backtrack off the auxiliary instead of swallowing it.
    (re.compile(rf"{_PERSON}\s+(?i:(?:has\s+been|is|was)\s+appointed)(?i:\s+as)?\s+{_QUAL}{_ROLE}"),
     "new_executive_hire"),
    (re.compile(rf"{_PERSON}\s+(?i:joins|joined)\b[^.]*?\b(?i:as)\s+{_QUAL}{_ROLE}"), "new_executive_hire"),
    (re.compile(rf"{_PERSON}\s+(?i:moves|moved|jumps)\s+(?i:from\s+)?(?:[\w\s&.,-]+?\s+)?(?i:to)\s+"
                rf"[\w\s&.,-]+?{_AS}{_QUAL}{_ROLE}"), "new_executive_hire"),
    (re.compile(rf"{_PERSON}\s+(?i:is\s+)?(?i:promoted\s+to)\s+{_ROLE}"), "promotion"),
    (re.compile(rf"\b(?i:promotes?)\s+{_PERSON}\s+(?i:to)\s+{_ROLE}"), "promotion"),
    (re.compile(rf"{_PERSON}\s+(?i:steps down|departs|resigns|to step down|is stepping down)"
                rf"(?:{_AS}{_ROLE})?"), "executive_departure"),
    (re.compile(rf"\b(?i:appoints?|names?|elects?)\s+{_PERSON}\s+(?i:to\s+(?:its|the)\s+board)\b"),
     "board_appointment"),
]
# Roles extracted from free text can trail into geography/time ("VP Engineering in
# Bengaluru", "CTO effective March") — strip that so the title stays clean; the
# location is captured separately via extract_geography() on the full article text.
_ROLE_STOP = re.compile(r"\s+\b(?:in|at|based in|effective|starting|from)\b.*$", re.I)


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip(" .,&/-")


def _clean_role(role: str) -> str:
    return _clean(_ROLE_STOP.sub("", role or ""))


def _extract_leadership(text: str) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    for pattern, mtype in _LEAD_PATTERNS:
        for m in pattern.finditer(text):
            person = _clean(m.group(1))
            role = "Board Member" if mtype == "board_appointment" else _clean_role(
                m.group(2) if m.lastindex and m.lastindex >= 2 else "") or "executive"
            if person:
                found.append((person, role, mtype))
    return found


def _published_ym(published_date: str | None) -> tuple[int, int] | None:
    return _ym({"text": published_date or ""})


# The opportunity_types the blog feeder reads: the legacy Blog Crawler title-case
# type AND the Change_03 company-news people-move types (structured signal).
_BLOG_LEADERSHIP_TYPES = ("Leadership Change", "LEADERSHIP_CHANGE", "EXECUTIVE_HIRE", "ROLE_CHANGE")
_NEWS_TYPES = frozenset({"LEADERSHIP_CHANGE", "EXECUTIVE_HIRE", "ROLE_CHANGE"})


def _from_news_signal(opp, sig: str | None = None) -> tuple[str, str, str, str] | None:
    """Parse the structured people-move form into ``(person, from_title, to_title,
    movement_type)`` — far more reliable than the free-text regex because the format
    is known. Returns ``None`` if it can't.

    ``sig`` defaults to the Change_03 ``company_news_signal`` column, but the caller
    may pass any candidate string (the News Collection Engine never populates that
    column — for feeds that carry the structured form the headline itself IS the
    signal). Returns ``None`` rather than guessing, so a non-structured string simply
    falls through to the free-text extractor."""
    sig = (sig if sig is not None else (opp.company_news_signal or "")).strip()
    if not sig:
        return None
    if opp.opportunity_type == "EXECUTIVE_HIRE":
        # The role must come from an explicit "as <role>" — never fall back to the
        # whole headline, which would fabricate a title once `sig` IS the headline.
        m = re.match(r"^(.+?)\s+joined\s+as\s+(.+?)(?:\s+\(ex-.*\))?$", sig, re.I)
        if not m:
            return None
        return _clean(m.group(1)), "", _clean(m.group(2)), "new_executive_hire"
    # LEADERSHIP_CHANGE / ROLE_CHANGE: "Person: From -> To (from X)" or "Person -> To"
    if "->" in sig:
        left, right = sig.split("->", 1)
        to_title = _clean(re.sub(r"\(from.*\)\s*$", "", right))
        if ":" in left:
            person, from_title = left.split(":", 1)
            return _clean(person), _clean(from_title), to_title, "role_change"
        return _clean(left), "", to_title, "role_change"
    return None


_DM_MATCH_CONFIDENCE_FLOOR = 0.75   # PlatformDecisionMakerIndex's company+name tier or better


def _match_decision_maker(dm_index: PlatformDecisionMakerIndex | None, *, company_domain: str | None,
                          person: str, title: str) -> int | None:
    """Conservative match against existing decision_makers, reusing the same
    company+name(+title) matching infrastructure the historical-import sync uses
    (sync.dm_sync.PlatformDecisionMakerIndex). No LinkedIn/email evidence is available
    from a news article, so this only ever reaches the company-name tiers (>=0.75) —
    same-name-different-company never collides (the index requires a domain match).
    Below the floor -> unresolved (never guessed, never attached to the wrong person)."""
    if dm_index is None or not company_domain or not person:
        return None
    dm_id, _match_type, confidence = dm_index.match(
        linkedin="", email="", domain=company_domain,
        person_key=norm_person_name(person), title=norm_title(title))
    return dm_id if (dm_id is not None and confidence >= _DM_MATCH_CONFIDENCE_FLOOR) else None


def _blog_signal(opp, person: str, from_title: str, to_title: str, mtype: str,
                 eff: tuple[int, int] | None, now_ym: tuple[int, int],
                 *, dm_index: PlatformDecisionMakerIndex | None = None) -> dict:
    bf = classify_seniority(to_title)
    # Keyed on the real-world event's identity (who/where/what/when) — deliberately
    # NOT on opp.opportunity_id, so two different articles (from the same or different
    # feeds) reporting the identical movement collapse to one signal instead of one
    # per article. A genuinely later event (different title/month) still gets its own row.
    raw = "|".join([opp.company_domain or "", person.lower(), mtype, to_title.lower(), _ymstr(eff)])
    geography = extract_geography(f"{opp.article_title or ''} {opp.summary or ''}")
    dm_id = _match_decision_maker(dm_index, company_domain=opp.company_domain, person=person, title=to_title)
    return {
        "signal_id": hashlib.sha1(raw.encode("utf-8")).hexdigest()[:32],
        "company_domain": opp.company_domain, "company_name": opp.company_name,
        "decision_maker_id": dm_id, "linkedin_url": "", "person_name": person,
        "movement_type": mtype, "from_title": from_title, "to_title": to_title,
        "seniority_band": bf[0], "role_function": bf[1],
        "effective_date": _ymstr(eff), "event_age_days": _age_days(eff, now_ym),
        "confidence": "medium" if eff else "low", "source": "blog_event",
        "source_ref": opp.opportunity_id or opp.article_url,
        "summary": (opp.summary or opp.article_title or "")[:500],
        "geography": geography,
    }


def from_blog_events(session: Session, *, now: datetime | None = None) -> list[dict]:
    """Derive person-level signals from ANY leadership-shaped opportunity — the legacy
    Blog Crawler ``Leadership Change`` type, the Change_03 company-news structured
    ``company_news_signal``, and (new) EXECUTIVE_HIRE/LEADERSHIP_CHANGE/ROLE_CHANGE
    opportunities from the News Collection Engine (any configured RSS or Google Alerts
    feed — content-driven, nothing here is source-specific). Director+ only (gated).

    Structured ``company_news_signal`` is tried first (more reliable, known format);
    when it's absent — which is always true for a News-Intelligence-sourced article,
    since that engine doesn't populate it — this falls back to the same free-text
    person+role extraction used for the legacy type, so no leadership-shaped opportunity
    is silently dropped just because it came from a different engine."""
    now_ym = _now_ym(now)
    out: list[dict] = []
    dm_index = PlatformDecisionMakerIndex.build(session)   # built once, reused per row
    rows = session.scalars(
        select(Opportunity).where(Opportunity.opportunity_type.in_(_BLOG_LEADERSHIP_TYPES))
    )
    for opp in rows:
        eff = _published_ym(opp.published_date)
        # company_news_signal first (populated only by the company-news ingestor); then
        # the headline, because a News-Collection-Engine row leaves that column empty yet
        # often carries the same structured form in its title ("A: X -> Y", "A joined as Y").
        sig = (opp.company_news_signal or "").strip() or (opp.article_title or "")
        parsed = _from_news_signal(opp, sig) if opp.opportunity_type in _NEWS_TYPES else None
        if parsed is not None:
            person, from_title, to_title, mtype = parsed
            if classify_seniority(to_title) is None:   # below director+ → out of scope
                continue
            out.append(_blog_signal(opp, person, from_title, to_title, mtype, eff, now_ym, dm_index=dm_index))
            continue
        text = f"{opp.article_title or ''}. {opp.summary or ''}"
        for person, role, mtype in _extract_leadership(text):
            if classify_seniority(role) is None:   # below director+ → out of scope
                continue
            out.append(_blog_signal(opp, person, "", role, mtype, eff, now_ym, dm_index=dm_index))
    return _dedup(out)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def _dedup(signals: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for s in signals:
        if s["signal_id"] in seen:
            continue
        seen.add(s["signal_id"])
        out.append(s)
    return out


# --------------------------------------------------------------------------- #
# Phase 3 — Decision Maker Snapshots (point-in-time comparison)
# --------------------------------------------------------------------------- #
def from_decision_maker_snapshots(session: Session, *, now: datetime | None = None) -> list[dict]:
    """Derive person-level signals from snapshot comparison (Apify engine).

    Each decision_maker_intelligence run captures a snapshot of current title/company/seniority.
    This function compares consecutive snapshots to detect movement:
    - Promotion: same company, title rank increases
    - Role change: same company, title rank same/decreases
    - New hire: different company, new role
    - Departure: person no longer in latest snapshot

    Director+ only (gated via seniority classification).
    """
    now_ym = _now_ym(now)
    out: list[dict] = []
    resolve = _make_resolver(session)

    # Get the most recent snapshot timestamp (to identify departures)
    latest_snapshot_ts = session.query(DecisionMakerSnapshot.captured_at)\
        .order_by(DecisionMakerSnapshot.captured_at.desc())\
        .limit(1).scalar()

    # Group snapshots by decision_maker_id, ordered by captured_at DESC
    dms = session.query(DecisionMaker).all()
    for dm in dms:
        snapshots = session.query(DecisionMakerSnapshot)\
            .filter(DecisionMakerSnapshot.decision_maker_id == dm.id)\
            .order_by(DecisionMakerSnapshot.captured_at.desc())\
            .all()

        if len(snapshots) < 2:
            continue  # Need at least 2 snapshots to detect change

        current = snapshots[0]
        previous = snapshots[1]

        # Gate: only director+ level
        if not classify_seniority(current.current_title):
            continue

        # Parse captured_at to YYYY-MM
        if current.captured_at:
            eff = (current.captured_at.year, current.captured_at.month)
        else:
            eff = now_ym

        name = f"{dm.first_name} {dm.last_name}".strip() or "Unknown"
        person_key = name.lower()

        # Detect movement type
        movement_type: str | None = None
        from_title = ""
        to_title = current.current_title

        if current.company_domain == previous.company_domain:
            # Same company: check for promotion or lateral move
            prev_rank = rank(previous.current_title)
            curr_rank = rank(current.current_title)
            if prev_rank is not None and curr_rank is not None:
                if curr_rank > prev_rank:
                    movement_type = "promotion"
                    from_title = previous.current_title
                elif curr_rank < prev_rank:
                    movement_type = "role_change"
                    from_title = previous.current_title
        else:
            # Different company: new hire (if not None domains)
            if current.company_domain and previous.company_domain:
                movement_type = "new_executive_hire"
                from_title = previous.current_title

        if not movement_type:
            continue

        domain = current.company_domain or resolve(current.current_company)
        bf = classify_seniority(to_title)
        seniority_band = bf[0] if bf else "director"
        role_function = bf[1] if bf else ""

        raw = "|".join([
            dm.linkedin_url or person_key,
            current.company_domain or current.current_company.lower(),
            movement_type,
            _ymstr(eff),
            to_title.lower(),
        ])
        signal = {
            "signal_id": hashlib.sha1(raw.encode("utf-8")).hexdigest()[:32],
            "company_domain": domain,
            "company_name": current.current_company,
            "decision_maker_id": dm.id,
            "linkedin_url": dm.linkedin_url,
            "person_name": name,
            "movement_type": movement_type,
            "from_title": from_title,
            "to_title": to_title,
            "seniority_band": seniority_band,
            "role_function": role_function,
            "effective_date": _ymstr(eff),
            "event_age_days": _age_days(eff, now_ym),
            "confidence": "high" if (domain and eff) else "medium",
            "source": "snapshot_comparison",
            "source_ref": f"dm_id={dm.id}",
            "summary": _summary(movement_type, name, from_title, to_title, current.current_company),
        }
        out.append(signal)

    # Detect departures: decision makers in previous snapshot but not in latest
    if latest_snapshot_ts:
        prev_ts_query = session.query(DecisionMakerSnapshot.captured_at)\
            .filter(DecisionMakerSnapshot.captured_at < latest_snapshot_ts)\
            .order_by(DecisionMakerSnapshot.captured_at.desc())\
            .limit(1).scalar()

        if prev_ts_query:
            current_dms = set(session.query(DecisionMakerSnapshot.decision_maker_id)\
                .filter(DecisionMakerSnapshot.captured_at == latest_snapshot_ts).all())
            previous_dms = set(session.query(DecisionMakerSnapshot.decision_maker_id)\
                .filter(DecisionMakerSnapshot.captured_at == prev_ts_query).all())

            departed_ids = previous_dms - current_dms

            for (dm_id,) in departed_ids:
                dm = session.query(DecisionMaker).filter(DecisionMaker.id == dm_id).first()
                if not dm:
                    continue

                prev_snapshot = session.query(DecisionMakerSnapshot)\
                    .filter(DecisionMakerSnapshot.decision_maker_id == dm_id,
                            DecisionMakerSnapshot.captured_at == prev_ts_query)\
                    .first()

                if not prev_snapshot or not classify_seniority(prev_snapshot.current_title):
                    continue

                eff = (latest_snapshot_ts.year, latest_snapshot_ts.month)
                name = f"{dm.first_name} {dm.last_name}".strip() or "Unknown"
                person_key = name.lower()

                domain = prev_snapshot.company_domain or resolve(prev_snapshot.current_company)
                bf = classify_seniority(prev_snapshot.current_title)
                seniority_band = bf[0] if bf else "director"
                role_function = bf[1] if bf else ""

                raw = "|".join([
                    dm.linkedin_url or person_key,
                    prev_snapshot.company_domain or prev_snapshot.current_company.lower(),
                    "executive_departure",
                    _ymstr(eff),
                    prev_snapshot.current_title.lower(),
                ])
                signal = {
                    "signal_id": hashlib.sha1(raw.encode("utf-8")).hexdigest()[:32],
                    "company_domain": domain,
                    "company_name": prev_snapshot.current_company,
                    "decision_maker_id": dm_id,
                    "linkedin_url": dm.linkedin_url,
                    "person_name": name,
                    "movement_type": "executive_departure",
                    "from_title": prev_snapshot.current_title,
                    "to_title": "",
                    "seniority_band": seniority_band,
                    "role_function": role_function,
                    "effective_date": _ymstr(eff),
                    "event_age_days": _age_days(eff, now_ym),
                    "confidence": "high" if domain else "medium",
                    "source": "snapshot_comparison",
                    "source_ref": f"dm_id={dm_id}",
                    "summary": _summary("executive_departure", name, prev_snapshot.current_title, "", prev_snapshot.current_company),
                }
                out.append(signal)

    return _dedup(out)


def _apply_priority(session: Session, signals: list[dict]) -> list[dict]:
    """Stamp the reusable ``priority_tier`` (leadership_signals/priority.py) onto every
    signal, from any source — startup/scaleup companies and India-relevant movement are
    high priority; unrelated overseas movement at an established/incumbent company ranks
    lower (kept, never discarded). Company tier is read once for the whole batch."""
    tiers = dict(session.execute(select(Company.company_domain, Company.company_tier)).all())
    for s in signals:
        s.setdefault("geography", "")
        s["priority_tier"] = priority_tier(tiers.get(s.get("company_domain")), s["geography"])
    return signals


def _replace(session: Session, source: str, signals: list[dict]) -> None:
    from orchestrator import provenance

    session.execute(delete(LeadershipSignal).where(LeadershipSignal.source == source))
    session.flush()
    stamp = _utcnow()
    for s in signals:
        session.add(LeadershipSignal(**s, computed_at=stamp))
        provenance.record(session, "leadership_signals", s["signal_id"], "derived", {
            "person_name": s.get("person_name", ""),
            "company_name": s.get("company_name", ""),
            "movement_type": s.get("movement_type", ""),
            "to_title": s.get("to_title", ""),
            "effective_date": s.get("effective_date", ""),
            "source": source,
        })


def rebuild(session: Session, *, window_months: int = DEFAULT_WINDOW_MONTHS,
            now: datetime | None = None, include_blog: bool = True, include_snapshots: bool = True) -> dict[str, int]:
    """Recompute every signal (idempotent, per-source delete + insert).

    Rebuilds signals from three sources:
    - linkedin_history: decision maker career history (deprecated when Apify-only)
    - blog_event: blog/company news opportunities
    - snapshot_comparison: consecutive decision maker snapshots (new for Apify)
    """
    li = _apply_priority(session, from_decision_makers(session, window_months=window_months, now=now))
    _replace(session, "linkedin_history", li)

    blog = _apply_priority(session, from_blog_events(session, now=now)) if include_blog else []
    if include_blog:
        _replace(session, "blog_event", blog)

    snapshots = _apply_priority(session, from_decision_maker_snapshots(session, now=now)) if include_snapshots else []
    if include_snapshots:
        _replace(session, "snapshot_comparison", snapshots)

    session.commit()
    return {
        "linkedin_history": len(li),
        "blog_event": len(blog),
        "snapshot_comparison": len(snapshots),
        "total": len(li) + len(blog) + len(snapshots)
    }
