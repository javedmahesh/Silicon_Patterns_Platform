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
    # After each SCHEDULED run, email an execution summary to every ACTIVE user via
    # Microsoft Graph sendMail (client-credentials, reusing the Entra app + secret).
    # Mode: 'auto' -> real Graph send when a client secret AND sender are configured,
    # else log-only; 'graph' forces real; 'off' disables. Notification failures never
    # fail the pipeline. Env: SP_NOTIFY_MODE.
    notify_mode: str = Field("auto", validation_alias=AliasChoices("SP_NOTIFY_MODE", "NOTIFY_MODE"))
    # Mailbox the summary is sent AS (Graph /users/{sender}/sendMail). Defaults to the
    # bootstrap admin. Requires the Entra app to hold the Mail.Send APPLICATION
    # permission (admin-consented) and this to be a real, licensed mailbox.
    notify_sender_email: str = Field(
        "", validation_alias=AliasChoices("SP_NOTIFY_SENDER_EMAIL", "NOTIFY_SENDER_EMAIL")
    )

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
