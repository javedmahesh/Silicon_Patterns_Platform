"""ATS / job-board / publisher host denylist.

Integration risk flagged in P0: a careers page such as ``jobs.lever.co`` or
``boards.greenhouse.io`` would otherwise resolve to the **ATS** domain and create
a junk company stub. Likewise an article on ``techcrunch.com`` is a publisher,
not the subject company. This module recognises those hosts so ingestors treat
them as "no company domain" and fall back to name-based resolution (or the
review queue) instead of minting a bogus company.
"""
from __future__ import annotations

from integration.normalizer import normalize_domain

# Applicant-tracking systems / job boards. A domain ending in one of these is a
# hiring platform, never the employer.
ATS_HOSTS: frozenset[str] = frozenset(
    {
        "lever.co", "greenhouse.io", "boards.greenhouse.io", "ashbyhq.com",
        "myworkdayjobs.com", "workday.com", "icims.com", "smartrecruiters.com",
        "jobvite.com", "workable.com", "bamboohr.com", "taleo.net", "brassring.com",
        "recruitee.com", "breezy.hr", "jazz.co", "jazzhr.com", "applytojob.com",
        "indeed.com", "linkedin.com", "glassdoor.com", "ziprecruiter.com",
        "monster.com", "dice.com", "wellfound.com", "angel.co", "builtin.com",
        "naukri.com", "hirist.com", "instahyre.com", "teamtailor.com",
        "pinpointhq.com", "rippling.com", "gem.com", "eightfold.ai",
    }
)

# News / aggregator / social hosts that surface companies but are not the company.
PUBLISHER_HOSTS: frozenset[str] = frozenset(
    {
        "techcrunch.com", "venturebeat.com", "eetimes.com", "eenewseurope.com",
        "semiwiki.com", "anandtech.com", "theregister.com", "reuters.com",
        "bloomberg.com", "forbes.com", "businesswire.com", "prnewswire.com",
        "globenewswire.com", "medium.com", "substack.com", "wordpress.com",
        "blogspot.com", "github.io", "youtube.com", "twitter.com", "x.com",
        "facebook.com", "crunchbase.com", "wikipedia.org",
    }
)


def is_ats_host(domain: str) -> bool:
    d = normalize_domain(domain)
    return bool(d) and (d in ATS_HOSTS or any(d == h or d.endswith("." + h) for h in ATS_HOSTS))


def is_publisher_host(domain: str) -> bool:
    d = normalize_domain(domain)
    return bool(d) and (d in PUBLISHER_HOSTS or any(d == h or d.endswith("." + h) for h in PUBLISHER_HOSTS))


def is_disallowed_company_host(domain: str) -> bool:
    """True when *domain* is an ATS or publisher host and must NOT be treated as
    a company's registrable domain."""
    return is_ats_host(domain) or is_publisher_host(domain)


def company_domain_or_blank(raw: str | None) -> str:
    """Normalize *raw* to a company domain, or return ``""`` if it resolves to an
    ATS/publisher host (so the caller resolves by name instead of by a bogus
    domain). This is the single guard every ingestor uses before trusting a
    domain/website value."""
    domain = normalize_domain(raw)
    if not domain or is_disallowed_company_host(domain):
        return ""
    return domain
