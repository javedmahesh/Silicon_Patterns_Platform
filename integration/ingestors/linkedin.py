"""LinkedIn Scraper -> decision_makers.

The hard case: LinkedIn carries NO company domain — only a free-text current
employer (inside profile_data positions/experience, or parseable from the
headline). This ingestor resolves that name to a ``company_domain`` best-effort
(alias/fuzzy); when it can't, the person is still written with a NULL domain and
the resolver queues the employer for review. The person record is never dropped.

Source: a candidates export (JSON array, or a Supabase REST dump). Accepts both
snake_case (Supabase columns) and camelCase (React schema) keys.
"""
from __future__ import annotations

from typing import Any

from integration.ingestors.base import BaseIngestor, RowResult
from master_db.models import DecisionMaker

_SENIOR_MARKERS = (
    "chief", "cxo", "ceo", "cto", "coo", "cfo", "vp", "vice president", "head of",
    "director", "principal", "staff", "senior", "sr.", "lead", "manager", "founder",
)


def _clean_url(url: str) -> str:
    return (url or "").split("?")[0].strip().lower()


def _first(row: dict[str, Any], *keys: str) -> str:
    for k in keys:
        v = row.get(k)
        if v:
            return str(v).strip()
    return ""


def _current_company(row: dict[str, Any]) -> str:
    """Best-effort current employer from a candidate record."""
    direct = _first(row, "current_company", "company", "companyName", "company_name")
    if direct:
        return direct
    profile = row.get("profile_data") or row.get("profileData") or {}
    if isinstance(profile, dict):
        for key in ("positions", "experience"):
            seq = profile.get(key)
            if isinstance(seq, list) and seq and isinstance(seq[0], dict):
                co = seq[0].get("companyName") or seq[0].get("company")
                if co:
                    return str(co).strip()
    # Fall back to "Title at Company" parsed from the headline.
    headline = _first(row, "headline")
    if " at " in headline:
        return headline.split(" at ", 1)[1].strip()
    return ""


def _seniority(title: str) -> str:
    low = title.lower()
    return "senior" if any(m in low for m in _SENIOR_MARKERS) else ""


class LinkedInIngestor(BaseIngestor):
    engine_name = "linkedin"
    # High-volume: bulk-upsert decision makers in one statement (keyed on linkedin_url).
    bulk_model = DecisionMaker
    bulk_conflict = ("linkedin_url",)

    def build_row(self, row: dict[str, Any]) -> RowResult:
        linkedin_url = _clean_url(_first(row, "linkedin_url", "linkedinUrl", "url"))
        if not linkedin_url:
            return RowResult(rejected=True, reason="missing linkedin_url")

        company_name = _current_company(row)
        # Resolve by NAME only (LinkedIn has no domain). Never create a stub from
        # a person record — an unmatched employer goes to the review queue.
        res = self.resolver.resolve(
            name=company_name or None, source_engine=self.engine_name,
            source_ref=linkedin_url, create_stub=False,
        )

        title = _first(row, "current_title", "currentTitle", "jobTitle", "headline")
        profile = row.get("profile_data") or row.get("profileData") or {}
        return RowResult(review_queued=res.review_queued, values={
            "linkedin_url": linkedin_url,
            "company_domain": res.company_domain,  # may be None (nullable FK)
            "resolved_company_name": company_name,
            "first_name": _first(row, "first_name", "firstName"),
            "last_name": _first(row, "last_name", "lastName"),
            "headline": _first(row, "headline"),
            "current_title": title,
            "seniority": _seniority(title),
            "location": _first(row, "location"),
            "match_score": self.f(row.get("match_score") if "match_score" in row else row.get("matchScore")),
            "agent_score": (None if row.get("agent_score") in (None, "") and row.get("agentScore") in (None, "")
                            else self.f(row.get("agent_score") if row.get("agent_score") not in (None, "") else row.get("agentScore"))),
            "agent_reasoning": _first(row, "agent_reasoning", "agentReasoning"),
            "status": _first(row, "status") or "sourced",
            "profile_data": profile if isinstance(profile, dict) else {},
            "source": "linkedin",
        })
