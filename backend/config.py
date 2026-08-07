"""Environment-based configuration (pydantic-settings).

All values are overridable via environment variables (or a .env file). The most
important is ``DATABASE_URL`` — defaults to the local SQLite master DB for review,
set it to the Supabase/Postgres URL in production.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLATFORM_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = _PLATFORM_ROOT / "master_local.db"


class Settings(BaseSettings):
    # populate_by_name lets the Python field name be used directly (e.g. Settings(api_key=...)
    # in tests) even when a field declares a validation_alias below.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )

    app_name: str = "Silicon Patterns Platform API"
    app_version: str = "1.0.0"
    app_description: str = "Unified read API over the Silicon Patterns master database."

    # sqlite:///... locally; postgresql+psycopg://user:pass@host/db (Supabase) in prod.
    database_url: str = f"sqlite:///{_DEFAULT_DB.as_posix()}"

    # Connection pooling (applied for non-SQLite engines).
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_echo: bool = False

    log_level: str = "INFO"
    log_json: bool = True

    # API key gate. Empty = auth DISABLED (local/dev/tests). Set SP_API_KEY in
    # prod; clients send it as the `X-API-Key` header. Bound from SP_API_KEY
    # (canonical — used by render.yaml + docs) or the bare API_KEY.
    api_key: str = Field("", validation_alias=AliasChoices("SP_API_KEY", "API_KEY"))

    # Simple in-memory rate limit (requests / minute / client IP). 0 disables it
    # (dev default). Set e.g. SP_RATE_LIMIT_PER_MINUTE=120 in prod. NOTE: per-process —
    # for multiple API instances, front it with a shared store (Redis) or a gateway limit.
    # Bound from SP_RATE_LIMIT_PER_MINUTE (canonical) or the bare RATE_LIMIT_PER_MINUTE.
    rate_limit_per_minute: int = Field(
        0, validation_alias=AliasChoices("SP_RATE_LIMIT_PER_MINUTE", "RATE_LIMIT_PER_MINUTE")
    )

    # Restricted by default to the dev frontend origin. In prod set this to your
    # deployed frontend origin(s) — never "*" with credentials.
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    default_page_size: int = 25
    max_page_size: int = 200

    # Server-side location of the uploaded historical export the sync-preview endpoint
    # reconciles (Phase 2). Empty by default; the Phase-3 import UI will replace this
    # with a real per-request upload. Bound from SP_HISTORICAL_IMPORT_PATH.
    historical_import_path: str = Field(
        "", validation_alias=AliasChoices("SP_HISTORICAL_IMPORT_PATH")
    )

    # Analytics responses are cached (ETag + in-process memo) and only change when a
    # refresh completes (twice daily), so this Cache-Control max-age can be generous.
    # 0 = revalidate every request (still cheap — a 304 when data is unchanged).
    # Env: ANALYTICS_CACHE_SECONDS.
    analytics_cache_seconds: int = 300

    # --- Deployment environment ---
    # Explicit environment marker — defaults to 'development' so local runs and the test
    # suite keep today's zero-config behavior untouched. Only 'production' changes any
    # behavior (see is_production / security._bypass_on): it hard-disables the dev auth
    # bypass no matter what else is or isn't configured. Env: ENVIRONMENT or SP_ENVIRONMENT.
    environment: str = Field(
        "development", validation_alias=AliasChoices("ENVIRONMENT", "SP_ENVIRONMENT")
    )

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    # --- Auth: Microsoft Entra ID (Azure AD) ---
    allowed_email_domain: str = "siliconpatterns.com"   # only this company domain may sign in
    jwt_secret: str = Field(                            # signs the app's session JWTs — set in prod!
        "dev-insecure-change-me", validation_alias=AliasChoices("SP_JWT_SECRET", "JWT_SECRET")
    )
    jwt_ttl_hours: int = 12
    # Dev-only: skip login and use a synthetic admin user, selectable via X-Dev-Role.
    # NEVER active when environment=production (see security._bypass_on), regardless
    # of this flag. Env: DEV_AUTH_BYPASS=true.
    dev_auth_bypass: bool = False
    admin_emails_raw: str = Field(                      # comma-separated; granted admin on first sign-in
        "", validation_alias=AliasChoices("SP_ADMIN_EMAILS", "ADMIN_EMAILS")
    )

    @property
    def admin_emails(self) -> set[str]:
        """Lower-cased set of emails auto-granted the admin role on their first sign-in."""
        return {e.strip().lower() for e in self.admin_emails_raw.split(",") if e.strip()}

    # --- Auth: initial administrator bootstrap ---
    # The one-time initial SUPER_ADMIN handoff: this email is auto-provisioned active
    # super_admin (skipping the pending queue) the first time it signs in via
    # Microsoft — see backend/services.py::login_with_microsoft. Once that User row
    # exists, later sign-ins never touch its role again (a deliberate demotion by
    # another admin can't be silently reversed by a later sign-in). Env:
    # SP_BOOTSTRAP_ADMIN_EMAIL.
    bootstrap_admin_email: str = Field(
        "admin@siliconpatterns.com", validation_alias=AliasChoices("SP_BOOTSTRAP_ADMIN_EMAIL")
    )

    # Entra App Registration (Single-Page Application platform, Authorization Code +
    # PKCE). The frontend obtains a Microsoft ID token via MSAL; the backend verifies
    # its signature locally against Microsoft's published JWKS for this tenant — no
    # network round trip to Microsoft per sign-in beyond key caching, and no client
    # secret needed for that verification (SPAs are a public client). The client
    # secret is accepted/stored for completeness (e.g. a future Graph API call) but
    # is not required by the current sign-in flow.
    microsoft_tenant_id: str = Field("", validation_alias=AliasChoices("MICROSOFT_TENANT_ID"))
    microsoft_client_id: str = Field("", validation_alias=AliasChoices("MICROSOFT_CLIENT_ID"))
    microsoft_client_secret: str = Field("", validation_alias=AliasChoices("MICROSOFT_CLIENT_SECRET"))
    microsoft_redirect_uri: str = Field(
        "http://localhost:5173", validation_alias=AliasChoices("MICROSOFT_REDIRECT_URI")
    )

    # --- Outreach module ---
    # 'mock' simulates email send/receive (no external creds — dev + demo default).
    # 'gmail' would use the real Gmail API (requires OAuth creds + a deployed origin).
    # Env: OUTREACH_MAIL_MODE.
    outreach_mail_mode: str = Field(
        "mock", validation_alias=AliasChoices("OUTREACH_MAIL_MODE", "SP_OUTREACH_MAIL_MODE")
    )
    # The shared sender address stamped on outbound mock mail.
    outreach_from_email: str = Field(
        "outreach@siliconpatterns.com", validation_alias=AliasChoices("OUTREACH_FROM_EMAIL")
    )

    # --- Gmail OAuth (Phase 4) ---
    # Provision these in Google Cloud Console → APIs & Services → Credentials.
    # Leave empty in dev/test (mock provider is used automatically).
    gmail_client_id: str = Field(
        "", validation_alias=AliasChoices("GMAIL_CLIENT_ID", "SP_GMAIL_CLIENT_ID")
    )
    gmail_client_secret: str = Field(
        "", validation_alias=AliasChoices("GMAIL_CLIENT_SECRET", "SP_GMAIL_CLIENT_SECRET")
    )
    # Must match an Authorised Redirect URI in the Google Cloud Console project.
    gmail_redirect_uri: str = Field(
        "http://localhost:8000/outreach/gmail/callback",
        validation_alias=AliasChoices("GMAIL_REDIRECT_URI", "SP_GMAIL_REDIRECT_URI"),
    )
    # Fernet key for token encryption at rest. Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Leave empty in dev/test (tokens stored unencrypted — fine for local SQLite).
    gmail_token_encryption_key: str = Field(
        "", validation_alias=AliasChoices("GMAIL_TOKEN_KEY", "SP_GMAIL_TOKEN_KEY")
    )

    # --- Integration Platform (Phase 10) ---
    # 'mock' simulates webhook/connector HTTP delivery deterministically (no network — dev
    # + test default). 'http' performs a real outbound POST via stdlib urllib.
    # Env: WEBHOOK_DELIVERY_MODE.
    webhook_delivery_mode: str = Field(
        "mock", validation_alias=AliasChoices("WEBHOOK_DELIVERY_MODE", "SP_WEBHOOK_DELIVERY_MODE")
    )

    # --- Standard Run scheduler ---
    # A background thread (backend/scheduler.py) fires the Standard Run (a full
    # `run all` — the same pipeline manual runs use) at each SP_SCHEDULE_TIMES slot,
    # server-local time. Disabled automatically under the test suite (conftest sets
    # SP_SCHEDULER_ENABLED=false) so no thread spins up per TestClient app.
    scheduler_enabled: bool = Field(
        True, validation_alias=AliasChoices("SP_SCHEDULER_ENABLED", "SCHEDULER_ENABLED")
    )
    # Comma-separated HH:MM slots (server-local). Configurable default, not hardcoded.
    schedule_times_raw: str = Field(
        "09:00,21:00", validation_alias=AliasChoices("SP_SCHEDULE_TIMES", "SCHEDULE_TIMES")
    )
    # A slot missed while the backend was down still fires when it comes back within
    # this many minutes of the slot (graceful recovery). 0 disables catch-up.
    schedule_grace_minutes: int = Field(
        180, validation_alias=AliasChoices("SP_SCHEDULE_GRACE_MINUTES")
    )

    @property
    def schedule_times(self) -> list[str]:
        """Normalized, de-duplicated, sorted 'HH:MM' slots."""
        out: list[str] = []
        for tok in self.schedule_times_raw.split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                h, m = tok.split(":")
                out.append(f"{int(h):02d}:{int(m):02d}")
            except (ValueError, TypeError):
                continue
        return sorted(dict.fromkeys(out))

    # --- Outlook / Microsoft Graph run notifications ---
    # LEGACY kill switch from the Microsoft-Graph notification module that
    # backend/notifications/ replaced. Only 'off' still has an effect, and only as a
    # backward-compatible alias for enable_notifications=False, so an environment that
    # already disabled notifications does not silently start sending again. Prefer
    # SP_ENABLE_NOTIFICATIONS for new deployments. Env: SP_NOTIFY_MODE.
    notify_mode: str = Field("auto", validation_alias=AliasChoices("SP_NOTIFY_MODE", "NOTIFY_MODE"))
    # Mailbox the summary is sent AS (Graph /users/{sender}/sendMail). Defaults to the
    # bootstrap admin. Requires the Entra app to hold the Mail.Send APPLICATION
    # permission (admin-consented) and this to be a real, licensed mailbox.
    notify_sender_email: str = Field(
        "", validation_alias=AliasChoices("SP_NOTIFY_SENDER_EMAIL", "NOTIFY_SENDER_EMAIL")
    )

    # --- Web crawling infrastructure (backend/crawling) ------------------------
    # Shared, vendor-neutral crawling used by Market Discovery, News Collection,
    # Career Intelligence and any future crawler. Firecrawl is ONE provider behind
    # the abstraction, not the abstraction itself: `crawl_provider` empty means
    # "choose by capability" (a JS-rendering provider when the caller needs one,
    # otherwise the cheap plain-HTTP one), so swapping vendors is a settings change.
    crawl_provider: str = Field(
        "", validation_alias=AliasChoices("SP_CRAWL_PROVIDER", "CRAWL_PROVIDER")
    )
    crawl_fallback_provider: str = Field(
        "http", validation_alias=AliasChoices("SP_CRAWL_FALLBACK_PROVIDER",
                                              "CRAWL_FALLBACK_PROVIDER")
    )
    crawl_timeout_seconds: int = Field(
        30, ge=1, le=600, validation_alias=AliasChoices("SP_CRAWL_TIMEOUT", "CRAWL_TIMEOUT")
    )
    crawl_concurrency: int = Field(
        4, ge=1, le=64, validation_alias=AliasChoices("SP_CRAWL_CONCURRENCY", "CRAWL_CONCURRENCY")
    )
    crawl_per_host_concurrency: int = Field(
        2, ge=1, le=32,
        validation_alias=AliasChoices("SP_CRAWL_PER_HOST_CONCURRENCY", "CRAWL_PER_HOST_CONCURRENCY"),
    )
    # Politeness toward the sites being crawled, not just the provider's quota.
    crawl_rate_limit_per_minute: int = Field(
        60, ge=0, validation_alias=AliasChoices("SP_CRAWL_RATE_LIMIT", "CRAWL_RATE_LIMIT")
    )
    crawl_per_host_rate_limit_per_minute: int = Field(
        30, ge=0,
        validation_alias=AliasChoices("SP_CRAWL_PER_HOST_RATE_LIMIT", "CRAWL_PER_HOST_RATE_LIMIT"),
    )
    # 0 disables caching entirely (every request hits the provider).
    crawl_cache_ttl_seconds: int = Field(
        3600, ge=0, validation_alias=AliasChoices("SP_CRAWL_CACHE_TTL", "CRAWL_CACHE_TTL")
    )
    crawl_cache_max_entries: int = Field(
        512, ge=1, validation_alias=AliasChoices("SP_CRAWL_CACHE_MAX_ENTRIES",
                                                 "CRAWL_CACHE_MAX_ENTRIES")
    )
    crawl_max_depth: int = Field(
        1, ge=1, le=10, validation_alias=AliasChoices("SP_CRAWL_MAX_DEPTH", "CRAWL_MAX_DEPTH")
    )
    crawl_max_pages: int = Field(
        20, ge=1, le=1000, validation_alias=AliasChoices("SP_CRAWL_MAX_PAGES", "CRAWL_MAX_PAGES")
    )
    crawl_retry_count: int = Field(
        3, ge=1, le=10, validation_alias=AliasChoices("SP_CRAWL_RETRY_COUNT", "CRAWL_RETRY_COUNT")
    )
    crawl_retry_backoff_seconds: float = Field(
        1.0, ge=0.0, le=60.0,
        validation_alias=AliasChoices("SP_CRAWL_RETRY_BACKOFF", "CRAWL_RETRY_BACKOFF"),
    )
    crawl_retry_max_backoff_seconds: float = Field(
        30.0, ge=0.0, le=300.0,
        validation_alias=AliasChoices("SP_CRAWL_RETRY_MAX_BACKOFF", "CRAWL_RETRY_MAX_BACKOFF"),
    )
    crawl_user_agent: str = Field(
        "SiliconPatternsBot/1.0 (+https://siliconpatterns.com/bot; platform crawler)",
        validation_alias=AliasChoices("SP_CRAWL_USER_AGENT", "CRAWL_USER_AGENT"),
    )
    # --- Firecrawl provider credentials (one provider among several) -----------
    firecrawl_api_key: str = Field(
        "", validation_alias=AliasChoices("SP_FIRECRAWL_API_KEY", "FIRECRAWL_API_KEY")
    )
    firecrawl_base_url: str = Field(
        "https://api.firecrawl.dev",
        validation_alias=AliasChoices("SP_FIRECRAWL_BASE_URL", "FIRECRAWL_BASE_URL"),
    )

    # --- Market Discovery Engine (backend/market_discovery) --------------------
    # The engine owns ALL discovery business logic; sources are data providers only.
    # Nothing runs until a source is both registered and named here — these providers
    # cost money and have rate limits, so enablement is explicit rather than implicit.
    # Comma-separated source names, or "*" for every registered source (dev only).
    discovery_enabled: bool = Field(
        True, validation_alias=AliasChoices("SP_DISCOVERY_ENABLED", "DISCOVERY_ENABLED")
    )
    discovery_sources_raw: str = Field(
        "", validation_alias=AliasChoices("SP_DISCOVERY_SOURCES", "DISCOVERY_SOURCES")
    )
    # Max candidates accepted from ONE source in one run — bounds a runaway provider
    # so it cannot stall the pipeline or flood the review queue. 0 = unbounded.
    discovery_source_limit: int = Field(
        500, ge=0, validation_alias=AliasChoices("SP_DISCOVERY_SOURCE_LIMIT", "DISCOVERY_SOURCE_LIMIT")
    )
    # Sources fetched in parallel. They are network-bound and independent, so a small
    # thread pool is the right shape; 1 keeps execution strictly serial (and ordered).
    discovery_concurrency: int = Field(
        4, ge=1, le=32, validation_alias=AliasChoices("SP_DISCOVERY_CONCURRENCY", "DISCOVERY_CONCURRENCY")
    )
    # Attempts per source per run (1 = no retry), and the wait between them.
    discovery_retry_count: int = Field(
        2, ge=1, le=10, validation_alias=AliasChoices("SP_DISCOVERY_RETRY_COUNT", "DISCOVERY_RETRY_COUNT")
    )
    discovery_retry_backoff_seconds: float = Field(
        2.0, ge=0.0, le=60.0,
        validation_alias=AliasChoices("SP_DISCOVERY_RETRY_BACKOFF", "DISCOVERY_RETRY_BACKOFF"),
    )
    # Global politeness ceiling applied per source by the engine, so a provider's
    # limits are honoured even when the connector itself does not implement them.
    discovery_rate_limit_per_minute: int = Field(
        60, ge=0, validation_alias=AliasChoices("SP_DISCOVERY_RATE_LIMIT", "DISCOVERY_RATE_LIMIT")
    )
    # Below this confidence a candidate is kept for review but never promoted.
    discovery_confidence_threshold: float = Field(
        0.45, ge=0.0, le=1.0,
        validation_alias=AliasChoices("SP_DISCOVERY_CONFIDENCE_THRESHOLD",
                                      "DISCOVERY_CONFIDENCE_THRESHOLD"),
    )
    # Wall-clock budget for one source's fetch, so a hung provider cannot hold the
    # scheduled run open indefinitely.
    discovery_source_timeout_seconds: int = Field(
        300, ge=1,
        validation_alias=AliasChoices("SP_DISCOVERY_SOURCE_TIMEOUT", "DISCOVERY_SOURCE_TIMEOUT"),
    )

    @property
    def discovery_sources(self) -> list[str]:
        """Enabled source names, normalized and de-duplicated."""
        raw = (self.discovery_sources_raw or "").strip()
        if not raw:
            return []
        seen: list[str] = []
        for part in raw.split(","):
            name = part.strip().lower()
            if name and name not in seen:
                seen.append(name)
        return seen

    # --- Wellfound connector (backend/market_discovery/sources/wellfound) ------
    # A data source only: it crawls PUBLIC startup listings through the shared crawl
    # service and returns candidates. It runs only when named in DISCOVERY_SOURCES.
    # Defaults are conservative because the target is a third party's infrastructure.
    wellfound_base_url: str = Field(
        "https://wellfound.com",
        validation_alias=AliasChoices("SP_WELLFOUND_BASE_URL", "WELLFOUND_BASE_URL"),
    )
    # Comma-separated listing paths; empty uses the built-in public defaults. Every
    # default is outside wellfound.com/robots.txt's Disallow set.
    wellfound_listing_paths_raw: str = Field(
        "", validation_alias=AliasChoices("SP_WELLFOUND_LISTING_PATHS", "WELLFOUND_LISTING_PATHS"),
    )
    # Opaque query string appended to a listing URL (e.g. "stage=seed"), so a change
    # to Wellfound's filter syntax needs configuration, not code.
    wellfound_listing_query: str = Field(
        "", validation_alias=AliasChoices("SP_WELLFOUND_LISTING_QUERY", "WELLFOUND_LISTING_QUERY"),
    )
    wellfound_max_pages: int = Field(
        3, ge=1, le=100,
        validation_alias=AliasChoices("SP_WELLFOUND_MAX_PAGES", "WELLFOUND_MAX_PAGES"),
    )
    # The expensive bound: each company is one crawl request against a third party.
    wellfound_max_companies: int = Field(
        50, ge=1, le=5000,
        validation_alias=AliasChoices("SP_WELLFOUND_MAX_COMPANIES", "WELLFOUND_MAX_COMPANIES"),
    )
    wellfound_crawl_depth: int = Field(
        1, ge=1, le=5,
        validation_alias=AliasChoices("SP_WELLFOUND_CRAWL_DEPTH", "WELLFOUND_CRAWL_DEPTH"),
    )
    # Off makes a run cheap and shallow (listing data only); on fetches each company
    # page for detail.
    wellfound_fetch_company_pages: bool = Field(
        True, validation_alias=AliasChoices("SP_WELLFOUND_FETCH_COMPANY_PAGES",
                                            "WELLFOUND_FETCH_COMPANY_PAGES"),
    )
    # Skip companies the platform already stored, so a nightly run costs far less
    # than the first one.
    wellfound_incremental: bool = Field(
        True, validation_alias=AliasChoices("SP_WELLFOUND_INCREMENTAL", "WELLFOUND_INCREMENTAL"),
    )

    # --- NVIDIA Inception connector -------------------------------------------
    # A data source only: it enumerates NVIDIA's PUBLIC case studies through the
    # shared crawl service. Runs only when named in DISCOVERY_SOURCES.
    # Pages are server-rendered, so no JS-rendering provider is needed.
    nvidia_inception_base_url: str = Field(
        "https://www.nvidia.com",
        validation_alias=AliasChoices("SP_NVIDIA_INCEPTION_BASE_URL", "NVIDIA_INCEPTION_BASE_URL"),
    )
    # The locale sitemap. Preferred over ?page= pagination, which nvidia.com's
    # robots.txt disallows outright.
    nvidia_inception_sitemap_path: str = Field(
        "/en-us/en-us.sitemap.xml",
        validation_alias=AliasChoices("SP_NVIDIA_INCEPTION_SITEMAP_PATH",
                                      "NVIDIA_INCEPTION_SITEMAP_PATH"),
    )
    nvidia_inception_use_sitemap: bool = Field(
        True, validation_alias=AliasChoices("SP_NVIDIA_INCEPTION_USE_SITEMAP",
                                            "NVIDIA_INCEPTION_USE_SITEMAP"),
    )
    nvidia_inception_index_paths_raw: str = Field(
        "", validation_alias=AliasChoices("SP_NVIDIA_INCEPTION_INDEX_PATHS",
                                          "NVIDIA_INCEPTION_INDEX_PATHS"),
    )
    nvidia_inception_max_pages: int = Field(
        2, ge=1, le=50,
        validation_alias=AliasChoices("SP_NVIDIA_INCEPTION_MAX_PAGES", "NVIDIA_INCEPTION_MAX_PAGES"),
    )
    # The expensive bound: each company is one crawl request against nvidia.com.
    nvidia_inception_max_companies: int = Field(
        50, ge=1, le=5000,
        validation_alias=AliasChoices("SP_NVIDIA_INCEPTION_MAX_COMPANIES",
                                      "NVIDIA_INCEPTION_MAX_COMPANIES"),
    )
    nvidia_inception_crawl_depth: int = Field(
        1, ge=1, le=5,
        validation_alias=AliasChoices("SP_NVIDIA_INCEPTION_CRAWL_DEPTH",
                                      "NVIDIA_INCEPTION_CRAWL_DEPTH"),
    )
    nvidia_inception_fetch_company_pages: bool = Field(
        True, validation_alias=AliasChoices("SP_NVIDIA_INCEPTION_FETCH_COMPANY_PAGES",
                                            "NVIDIA_INCEPTION_FETCH_COMPANY_PAGES"),
    )
    nvidia_inception_incremental: bool = Field(
        True, validation_alias=AliasChoices("SP_NVIDIA_INCEPTION_INCREMENTAL",
                                            "NVIDIA_INCEPTION_INCREMENTAL"),
    )

    # --- Market Intelligence Layer (backend/market_intelligence) ---------------
    # Interprets discovery candidates: classification, technologies, market signals,
    # opportunity priority and the explanation behind each. Deterministic rules only
    # — no ML, no LLM, no external AI service, no network call. Runs in-process as a
    # pipeline stage immediately after the Market Discovery Engine.
    #
    # EVERY business decision below is configuration. Nothing here is a credential,
    # so the layer is safe to leave on: with no discovery candidates it is a no-op.
    intelligence_enabled: bool = Field(
        True, validation_alias=AliasChoices("SP_INTELLIGENCE_ENABLED", "INTELLIGENCE_ENABLED")
    )
    # Which built-in rule pack defines the vocabulary. "semiconductor" ships with the
    # platform; an overlay below can extend or replace any of its rules.
    intelligence_rule_pack: str = Field(
        "semiconductor",
        validation_alias=AliasChoices("SP_INTELLIGENCE_RULE_PACK", "INTELLIGENCE_RULE_PACK"),
    )
    # Path to a JSON rule-pack overlay (adds/replaces rules, thresholds, weights).
    # Unreadable or malformed degrades to the built-in pack with a loud log — shipped
    # rules always beat no intelligence at all.
    intelligence_rules_path: str = Field(
        "", validation_alias=AliasChoices("SP_INTELLIGENCE_RULES_PATH",
                                          "INTELLIGENCE_RULES_PATH"),
    )
    # Comma-separated rule keys to switch off / back on without editing a pack.
    intelligence_disabled_rules_raw: str = Field(
        "", validation_alias=AliasChoices("SP_INTELLIGENCE_DISABLED_RULES",
                                          "INTELLIGENCE_DISABLED_RULES"),
    )
    intelligence_enabled_rules_raw: str = Field(
        "", validation_alias=AliasChoices("SP_INTELLIGENCE_ENABLED_RULES",
                                          "INTELLIGENCE_ENABLED_RULES"),
    )
    # JSON objects: extra vocabulary per rule key, threshold and weight overrides.
    # e.g. {"asic": ["custom asic"]} / {"technology_target": 4} / {"funding_activity": 2}
    intelligence_extra_terms_raw: str = Field(
        "", validation_alias=AliasChoices("SP_INTELLIGENCE_EXTRA_TERMS",
                                          "INTELLIGENCE_EXTRA_TERMS"),
    )
    intelligence_thresholds_raw: str = Field(
        "", validation_alias=AliasChoices("SP_INTELLIGENCE_THRESHOLDS",
                                          "INTELLIGENCE_THRESHOLDS"),
    )
    intelligence_weights_raw: str = Field(
        "", validation_alias=AliasChoices("SP_INTELLIGENCE_WEIGHTS", "INTELLIGENCE_WEIGHTS"),
    )
    # Priority band floors, checked most-urgent first. These win over the same keys
    # supplied through SP_INTELLIGENCE_THRESHOLDS.
    intelligence_priority_critical: float = Field(
        0.75, ge=0.0, le=1.0,
        validation_alias=AliasChoices("SP_INTELLIGENCE_PRIORITY_CRITICAL",
                                      "INTELLIGENCE_PRIORITY_CRITICAL"),
    )
    intelligence_priority_high: float = Field(
        0.55, ge=0.0, le=1.0,
        validation_alias=AliasChoices("SP_INTELLIGENCE_PRIORITY_HIGH",
                                      "INTELLIGENCE_PRIORITY_HIGH"),
    )
    intelligence_priority_medium: float = Field(
        0.35, ge=0.0, le=1.0,
        validation_alias=AliasChoices("SP_INTELLIGENCE_PRIORITY_MEDIUM",
                                      "INTELLIGENCE_PRIORITY_MEDIUM"),
    )
    # A detected signal below this confidence is not reported. It still counts as a
    # prerequisite for derived rules, so raising this cannot silently break a rule.
    intelligence_signal_min_confidence: float = Field(
        0.3, ge=0.0, le=1.0,
        validation_alias=AliasChoices("SP_INTELLIGENCE_SIGNAL_MIN_CONFIDENCE",
                                      "INTELLIGENCE_SIGNAL_MIN_CONFIDENCE"),
    )
    # Candidates interpreted in one pass, and the ceiling read per run (0 = no cap).
    intelligence_batch_size: int = Field(
        200, ge=1, le=10000,
        validation_alias=AliasChoices("SP_INTELLIGENCE_BATCH_SIZE", "INTELLIGENCE_BATCH_SIZE"),
    )
    intelligence_max_candidates: int = Field(
        2000, ge=0,
        validation_alias=AliasChoices("SP_INTELLIGENCE_MAX_CANDIDATES",
                                      "INTELLIGENCE_MAX_CANDIDATES"),
    )
    # Evaluation is pure CPU string matching, so >1 buys nothing today; the pool is
    # there for the enrichment seam, where future work will be network-bound. Output
    # order is fixed regardless, so this can never change a result.
    intelligence_concurrency: int = Field(
        1, ge=1, le=32,
        validation_alias=AliasChoices("SP_INTELLIGENCE_CONCURRENCY",
                                      "INTELLIGENCE_CONCURRENCY"),
    )
    # Re-interpret every candidate instead of only those seen since their last
    # evaluation. The way to roll a rule change over existing data.
    intelligence_reprocess_all: bool = Field(
        False, validation_alias=AliasChoices("SP_INTELLIGENCE_REPROCESS_ALL",
                                             "INTELLIGENCE_REPROCESS_ALL"),
    )
    intelligence_log_level: str = Field(
        "", validation_alias=AliasChoices("SP_INTELLIGENCE_LOG_LEVEL",
                                          "INTELLIGENCE_LOG_LEVEL"),
    )

    # --- Startup schema migrations ---------------------------------------------
    # Apply every pending master_db/migrations/*.sql before the API serves its first
    # request, so a deploy never needs a manual migration step. Postgres only (SQLite
    # dev builds its schema from the ORM). A failure ABORTS startup — the process must
    # not serve traffic on a schema it does not match. Concurrent replicas are
    # serialized by a Postgres advisory lock, so this is safe with numReplicas > 1.
    # Set false to return to running scripts/apply_migrations.py out-of-band.
    auto_migrate: bool = Field(
        True, validation_alias=AliasChoices("SP_AUTO_MIGRATE", "AUTO_MIGRATE")
    )

    # --- Notification framework (backend/notifications) ------------------------
    # Channel-agnostic delivery after a scheduled run. The scheduler emits a payload
    # to the notification service, which renders it and hands it to a registered
    # provider — it never talks to a mail server. Adding Teams/Slack/webhook later is
    # a new provider plus a change to `notification_provider`, with no scheduler edit.
    #
    # Master switch. False => nothing is delivered on any channel (recorded 'skipped').
    enable_notifications: bool = Field(
        True, validation_alias=AliasChoices("SP_ENABLE_NOTIFICATIONS", "ENABLE_NOTIFICATIONS")
    )
    # Registered provider name: 'email' | 'gmail' today (both the SMTP provider).
    notification_provider: str = Field(
        "gmail", validation_alias=AliasChoices("SP_NOTIFICATION_PROVIDER", "NOTIFICATION_PROVIDER",
                                               "EMAIL_PROVIDER")
    )
    # Total SMTP attempts per notification (1 = no retry). No backoff between tries:
    # a scheduled run must not be held open, and SMTP failures here are almost always
    # configuration, which waiting does not fix.
    notification_retry_count: int = Field(
        3, ge=1, le=10,
        validation_alias=AliasChoices("SP_NOTIFICATION_RETRY_COUNT", "NOTIFICATION_RETRY_COUNT"),
    )
    # Target of the "Open Silicon Patterns" button. Empty hides the button.
    frontend_url: str = Field("", validation_alias=AliasChoices("SP_FRONTEND_URL", "FRONTEND_URL"))
    # Branding used in the subject line, header and footer.
    brand_name: str = Field("Silicon Patterns", validation_alias=AliasChoices("SP_BRAND_NAME", "BRAND_NAME"))
    # Absolute URL to a logo. Empty renders a built-in monogram instead — email
    # clients cannot load a relative path, so a bad value degrades, never breaks.
    brand_logo_url: str = Field("", validation_alias=AliasChoices("SP_BRAND_LOGO_URL", "BRAND_LOGO_URL"))

    # --- SMTP / email sender identity ------------------------------------------
    # Gmail requires an APP PASSWORD (not the account password) once 2FA is on.
    # Any RFC-compliant SMTP server works by changing host/port — nothing here is
    # Gmail-specific beyond the defaults.
    email_from: str = Field("", validation_alias=AliasChoices("SP_EMAIL_FROM", "EMAIL_FROM"))
    email_display_name: str = Field(
        "Silicon Patterns", validation_alias=AliasChoices("SP_EMAIL_DISPLAY_NAME", "EMAIL_DISPLAY_NAME")
    )
    smtp_host: str = Field("smtp.gmail.com", validation_alias=AliasChoices("SP_SMTP_HOST", "SMTP_HOST"))
    smtp_port: int = Field(587, validation_alias=AliasChoices("SP_SMTP_PORT", "SMTP_PORT"))
    smtp_username: str = Field("", validation_alias=AliasChoices("SP_SMTP_USERNAME", "SMTP_USERNAME"))
    smtp_password: str = Field("", validation_alias=AliasChoices("SP_SMTP_PASSWORD", "SMTP_PASSWORD"))
    smtp_use_starttls: bool = Field(
        True, validation_alias=AliasChoices("SP_SMTP_USE_STARTTLS", "SMTP_USE_STARTTLS")
    )
    # Implicit TLS (port 465). Mutually exclusive with STARTTLS; when true it wins.
    smtp_use_ssl: bool = Field(False, validation_alias=AliasChoices("SP_SMTP_USE_SSL", "SMTP_USE_SSL"))

    # --- Machine Learning Foundation -------------------------------------------
    # Feature store / feedback / embeddings / dataset infrastructure. NONE of this is
    # wired into the Standard Run or the scheduler (they stay untouched) — feature
    # generation is incremental + cached and runs on demand (CLI/API) so nightly
    # retraining never slows a scheduled pipeline run.
    ml_enabled: bool = Field(True, validation_alias=AliasChoices("SP_ML_ENABLED", "ML_ENABLED"))
    # Bumping the feature version invalidates the feature cache (a new row set is built).
    ml_feature_version: str = Field(
        "fs-1", validation_alias=AliasChoices("SP_ML_FEATURE_VERSION", "ML_FEATURE_VERSION")
    )
    # Embedding backend: "hash" (deterministic, zero-dependency default — keeps tests +
    # scheduled runs fast) or "sentence-transformers" (loads the model if installed;
    # transparently upgrades the same cache). Model name is recorded on each cached row.
    ml_embedding_backend: str = Field(
        "hash", validation_alias=AliasChoices("SP_ML_EMBEDDING_BACKEND", "ML_EMBEDDING_BACKEND")
    )
    ml_embedding_model: str = Field(
        "all-MiniLM-L6-v2", validation_alias=AliasChoices("SP_ML_EMBEDDING_MODEL", "ML_EMBEDDING_MODEL")
    )
    ml_embedding_dim: int = Field(384, validation_alias=AliasChoices("SP_ML_EMBEDDING_DIM", "ML_EMBEDDING_DIM"))
    # Exponential time-decay half-lives (days) per opportunity category. Independent so
    # a layoff signal fades faster than a funding round. Configurable via env.
    ml_decay_half_life_layoffs: int = Field(30, validation_alias=AliasChoices("SP_ML_DECAY_LAYOFFS"))
    ml_decay_half_life_hiring: int = Field(45, validation_alias=AliasChoices("SP_ML_DECAY_HIRING"))
    ml_decay_half_life_projects: int = Field(90, validation_alias=AliasChoices("SP_ML_DECAY_PROJECTS"))
    ml_decay_half_life_funding: int = Field(120, validation_alias=AliasChoices("SP_ML_DECAY_FUNDING"))
    ml_decay_half_life_default: int = Field(60, validation_alias=AliasChoices("SP_ML_DECAY_DEFAULT"))
    # Training dataset lookback window (clamped to 30..90 by the builder).
    ml_training_window_days: int = Field(
        60, validation_alias=AliasChoices("SP_ML_TRAINING_WINDOW_DAYS", "ML_TRAINING_WINDOW_DAYS")
    )
    # Model training / promotion. The registered model name; the metric a promotion is
    # judged on; and the minimum quality gates a candidate must clear (AND outperform the
    # current production model) before it can be promoted. Promotion is NEVER automatic.
    ml_model_name: str = Field("lead_recommender", validation_alias=AliasChoices("SP_ML_MODEL_NAME"))
    ml_primary_metric: str = Field("pr_auc", validation_alias=AliasChoices("SP_ML_PRIMARY_METRIC"))
    ml_promote_min_roc_auc: float = Field(0.60, validation_alias=AliasChoices("SP_ML_PROMOTE_MIN_ROC_AUC"))
    ml_promote_min_pr_auc: float = Field(0.50, validation_alias=AliasChoices("SP_ML_PROMOTE_MIN_PR_AUC"))
    ml_val_fraction: float = Field(0.25, validation_alias=AliasChoices("SP_ML_VAL_FRACTION"))

    def promote_thresholds(self) -> dict[str, float]:
        return {"roc_auc": self.ml_promote_min_roc_auc, "pr_auc": self.ml_promote_min_pr_auc}

    def decay_half_lives(self) -> dict[str, int]:
        """Per-category half-lives (days) for the ML time-decay feature."""
        return {
            "layoffs": self.ml_decay_half_life_layoffs,
            "hiring": self.ml_decay_half_life_hiring,
            "projects": self.ml_decay_half_life_projects,
            "funding": self.ml_decay_half_life_funding,
            "default": self.ml_decay_half_life_default,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
