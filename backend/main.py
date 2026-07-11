"""FastAPI application factory + ASGI entrypoint.

    python -m backend.main          # dev server (uvicorn) on :8000
    uvicorn backend.main:app        # production server

OpenAPI/Swagger docs at /docs, ReDoc at /redoc, raw schema at /openapi.json.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from backend.config import Settings, get_settings
from backend.database import Database
from backend.logging_config import configure_logging
from backend.rate_limiter import InMemoryRateLimiter
from backend.routers import (
    admin,
    admin_governance,
    ai,
    alerts,
    analytics,
    assignments,
    auth,
    bi,
    campaigns,
    companies,
    crm,
    cs,
    custom_objects,
    deals,
    decision_makers,
    demand_signals,
    health,
    integrations,
    leadership_signals,
    leads,
    ml as ml_router,
    opportunities,
    outreach,
    pipeline,
    platform,
    review,
    reviews,
    revops,
    scheduler as scheduler_router,
    search,
    team,
    workflows,
)
from backend.security import _bypass_on, require_principal

logger = logging.getLogger("backend.api")

_TAGS_METADATA = [
    {"name": "health", "description": "Liveness and database connectivity."},
    {"name": "companies", "description": "Company list/search and the unified profile."},
    {"name": "leads", "description": "Lead-scored, ranked prospects."},
    {"name": "opportunities", "description": "Blog Crawler market events."},
    {"name": "demand-signals", "description": "Career Scraper hiring-demand rollups."},
    {"name": "decision-makers", "description": "LinkedIn decision makers."},
    {"name": "analytics", "description": "Platform-wide rollups + engine-coverage matrix."},
    {"name": "pipeline", "description": "Orchestrator run history + per-component freshness."},
    {"name": "review-queue", "description": "Resolve/merge/approve stub + unresolved companies."},
]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        # Hard fail-closed: refuse to start at all in production with no strong JWT
        # secret configured. This is a startup abort (raised before the DB engine or
        # any route can serve a request), not a log line — closes the fail-open gap
        # where a misconfigured prod deploy silently served an open API under a
        # synthetic admin. Outside production (the default), behavior is unchanged —
        # see security._bypass_on. The app JWT secret is what's checked here; the
        # Microsoft Entra credential check right below covers the identity-provider side.
        if settings.is_production and (
            settings.jwt_secret == "dev-insecure-change-me" or len(settings.jwt_secret) < 32
        ):
            raise RuntimeError(
                "Refusing to start: ENVIRONMENT=production requires SP_JWT_SECRET to be "
                "set to a strong (32+ char) value. There is no implicit auth bypass in production."
            )
        # Same fail-closed principle, for the identity provider itself: production with
        # no Microsoft Entra app configured means literally no one could ever sign in
        # (the dev bypass is unconditionally off there — security._bypass_on).
        if settings.is_production and not (settings.microsoft_tenant_id and settings.microsoft_client_id):
            raise RuntimeError(
                "Refusing to start: ENVIRONMENT=production requires MICROSOFT_TENANT_ID and "
                "MICROSOFT_CLIENT_ID to be configured. There is no other sign-in path in production."
            )
        app.state.db = Database(settings)
        logger.info("API startup: %s v%s", settings.app_name, settings.app_version)
        # Production safety: the dev auth-bypass must never be active in prod
        # (unconditionally forced off there — see security._bypass_on); flag loudly if
        # it is on outside prod so a misconfigured deploy is obvious in the logs.
        bypass_on = _bypass_on(settings)
        if bypass_on:
            logger.critical(
                "DEV AUTH BYPASS IS ACTIVE — the API is OPEN (synthetic admin). This is for "
                "local dev/tests ONLY. Leave DEV_AUTH_BYPASS unset in production."
            )
        # Initial administrator bootstrap now happens lazily, on the configured
        # bootstrap email's first Microsoft sign-in (see
        # backend/services.py::login_with_microsoft) rather than at startup — there's
        # no password-holding account to proactively create anymore.
        # Phase 13 deployment-readiness check: surfaced in the logs on every boot (not
        # fatal — the dev bypass check above already covers the one hard-blocking case),
        # so a misconfigured prod deploy is visible immediately without a separate call.
        from backend.platform_service import production_readiness
        with app.state.db.sessionmaker() as _readiness_session:
            readiness = production_readiness(settings, _readiness_session)
        if not readiness["ready"]:
            failing = [c for c in readiness["critical_checks"] if not readiness["checks"][c]]
            logger.warning("Production readiness check: NOT READY — failing: %s", failing)
        else:
            logger.info("Production readiness check: ready")
        # Seed system labels idempotently on each startup
        with app.state.db.sessionmaker() as _s:
            from backend.outreach_repo import seed_system_labels
            seed_system_labels(_s)
            _s.commit()
        # Background webhook delivery worker (Phase 10 hardening): outbound HTTP calls in
        # webhook_delivery_mode='http' run off the request thread. No-op overhead in the
        # default 'mock' mode — see integration_service._dispatch_delivery.
        from backend.integration_service import start_webhook_worker, stop_webhook_worker
        start_webhook_worker(app.state.db.sessionmaker, settings)
        # Standard Run scheduler (Phase: Standard Scheduled Runs): fires the full
        # pipeline at each SP_SCHEDULE_TIMES slot. Disabled under the test suite
        # (conftest sets SP_SCHEDULER_ENABLED=false) and whenever scheduler_enabled
        # is off; start() itself is a no-op in that case.
        from backend.scheduler import PipelineScheduler
        app.state.scheduler = PipelineScheduler(app.state.db.sessionmaker, settings)
        app.state.scheduler.start()
        try:
            yield
        finally:
            app.state.scheduler.stop()
            stop_webhook_worker()
            app.state.db.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        openapi_tags=_TAGS_METADATA,
        lifespan=lifespan,
    )
    app.state.settings = settings

    # Credentials cannot be combined with a "*" origin per the CORS spec.
    allow_credentials = "*" not in settings.cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Optional rate limit (per client IP), disabled when rate_limit_per_minute == 0.
    # /health is always exempt (load-balancer probe). Backed by an InMemoryRateLimiter
    # (backend.rate_limiter) — see that module for the distributed-backend extension point.
    rate_limit = settings.rate_limit_per_minute
    _limiter = InMemoryRateLimiter()

    @app.middleware("http")
    async def rate_limiter(request: Request, call_next):
        if rate_limit > 0 and request.url.path != "/health":
            ip = request.client.host if request.client else "anonymous"
            allowed, retry_after = _limiter.check(ip, limit=rate_limit, window_seconds=60)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                "client": request.client.host if request.client else "",
            },
        )
        return response

    # Open: the health probe + the SSO login exchange. Everything else requires a
    # principal — a signed-in user's app JWT, or the service API key (require_principal).
    app.include_router(health.router)
    app.include_router(auth.router)
    # Admin/CRM routers enforce their own per-route role gates (require_admin / require_manager
    # / get_current_user), so they're registered without the blanket principal dependency.
    app.include_router(admin.router)
    app.include_router(assignments.router)
    app.include_router(crm.router)
    app.include_router(reviews.router)
    # Outreach: every route depends on get_current_user and enforces its own role
    # gates in the service layer (members draft; admin/manager approve/manage).
    app.include_router(outreach.router)
    # Enterprise CRM: campaigns, sequences, enrollments (same auth model as outreach).
    app.include_router(campaigns.router)
    app.include_router(campaigns.sequences_router)
    app.include_router(campaigns.enrollments_router)
    # Enterprise CRM Phase 2: pipelines (kanban/forecast/analytics) and deals.
    app.include_router(deals.pipelines_router)
    app.include_router(deals.deals_router)
    # Enterprise CRM Phase 3: team collaboration, work queue, comments, notifications.
    app.include_router(team.router)
    # Enterprise CRM Phase 4: customer success & account management.
    app.include_router(cs.router)
    # Enterprise CRM Phase 5: revenue operations, forecasting & executive analytics.
    app.include_router(revops.router)
    # Enterprise CRM Phase 6: workflow automation & business process engine.
    app.include_router(workflows.router)
    # Enterprise CRM Phase 7: custom objects, forms & no-code platform.
    app.include_router(custom_objects.router)
    # Enterprise CRM Phase 8: AI intelligence & copilot (deterministic, no LLM).
    app.include_router(ai.router)
    # Enterprise CRM Phase 9: enterprise administration, security & compliance.
    app.include_router(admin_governance.router)
    # Enterprise CRM Phase 10: integration platform & developer ecosystem.
    app.include_router(integrations.router)
    # Enterprise CRM Phase 11: enterprise search & knowledge platform.
    app.include_router(search.search_router)
    app.include_router(search.knowledge_router)
    # Enterprise CRM Phase 12: data warehouse & advanced business intelligence.
    app.include_router(bi.router)
    # Enterprise CRM Phase 13: production deployment, authentication & platform hardening.
    app.include_router(platform.router)
    # Standard Scheduled Runs: scheduler status + run history + run-now.
    app.include_router(scheduler_router.router)
    # Machine Learning Foundation: feedback capture + feature store + registries.
    app.include_router(ml_router.router)
    guarded = (companies, leads, opportunities, demand_signals, decision_makers,
               leadership_signals, analytics, pipeline, review, alerts)
    for module in guarded:
        app.include_router(module.router, dependencies=[Depends(require_principal)])

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False, log_config=None)
