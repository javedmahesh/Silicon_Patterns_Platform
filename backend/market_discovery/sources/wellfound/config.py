"""Wellfound connector configuration.

Every limit is environment-driven — nothing here is hardcoded. Defaults are
deliberately conservative: this connector crawls a third-party site, so the cost of
a too-large default is someone else's infrastructure.
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: Public listing surfaces the connector may start from. Wellfound's robots.txt
#: disallows /_jobs/, /auth/, /u/, /projects/, /re/ and query-parameter variants;
#: none of these paths are in that set. Discovery starts here and follows only
#: /company/<slug> links, so the crawl never wanders into a disallowed area.
DEFAULT_LISTING_PATHS: tuple[str, ...] = (
    "/startups",
    "/discover/startups",
)

#: Only company pages are ever fetched for detail.
COMPANY_PATH_PREFIX = "/company/"


@dataclass(slots=True)
class WellfoundConfig:
    """Runtime knobs for one Wellfound discovery run."""

    base_url: str = "https://wellfound.com"
    listing_paths: tuple[str, ...] = DEFAULT_LISTING_PATHS
    #: Listing pages to walk per run (pagination bound).
    max_pages: int = 3
    #: Company detail pages to fetch per run. The expensive number — each is one
    #: crawl request against a third party.
    max_companies: int = 50
    #: Crawl depth handed to the crawl service for a listing page.
    crawl_depth: int = 1
    #: Fetch each company's own page for detail, or stop at what the listing shows.
    #: Off makes a run cheap and shallow; on makes it slow and rich.
    fetch_company_pages: bool = True
    #: Skip companies whose candidate_key the platform already stored.
    incremental: bool = True
    request_timeout_seconds: int = 30
    #: Extra filters appended to a listing URL (e.g. "?stage=seed"). Kept as opaque
    #: strings so a change to Wellfound's filter syntax needs no code change.
    listing_query: str = ""
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_settings(cls, settings) -> "WellfoundConfig":
        raw_paths = (getattr(settings, "wellfound_listing_paths_raw", "") or "").strip()
        paths = tuple(p.strip() for p in raw_paths.split(",") if p.strip()) or DEFAULT_LISTING_PATHS
        return cls(
            base_url=getattr(settings, "wellfound_base_url", cls.base_url).rstrip("/"),
            listing_paths=paths,
            max_pages=getattr(settings, "wellfound_max_pages", cls.max_pages),
            max_companies=getattr(settings, "wellfound_max_companies", cls.max_companies),
            crawl_depth=getattr(settings, "wellfound_crawl_depth", cls.crawl_depth),
            fetch_company_pages=getattr(settings, "wellfound_fetch_company_pages", True),
            incremental=getattr(settings, "wellfound_incremental", True),
            request_timeout_seconds=getattr(settings, "crawl_timeout_seconds", 30),
            listing_query=getattr(settings, "wellfound_listing_query", ""),
        )

    def listing_url(self, path: str, page: int) -> str:
        """Page 1 is the bare path; later pages use Wellfound's ``?page=`` parameter."""
        url = f"{self.base_url}{path}"
        params = [p for p in (self.listing_query.lstrip("?"), f"page={page}" if page > 1 else "") if p]
        return f"{url}?{'&'.join(params)}" if params else url

    def company_url(self, slug: str) -> str:
        return f"{self.base_url}{COMPANY_PATH_PREFIX}{slug.strip('/')}"
