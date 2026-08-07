"""NVIDIA Inception connector configuration.

Every limit is environment-driven. Defaults are conservative because the target is
a third party's infrastructure.

Discovery uses two public surfaces, in order of reliability:

* the locale sitemap (``en-us.sitemap.xml``) — static XML, complete, and the
  enumeration method a site publishes *for* crawlers;
* the Inception showcase and case-study index pages, for links that appear in
  server-rendered HTML.

Notably NOT used: ``?page=`` pagination. ``www.nvidia.com/robots.txt`` carries
``Disallow: /*[?&]page=*``, so paginating that way would violate it. The sitemap
makes it unnecessary — it returns every case study in one request.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlparse

#: Query parameters www.nvidia.com/robots.txt disallows for a generic crawler.
#: Enforced by :func:`robots_allows` so a misconfigured URL is refused rather than
#: quietly fetched.
DISALLOWED_QUERY_PARAMS: frozenset[str] = frozenset({
    "page", "topicpage", "commentpage", "section", "target", "ref", "cid", "eid",
    "nvid", "ncid", "lx", "jso", "link", "hstc", "accesstoken", "regcode",
    "wcmmode", "srsltid", "nv_excludes",
})

#: Path prefixes robots.txt disallows that a crawl might otherwise wander into.
DISALLOWED_PATH_PREFIXES: tuple[str, ...] = (
    "/content/g/", "/content/gated-pdfs/", "/gated-resources/", "/admin/", "/attach/",
    "/content/forms/", "/content/temp/", "/forms/", "/props/", "/email-verify/",
    "/ddl2", "/processFind",
)

#: Public index pages that link to Inception member case studies.
DEFAULT_INDEX_PATHS: tuple[str, ...] = (
    "/en-us/startups/showcase/",
    "/en-us/case-studies/",
)

CASE_STUDY_PREFIX = "/case-studies/"


def robots_allows(url: str) -> bool:
    """True when ``url`` is outside www.nvidia.com/robots.txt's Disallow set.

    Checked before every request. A crawler that ignores robots.txt is not one this
    platform ships, and the ``?page=`` rule in particular is easy to violate by
    reflex when adding pagination later.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    path = parsed.path or "/"
    if any(path.startswith(prefix) for prefix in DISALLOWED_PATH_PREFIXES):
        return False
    for key, _value in parse_qsl(parsed.query or "", keep_blank_values=True):
        name = key.strip().lower()
        # robots.txt disallows the whole utm_* family, so match by prefix.
        if name in DISALLOWED_QUERY_PARAMS or name.startswith("utm"):
            return False
    return True


@dataclass(slots=True)
class NvidiaInceptionConfig:
    """Runtime knobs for one NVIDIA Inception discovery run."""

    base_url: str = "https://www.nvidia.com"
    #: Locale sitemap listing every published page, case studies included.
    sitemap_path: str = "/en-us/en-us.sitemap.xml"
    use_sitemap: bool = True
    index_paths: tuple[str, ...] = DEFAULT_INDEX_PATHS
    #: Index pages walked per run. The sitemap makes this a secondary source, so the
    #: default is small.
    max_pages: int = 2
    #: Case-study pages fetched per run — the expensive bound, one request each.
    max_companies: int = 50
    crawl_depth: int = 1
    #: Fetch each case study for detail, or stop at what the index/sitemap exposes.
    fetch_company_pages: bool = True
    incremental: bool = True
    request_timeout_seconds: int = 30
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_settings(cls, settings) -> "NvidiaInceptionConfig":
        raw_paths = (getattr(settings, "nvidia_inception_index_paths_raw", "") or "").strip()
        paths = tuple(p.strip() for p in raw_paths.split(",") if p.strip()) or DEFAULT_INDEX_PATHS
        return cls(
            base_url=getattr(settings, "nvidia_inception_base_url", cls.base_url).rstrip("/"),
            sitemap_path=getattr(settings, "nvidia_inception_sitemap_path", cls.sitemap_path),
            use_sitemap=getattr(settings, "nvidia_inception_use_sitemap", True),
            index_paths=paths,
            max_pages=getattr(settings, "nvidia_inception_max_pages", cls.max_pages),
            max_companies=getattr(settings, "nvidia_inception_max_companies", cls.max_companies),
            crawl_depth=getattr(settings, "nvidia_inception_crawl_depth", cls.crawl_depth),
            fetch_company_pages=getattr(settings, "nvidia_inception_fetch_company_pages", True),
            incremental=getattr(settings, "nvidia_inception_incremental", True),
            request_timeout_seconds=getattr(settings, "crawl_timeout_seconds", 30),
        )

    @property
    def sitemap_url(self) -> str:
        return f"{self.base_url}{self.sitemap_path}"

    def index_url(self, path: str) -> str:
        return f"{self.base_url}{path}"
