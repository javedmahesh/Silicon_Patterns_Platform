"""Apify Decision Maker Intelligence -> decision_makers.

Replaces the LinkedIn scraper with Apify-powered decision-maker scraping.
Apify returns current position data (no career history), so we store the Apify
metadata in profile_data for potential future enrichment.

Field names are mapped from the leads-scraper-ppe actor's VERIFIED output schema:
  position -> current_title, organizationName -> resolved_company_name,
  organizationWebsite -> company_domain (scheme/www stripped), linkedinUrl, email,
  phone_numbers, city/state/country -> location.

Company resolution: the actor returns ``organizationWebsite`` (e.g.
"https://nvidia.com"). We normalize it to a bare domain and resolve it against the
companies table. If it resolves, we link it; if not, we keep the person with a NULL
domain (FK-safe) and stash the raw org domain in profile_data, rather than dropping a
verified C-suite contact.

Source: Apify actor output (JSON records via API call).
"""
from __future__ import annotations

from typing import Any

from integration.ingestors.base import BaseIngestor, RowResult
from master_db.models import Company, DecisionMaker

_SENIORITY_LEVELS = {
    "c_level": "senior",
    "founder": "senior",
    "ceo": "senior",
    "executive": "senior",
    "vp": "senior",
    "vice_president": "senior",
    "director": "senior",
    "manager": "",
    "senior_manager": "senior",
    "staff": "",
    "senior_staff": "",
}

_DIRECTOR_PLUS_KEYWORDS = (
    "chief", "cxo", "ceo", "cto", "coo", "cfo", "cro", "clso",
    "founder", "co-founder", "partner",
    "vp", "vice president", "vice-president",
    "director", "managing director", "head of",
    "evp", "executive vice president", "svp", "senior vice president",
)


def _seniority_from_title(title: str) -> str:
    """Classify seniority from title string."""
    low = (title or "").lower()
    return "senior" if any(m in low for m in _DIRECTOR_PLUS_KEYWORDS) else ""


def _or_none(value: str) -> str | None:
    """Return a stripped string, or None when empty.

    The structured ``decision_makers`` columns are NULLABLE on purpose: a field the
    actor didn't return must stay NULL rather than carry a "" placeholder.
    """
    v = (value or "").strip()
    return v or None


def _join(value: Any) -> str:
    """Stringify a scalar/list field for storage in profile_data (lists → comma-
    joined; numbers → str). Safe on None/int/list, unlike ``self.s``."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v).strip() for v in value if str(v).strip())
    return str(value).strip()


def _extract_name(row: dict[str, Any]) -> tuple[str, str]:
    """Extract first and last name, handling camelCase and snake_case."""
    first = (
        row.get("firstName") or
        row.get("first_name") or
        row.get("first") or
        ""
    ).strip()
    last = (
        row.get("lastName") or
        row.get("last_name") or
        row.get("last") or
        ""
    ).strip()
    return first, last


def _extract_title(row: dict[str, Any]) -> str:
    """Extract current title, preferring more complete versions.

    The leads-scraper-ppe actor uses ``position``; the other keys are accepted as
    fallbacks for forward-compat with alternative actors.
    """
    return (
        row.get("position") or
        row.get("currentTitle") or
        row.get("current_title") or
        row.get("title") or
        row.get("jobTitle") or
        row.get("job_title") or
        row.get("headline") or
        ""
    ).strip()


def _normalize_domain(raw: str) -> str:
    """Normalize a website/URL to a bare lowercase domain.

    "https://www.NVIDIA.com/about" -> "nvidia.com". Matches the companies table's
    company_domain format (lowercase, no scheme, no path, no www).
    """
    d = (raw or "").strip().lower()
    if not d:
        return ""
    # strip scheme
    if "://" in d:
        d = d.split("://", 1)[1]
    # strip path / query
    d = d.split("/", 1)[0].split("?", 1)[0]
    # strip leading www.
    if d.startswith("www."):
        d = d[4:]
    return d


def _extract_company(row: dict[str, Any]) -> tuple[str, str]:
    """Extract company name and normalized bare domain.

    The leads-scraper-ppe actor uses ``organizationName`` / ``organizationWebsite``;
    older keys are accepted as fallbacks.
    """
    name = (
        row.get("organizationName") or
        row.get("companyName") or
        row.get("company_name") or
        row.get("company") or
        ""
    ).strip()
    raw_domain = (
        row.get("organizationWebsite") or
        row.get("companyDomain") or
        row.get("company_domain") or
        row.get("domain") or
        ""
    )
    return name, _normalize_domain(raw_domain)


def _extract_linkedin_url(row: dict[str, Any]) -> str:
    """Extract LinkedIn profile URL."""
    url = (
        row.get("linkedinUrl") or
        row.get("linkedin_url") or
        row.get("url") or
        ""
    ).strip()
    if url:
        url = url.split("?")[0].strip().lower()
    return url


class ApifyIngestor(BaseIngestor):
    """Ingestor for Apify Decision Maker Intelligence actor output.

    Configuration:
    - bulk_model: DecisionMaker (bulk upsert)
    - bulk_conflict: ("linkedin_url",) — dedup by LinkedIn URL if present

    Note: Apify may not provide LinkedIn URLs for all records. If linkedin_url
    is missing, the record is rejected (we require it for dedup).
    """

    engine_name = "decision_maker_intelligence"
    bulk_model = DecisionMaker
    bulk_conflict = ("linkedin_url",)

    def build_row(self, row: dict[str, Any]) -> RowResult:
        """Transform an Apify record to decision_makers schema."""

        # LinkedIn URL is our dedup key
        linkedin_url = _extract_linkedin_url(row)
        if not linkedin_url:
            return RowResult(rejected=True, reason="missing linkedin_url")

        first_name, last_name = _extract_name(row)
        if not first_name and not last_name:
            return RowResult(rejected=True, reason="missing name")

        current_title = _extract_title(row)
        if not current_title:
            return RowResult(rejected=True, reason="missing current_title")

        company_name, raw_domain = _extract_company(row)
        if not raw_domain:
            # Strict mode: skip records without any company domain (no review queue)
            return RowResult(rejected=True, reason="missing company_domain")

        # Resolve the org domain against the companies table (the FK target).
        # If it isn't one of our tracked companies, keep the person with a NULL
        # domain (FK-safe) rather than dropping a verified decision maker.
        company_domain: str | None = raw_domain
        if self.session.get(Company, raw_domain) is None:
            company_domain = None

        # Geography: keep the granular parts AND a human-readable composite.
        city = self.s(row.get("city"))
        state = self.s(row.get("state") or row.get("region") or row.get("stateRegion"))
        country = self.s(row.get("country"))
        loc_parts = [city, state, country]
        location = ", ".join(p for p in loc_parts if p) or self.s(row.get("location"))
        seniority = _seniority_from_title(current_title)

        full_name = self.s(row.get("fullName") or row.get("full_name")) or \
            " ".join(p for p in (first_name, last_name) if p)
        functional = self.s(row.get("functional") or row.get("functionalArea") or
                            row.get("function"))
        email = self.s(row.get("email"))
        all_emails = self.s(row.get("all_emails"))
        email_status = self.s(row.get("contactEmailStatus") or row.get("emailStatus"))
        phone = self.s(row.get("phone_numbers") or row.get("phone") or row.get("mobile"))
        org_website = self.s(row.get("organizationWebsite") or row.get("companyWebsite"))
        org_linkedin = self.s(row.get("organizationLinkedinUrl") or row.get("companyLinkedinUrl"))
        org_id = self.s(row.get("organizationId") or row.get("organization_id"))
        headline = self.s(row.get("headline")) or current_title

        # Preserve the COMPLETE raw actor record so future features can use any field
        # without re-ingesting. Curated keys remain for existing readers/back-compat.
        profile_data = {
            "source": "apify",
            "person_id": self.s(row.get("personId")),
            "full_name": full_name,
            "location": location,
            "email": email,
            "all_emails": all_emails,
            "phone": phone,
            "email_status": email_status,
            "apify_seniority": self.s(row.get("seniority")),
            "functional": functional,
            "company_name": company_name,
            "company_domain": raw_domain,          # raw org domain, even if unresolved
            "organization_id": org_id,
            "resolved": company_domain is not None,
            "company_size": self.s(row.get("organizationSize") or row.get("companySize")),
            "industry": self.s(row.get("organizationIndustry") or row.get("industry")),
            "company_linkedin": org_linkedin,
            "headline": headline,
            # Extended enterprise enrichment (curated for clean reads; full fidelity
            # always remains in "raw"). Absent fields stay "" — never a placeholder.
            "photo_url": _join(row.get("photoUrl") or row.get("photo") or row.get("imageUrl")
                               or row.get("profilePicture") or row.get("picture")),
            "department": _join(row.get("department") or row.get("departments")),
            "business_unit": _join(row.get("businessUnit") or row.get("business_unit")),
            "summary": _join(row.get("summary") or row.get("about") or row.get("bio")),
            "skills": _join(row.get("skills") or row.get("topSkills")),
            "languages": _join(row.get("languages") or row.get("language")),
            "years_in_company": _join(row.get("yearsInCompany") or row.get("companyTenure")),
            "years_in_role": _join(row.get("yearsInRole") or row.get("roleTenure")),
            "followers": _join(row.get("followers") or row.get("followersCount")),
            "connections": _join(row.get("connections") or row.get("connectionsCount")),
            "raw": row,                            # full, unmodified actor response
        }

        return RowResult(values={
            "linkedin_url": linkedin_url,
            "company_domain": company_domain,
            "resolved_company_name": company_name,
            "first_name": first_name,
            "last_name": last_name,
            "headline": headline,
            "current_title": current_title,
            "seniority": seniority,
            "location": location,
            # Structured professional fields — NULL when the actor didn't supply them.
            "full_name": _or_none(full_name),
            "functional_area": _or_none(functional),
            "work_email": _or_none(email),
            "email_status": _or_none(email_status),
            "work_phone": _or_none(phone),
            "city": _or_none(city),
            "state_region": _or_none(state),
            "country": _or_none(country),
            "organization_website": _or_none(org_website),
            "organization_linkedin": _or_none(org_linkedin),
            "match_score": 0.0,  # Apify doesn't provide match scores
            "agent_score": None,
            "agent_reasoning": "Source: Apify Decision Maker Intelligence",
            "status": "sourced",
            "profile_data": profile_data,
            "source": "apify",
        })
