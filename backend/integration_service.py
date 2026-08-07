"""Enterprise CRM Phase 10: Integration Platform & Developer Ecosystem.

Webhook/connector "delivery" is pluggable exactly like the existing outreach mail
provider (backend/email_providers): a deterministic 'mock' mode (default, no network —
dev/test) and a real 'http' mode using stdlib urllib (no new dependency). Toggle via
Settings.webhook_delivery_mode. See config.py.

Event Bus: publish_event() is the single entry point. It is wired into
workflow_service.fire_event() (reusing the existing WORKFLOW_TRIGGER_EVENTS vocabulary
verbatim as event_type — the concrete "reuse existing workflow triggers" the Phase 10
spec calls for), which gives automatic CRM/Workflow/Customer category coverage. Revenue/
AI/Administration events are reachable through the Developer API (POST
/integrations/events/publish) for on-demand publishing rather than instrumenting every
mutation point across Phase 5/8/9 (same proportional-effort scope call as Phase 9's
audit-logging integration).

Plugins carry no arbitrary executable code — "executing" a hook is a recorded,
permission-checked dispatch (plugin_executions row), not code execution. A real plugin
sandbox/runtime is a distinct, much larger security project.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import queue as queue_mod
import secrets
import threading
import time
import urllib.error
import urllib.request

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import admin_repo
from backend import integration_repo as repo
from backend.config import get_settings
from backend.tick_lock import single_flight
from backend.schemas import (
    ConnectorCreate,
    ConnectorHealthOut,
    ConnectorOut,
    ConnectorPatch,
    ConnectorRunOut,
    IntegrationAnalyticsOut,
    IntegrationCreate,
    IntegrationDashboardOut,
    IntegrationEventOut,
    IntegrationOut,
    IntegrationPatch,
    OAuthCredentialCreate,
    OAuthCredentialCreatedOut,
    OAuthCredentialOut,
    Page,
    PluginCreate,
    PluginExecutionOut,
    PluginOut,
    PluginPatch,
    WebhookCreate,
    WebhookCreatedOut,
    WebhookDeliveryOut,
    WebhookOut,
    WebhookPatch,
)
from config.enums import (
    CONNECTOR_TYPES,
    EVENT_BUS_CATEGORIES,
    PLUGIN_HOOK_TYPES,
)

logger = logging.getLogger("backend.integrations")

from backend.timeutil import utc as _utc, utcnow as _utcnow


def _is_manager(user) -> bool:
    return getattr(user, "role", "member") in ("admin", "manager")


def _require_manager(user) -> None:
    if not _is_manager(user):
        raise HTTPException(403, "manager or admin required")


def _audit(session: Session, *, category: str, action: str, actor, entity_type: str = "", entity_id="", detail: dict | None = None) -> None:
    """Cross-cutting audit trail, reusing the existing audit_events table at the repo
    layer (admin_repo) rather than admin_service — avoids an admin_service <-> this
    module import cycle since admin_service is not touched by Phase 10."""
    admin_repo.create_audit_event(
        session, category=category, action=action,
        actor_id=getattr(actor, "id", None), actor_email=getattr(actor, "email", ""),
        entity_type=entity_type, entity_id=str(entity_id), detail=detail or {}, ip_address="",
    )


# ================================================================== delivery providers (mock / http)
def _deliver_mock(url: str, payload: dict, secret: str) -> tuple[int, bool, str]:
    """Deterministic, no network. ponytail: a target_url containing 'simulate-fail' is a
    documented test hook to exercise the retry/failure path without real network access."""
    if not url:
        return 0, False, "no target_url"
    if "simulate-fail" in url:
        return 500, False, "simulated failure"
    return 200, True, ""


def _deliver_http(url: str, payload: dict, secret: str, timeout: float = 5.0) -> tuple[int, bool, str]:
    if not url:
        return 0, False, "no target_url"
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if secret:
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={sig}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.status
            return code, 200 <= code < 300, ""
    except urllib.error.HTTPError as exc:
        return exc.code, False, str(exc)[:500]
    except Exception as exc:  # noqa: BLE001 - network failure must not raise, it's a delivery outcome
        return 0, False, str(exc)[:500]


def _deliver(url: str, payload: dict, secret: str) -> tuple[int, bool, str]:
    if _current_delivery_mode() == "http":
        return _deliver_http(url, payload, secret)
    return _deliver_mock(url, payload, secret)


_DEFAULT_MAX_ATTEMPTS = 3


def _record_delivery_outcome(delivery, retry_policy: dict, code: int, ok: bool, error: str) -> None:
    delivery.attempt_count += 1
    delivery.response_code = code
    delivery.last_attempted_at = _utcnow()
    delivery.error_detail = error
    if ok:
        delivery.status = "success"
        delivery.delivered_at = _utcnow()
        return
    max_attempts = (retry_policy or {}).get("max_attempts", _DEFAULT_MAX_ATTEMPTS)
    delivery.status = "retrying" if delivery.attempt_count < max_attempts else "failed"


def _attempt_delivery(delivery, webhook) -> None:
    code, ok, error = _deliver(webhook.target_url, delivery.payload, webhook.secret)
    _record_delivery_outcome(delivery, webhook.retry_policy, code, ok, error)


# ================================================================== background delivery worker
# Outbound webhook HTTP calls (webhook_delivery_mode='http') must never block the request
# thread that triggered them (a business mutation firing an event, e.g. a deal update).
# This is a single in-process worker thread draining a stdlib Queue — no Redis/broker.
# ponytail: single-process ceiling, same as this platform's other in-memory state; a
# multi-instance deployment needs a real broker (SQS/Redis Streams/etc) to fan work out
# across processes. In 'mock' mode (dev/test default) delivery is deterministic and never
# touches the network, so it stays synchronous — nothing to queue, and queuing would only
# add nondeterminism to the test suite for no benefit.
#
# The queued item carries the target_url/secret/payload/retry_policy directly rather than
# just IDs: the worker thread performs the HTTP call BEFORE it ever opens a DB session, so
# it never races the enqueuing request's still-open transaction (publish_event() doesn't
# commit — its caller does, a few lines later). The only DB access from the worker is the
# outcome write-back afterward, by which point the original commit has long since landed.
_delivery_queue: "queue_mod.Queue | None" = None
_worker_thread: threading.Thread | None = None
_worker_sessionmaker = None
# Set by start_webhook_worker() with the app's actual Settings instance. Used instead of
# get_settings() for the delivery-mode decision: get_settings() is an lru_cache'd bare
# singleton that only reflects whichever Settings() was first constructed with no args in
# this process — it does NOT reflect a caller's explicit create_app(Settings(...)) instance
# (the standard pattern every test in this repo uses). Falls back to get_settings() only
# for callers that use this module without ever starting the app (e.g. a bare script).
_worker_settings = None


def _current_delivery_mode() -> str:
    return (_worker_settings or get_settings()).webhook_delivery_mode


def _worker_loop() -> None:
    while True:
        item = _delivery_queue.get()
        try:
            if item is None:  # shutdown sentinel
                return
            code, ok, error = _deliver(item["target_url"], item["payload"], item["secret"])
            try:
                with _worker_sessionmaker() as session:
                    d = repo.get_delivery(session, item["delivery_id"])
                    if d is None:
                        logger.warning("webhook delivery worker: delivery %s not found when recording outcome", item["delivery_id"])
                        continue
                    _record_delivery_outcome(d, item["retry_policy"], code, ok, error)
                    session.commit()
            except Exception:  # noqa: BLE001 - the worker thread must never die
                logger.exception("webhook delivery worker: failed to record outcome for delivery %s", item["delivery_id"])
        finally:
            _delivery_queue.task_done()


def start_webhook_worker(sessionmaker, settings=None) -> None:
    """Called once from the app lifespan on every startup (including a fresh TestClient
    app in each test) — always rebinds _worker_sessionmaker/_worker_settings to the
    calling app's instances so they never point at a torn-down engine or stale config,
    even though the queue/thread themselves are only (re)started once per process."""
    global _delivery_queue, _worker_thread, _worker_sessionmaker, _worker_settings
    _worker_sessionmaker = sessionmaker
    _worker_settings = settings
    if _worker_thread is not None and _worker_thread.is_alive():
        return
    _delivery_queue = queue_mod.Queue()
    _worker_thread = threading.Thread(target=_worker_loop, name="webhook-delivery-worker", daemon=True)
    _worker_thread.start()


def stop_webhook_worker(timeout: float = 5.0) -> None:
    global _worker_thread
    if _delivery_queue is not None:
        _delivery_queue.put(None)
    if _worker_thread is not None:
        _worker_thread.join(timeout=timeout)
        _worker_thread = None


def _worker_running() -> bool:
    return _worker_thread is not None and _worker_thread.is_alive()


def _dispatch_delivery(delivery, webhook) -> None:
    """mock mode (or no worker running, e.g. a script that never started the app
    lifespan): synchronous, deterministic — unchanged from before. http mode with the
    worker running: enqueued so the calling request thread never waits on the network."""
    if _current_delivery_mode() == "http" and _worker_running():
        _delivery_queue.put({
            "delivery_id": delivery.id, "target_url": webhook.target_url,
            "secret": webhook.secret, "payload": delivery.payload,
            "retry_policy": webhook.retry_policy or {},
        })
        return
    _attempt_delivery(delivery, webhook)


# ================================================================== event bus
def publish_event(
    session: Session, *, category: str, event_type: str,
    entity_type: str = "", entity_id: str = "", payload: dict | None = None,
):
    """Create the event-log row and dispatch to every enabled webhook subscribed to
    `event_type` (or '*'). Does not commit — caller owns the transaction, same
    convention as workflow_service.fire_event()."""
    if category not in EVENT_BUS_CATEGORIES:
        raise HTTPException(422, f"invalid category: {category}")
    event = repo.create_event(
        session, category=category, event_type=event_type,
        entity_type=entity_type, entity_id=str(entity_id), payload=payload or {},
    )
    for wh in repo.enabled_webhooks_for_event(session, event_type):
        delivery = repo.create_delivery(
            session, webhook_id=wh.id, event_type=event_type, payload=payload or {}, status="pending",
        )
        _dispatch_delivery(delivery, wh)
    return event


def _event_out(e) -> IntegrationEventOut:
    return IntegrationEventOut(
        id=e.id, category=e.category, event_type=e.event_type,
        entity_type=e.entity_type, entity_id=e.entity_id, payload=e.payload or {},
        created_at=_utc(e.created_at),
    )


def publish_event_api(session: Session, data, user) -> IntegrationEventOut:
    event = publish_event(
        session, category=data.category, event_type=data.event_type,
        entity_type=data.entity_type, entity_id=data.entity_id, payload=data.payload,
    )
    session.commit()
    return _event_out(event)


def list_events(session: Session, user, *, category: str | None = None, event_type: str | None = None, limit: int = 50, offset: int = 0) -> Page:
    rows, total = repo.list_events(session, category=category, event_type=event_type, limit=limit, offset=offset)
    return Page.build([_event_out(e) for e in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


# ================================================================== integration registry
def _integration_out(i) -> IntegrationOut:
    return IntegrationOut(
        id=i.id, name=i.name, provider=i.provider, category=i.category, status=i.status,
        version=i.version, configuration=i.configuration or {}, health_status=i.health_status,
        created_by=i.created_by, created_at=_utc(i.created_at), updated_at=_utc(i.updated_at),
    )


def create_integration(session: Session, data: IntegrationCreate, user) -> IntegrationOut:
    _require_manager(user)
    i = repo.create_integration(
        session, name=data.name, provider=data.provider, category=data.category,
        version=data.version, configuration=data.configuration, created_by=user.id,
    )
    _audit(session, category="configuration_change", action="integration_created", actor=user, entity_type="integration", entity_id=i.id)
    session.commit()
    return _integration_out(i)


def list_integrations(session: Session, user, *, category: str | None = None, status: str | None = None, limit: int = 50, offset: int = 0) -> Page:
    rows, total = repo.list_integrations(session, category=category, status=status, limit=limit, offset=offset)
    return Page.build([_integration_out(i) for i in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


def get_integration(session: Session, integration_id: int, user) -> IntegrationOut:
    i = repo.get_integration(session, integration_id)
    if not i:
        raise HTTPException(404, "integration not found")
    return _integration_out(i)


def patch_integration(session: Session, integration_id: int, data: IntegrationPatch, user) -> IntegrationOut:
    _require_manager(user)
    i = repo.get_integration(session, integration_id)
    if not i:
        raise HTTPException(404, "integration not found")
    for field in ("status", "version", "configuration", "health_status"):
        val = getattr(data, field)
        if val is not None:
            setattr(i, field, val)
    _audit(session, category="configuration_change", action="integration_updated", actor=user, entity_type="integration", entity_id=integration_id)
    session.commit()
    return _integration_out(i)


def delete_integration(session: Session, integration_id: int, user) -> None:
    _require_manager(user)
    if not repo.delete_integration(session, integration_id):
        raise HTTPException(404, "integration not found")
    _audit(session, category="configuration_change", action="integration_deleted", actor=user, entity_type="integration", entity_id=integration_id)
    session.commit()


# ================================================================== webhooks
def _webhook_out(w) -> WebhookOut:
    return WebhookOut(
        id=w.id, name=w.name, event_type=w.event_type, target_url=w.target_url,
        retry_policy=w.retry_policy or {}, status=w.status,
        created_at=_utc(w.created_at), updated_at=_utc(w.updated_at),
    )


def create_webhook(session: Session, data: WebhookCreate, user) -> WebhookCreatedOut:
    _require_manager(user)
    secret = secrets.token_urlsafe(32)
    w = repo.create_webhook(
        session, name=data.name, event_type=data.event_type, target_url=data.target_url,
        secret=secret, retry_policy=data.retry_policy or {"max_attempts": _DEFAULT_MAX_ATTEMPTS, "backoff_seconds": 300},
        created_by=user.id,
    )
    _audit(session, category="configuration_change", action="webhook_created", actor=user, entity_type="webhook", entity_id=w.id)
    session.commit()
    return WebhookCreatedOut(**_webhook_out(w).model_dump(), secret=secret)


def list_webhooks(session: Session, user, *, event_type: str | None = None, status: str | None = None, limit: int = 50, offset: int = 0) -> Page:
    rows, total = repo.list_webhooks(session, event_type=event_type, status=status, limit=limit, offset=offset)
    return Page.build([_webhook_out(w) for w in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


def get_webhook(session: Session, webhook_id: int, user) -> WebhookOut:
    w = repo.get_webhook(session, webhook_id)
    if not w:
        raise HTTPException(404, "webhook not found")
    return _webhook_out(w)


def patch_webhook(session: Session, webhook_id: int, data: WebhookPatch, user) -> WebhookOut:
    _require_manager(user)
    w = repo.get_webhook(session, webhook_id)
    if not w:
        raise HTTPException(404, "webhook not found")
    for field in ("name", "target_url", "retry_policy", "status"):
        val = getattr(data, field)
        if val is not None:
            setattr(w, field, val)
    _audit(session, category="configuration_change", action="webhook_updated", actor=user, entity_type="webhook", entity_id=webhook_id)
    session.commit()
    return _webhook_out(w)


def delete_webhook(session: Session, webhook_id: int, user) -> None:
    _require_manager(user)
    if not repo.delete_webhook(session, webhook_id):
        raise HTTPException(404, "webhook not found")
    _audit(session, category="configuration_change", action="webhook_deleted", actor=user, entity_type="webhook", entity_id=webhook_id)
    session.commit()


def _delivery_out(d, name_map: dict[int, str]) -> WebhookDeliveryOut:
    return WebhookDeliveryOut(
        id=d.id, webhook_id=d.webhook_id, webhook_name=name_map.get(d.webhook_id, ""),
        event_type=d.event_type, payload=d.payload or {}, status=d.status,
        response_code=d.response_code, attempt_count=d.attempt_count, error_detail=d.error_detail,
        last_attempted_at=_utc(d.last_attempted_at), delivered_at=_utc(d.delivered_at), created_at=_utc(d.created_at),
    )


def list_deliveries(session: Session, user, *, webhook_id: int | None = None, status: str | None = None, limit: int = 50, offset: int = 0) -> Page:
    rows, total = repo.list_deliveries(session, webhook_id=webhook_id, status=status, limit=limit, offset=offset)
    name_map = repo.get_webhook_names(session, [r.webhook_id for r in rows])
    return Page.build([_delivery_out(d, name_map) for d in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


def replay_delivery(session: Session, delivery_id: int, user) -> WebhookDeliveryOut:
    """Manually re-attempt a delivery (typically a failed one) — bypasses the automatic
    retry_policy.max_attempts cap since this is an explicit human action."""
    _require_manager(user)
    d = repo.get_delivery(session, delivery_id)
    if not d:
        raise HTTPException(404, "delivery not found")
    w = repo.get_webhook(session, d.webhook_id)
    if not w:
        raise HTTPException(404, "webhook not found")
    _attempt_delivery(d, w)
    _audit(session, category="configuration_change", action="webhook_delivery_replayed", actor=user, entity_type="webhook_delivery", entity_id=delivery_id)
    session.commit()
    name_map = repo.get_webhook_names(session, [w.id])
    return _delivery_out(d, name_map)


@single_flight("webhook_retry_tick")
def run_retry_tick(session: Session, user) -> dict:
    """Sweep 'retrying' deliveries whose backoff window has elapsed and re-attempt them.
    Manual or cron-tick, same pattern as workflow_service.run_sla_tick. single_flight
    prevents two overlapping cron pokes from double-sending the same retry."""
    now = _utcnow()
    retried = 0
    for d in repo.retrying_deliveries(session):
        w = repo.get_webhook(session, d.webhook_id)
        if not w:
            continue
        backoff = (w.retry_policy or {}).get("backoff_seconds", 300)
        last = _utc(d.last_attempted_at) or now
        if (now - last).total_seconds() < backoff:
            continue
        _dispatch_delivery(d, w)
        retried += 1
    session.commit()
    return {"retried": retried}


# ================================================================== OAuth credentials
def _oauth_out(c) -> OAuthCredentialOut:
    return OAuthCredentialOut(
        id=c.id, name=c.name, provider=c.provider, client_id=c.client_id, scopes=c.scopes or [],
        owner_id=c.owner_id, status=c.status, request_count=c.request_count,
        expires_at=_utc(c.expires_at), last_used_at=_utc(c.last_used_at),
        created_at=_utc(c.created_at), revoked_at=_utc(c.revoked_at),
    )


def create_oauth_credential(session: Session, data: OAuthCredentialCreate, user) -> OAuthCredentialCreatedOut:
    _require_manager(user)
    raw_secret = data.client_secret or secrets.token_urlsafe(32)
    secret_hash = hashlib.sha256(raw_secret.encode()).hexdigest()
    c = repo.create_oauth_credential(
        session, name=data.name, provider=data.provider, client_id=data.client_id,
        client_secret_hash=secret_hash, scopes=data.scopes, owner_id=user.id, expires_at=data.expires_at,
    )
    _audit(session, category="configuration_change", action="oauth_credential_created", actor=user, entity_type="oauth_credential", entity_id=c.id)
    session.commit()
    return OAuthCredentialCreatedOut(**_oauth_out(c).model_dump(), client_secret=raw_secret)


def list_oauth_credentials(session: Session, user) -> list[OAuthCredentialOut]:
    return [_oauth_out(c) for c in repo.list_oauth_credentials(session, owner_id=None if _is_manager(user) else user.id)]


def revoke_oauth_credential(session: Session, credential_id: int, user) -> OAuthCredentialOut:
    c = repo.get_oauth_credential(session, credential_id)
    if not c:
        raise HTTPException(404, "credential not found")
    if c.owner_id != user.id and not _is_manager(user):
        raise HTTPException(403, "only the owner or a manager may revoke this credential")
    c.status = "revoked"
    c.revoked_at = _utcnow()
    _audit(session, category="configuration_change", action="oauth_credential_revoked", actor=user, entity_type="oauth_credential", entity_id=credential_id)
    session.commit()
    return _oauth_out(c)


def rotate_oauth_credential(session: Session, credential_id: int, user) -> OAuthCredentialCreatedOut:
    old = repo.get_oauth_credential(session, credential_id)
    if not old:
        raise HTTPException(404, "credential not found")
    if old.owner_id != user.id and not _is_manager(user):
        raise HTTPException(403, "only the owner or a manager may rotate this credential")
    old.status = "revoked"
    old.revoked_at = _utcnow()
    raw_secret = secrets.token_urlsafe(32)
    new = repo.create_oauth_credential(
        session, name=old.name, provider=old.provider, client_id=old.client_id,
        client_secret_hash=hashlib.sha256(raw_secret.encode()).hexdigest(),
        scopes=old.scopes, owner_id=old.owner_id, expires_at=old.expires_at,
    )
    _audit(session, category="configuration_change", action="oauth_credential_rotated", actor=user, entity_type="oauth_credential", entity_id=new.id, detail={"replaced_credential_id": credential_id})
    session.commit()
    return OAuthCredentialCreatedOut(**_oauth_out(new).model_dump(), client_secret=raw_secret)


# ================================================================== connector framework
def _connector_out(c) -> ConnectorOut:
    return ConnectorOut(
        id=c.id, name=c.name, connector_type=c.connector_type, config=c.config or {},
        schedule_cron=c.schedule_cron, status=c.status, last_run_at=_utc(c.last_run_at),
        last_run_status=c.last_run_status, created_at=_utc(c.created_at), updated_at=_utc(c.updated_at),
    )


def create_connector(session: Session, data: ConnectorCreate, user) -> ConnectorOut:
    _require_manager(user)
    if data.connector_type not in CONNECTOR_TYPES:
        raise HTTPException(422, f"invalid connector_type: {data.connector_type}")
    c = repo.create_connector(
        session, name=data.name, connector_type=data.connector_type, config=data.config,
        schedule_cron=data.schedule_cron, created_by=user.id,
    )
    _audit(session, category="configuration_change", action="connector_created", actor=user, entity_type="connector", entity_id=c.id)
    session.commit()
    return _connector_out(c)


def list_connectors(session: Session, user, *, connector_type: str | None = None, status: str | None = None) -> list[ConnectorOut]:
    return [_connector_out(c) for c in repo.list_connectors(session, connector_type=connector_type, status=status)]


def patch_connector(session: Session, connector_id: int, data: ConnectorPatch, user) -> ConnectorOut:
    _require_manager(user)
    c = repo.get_connector(session, connector_id)
    if not c:
        raise HTTPException(404, "connector not found")
    for field in ("name", "config", "schedule_cron", "status"):
        val = getattr(data, field)
        if val is not None:
            setattr(c, field, val)
    session.commit()
    return _connector_out(c)


def delete_connector(session: Session, connector_id: int, user) -> None:
    _require_manager(user)
    if not repo.delete_connector(session, connector_id):
        raise HTTPException(404, "connector not found")
    session.commit()


def _run_out(r) -> ConnectorRunOut:
    return ConnectorRunOut(
        id=r.id, connector_id=r.connector_id, status=r.status, duration_ms=r.duration_ms,
        result_detail=r.result_detail or {}, started_at=_utc(r.started_at), completed_at=_utc(r.completed_at),
    )


def run_connector(session: Session, connector_id: int, user) -> ConnectorRunOut:
    """Executes an HTTP/REST/webhook connector's configured call, or simulates one manual
    tick of a 'scheduled' connector. ponytail: no real cron scheduler is wired here (that's
    the existing email_scheduler's job for outreach); schedule_cron is stored metadata,
    upgrade path is a periodic tick calling this per due connector."""
    _require_manager(user)
    c = repo.get_connector(session, connector_id)
    if not c:
        raise HTTPException(404, "connector not found")
    if c.status != "active":
        raise HTTPException(409, "connector is not active")
    started = _utcnow()
    t0 = time.monotonic()
    cfg = c.config or {}
    code, ok, error = _deliver(cfg.get("url", ""), cfg.get("payload", {}), cfg.get("secret", ""))
    duration_ms = int((time.monotonic() - t0) * 1000)
    status = "success" if ok else "failed"
    run = repo.create_connector_run(
        session, connector_id=c.id, status=status, duration_ms=duration_ms,
        result_detail={"response_code": code, "error": error},
        started_at=started, completed_at=_utcnow(),
    )
    c.last_run_at = _utcnow()
    c.last_run_status = status
    session.commit()
    return _run_out(run)


def list_connector_runs(session: Session, connector_id: int, user, *, limit: int = 50) -> list[ConnectorRunOut]:
    return [_run_out(r) for r in repo.list_connector_runs(session, connector_id, limit=limit)]


# ================================================================== plugin framework
def _plugin_out(p) -> PluginOut:
    return PluginOut(
        id=p.id, name=p.name, version=p.version, plugin_metadata=p.plugin_metadata or {},
        permissions=p.permissions or [], execution_hooks=p.execution_hooks or [], status=p.status,
        created_at=_utc(p.created_at), updated_at=_utc(p.updated_at),
    )


def register_plugin(session: Session, data: PluginCreate, user) -> PluginOut:
    _require_manager(user)
    bad_hooks = [h for h in data.execution_hooks if h not in PLUGIN_HOOK_TYPES]
    if bad_hooks:
        raise HTTPException(422, f"invalid execution_hooks: {bad_hooks}")
    p = repo.create_plugin(
        session, name=data.name, version=data.version, plugin_metadata=data.plugin_metadata,
        permissions=data.permissions, execution_hooks=data.execution_hooks, created_by=user.id,
    )
    _audit(session, category="configuration_change", action="plugin_registered", actor=user, entity_type="plugin", entity_id=p.id)
    session.commit()
    return _plugin_out(p)


def list_plugins(session: Session, user, *, status: str | None = None) -> list[PluginOut]:
    return [_plugin_out(p) for p in repo.list_plugins(session, status=status)]


def patch_plugin(session: Session, plugin_id: int, data: PluginPatch, user) -> PluginOut:
    _require_manager(user)
    p = repo.get_plugin(session, plugin_id)
    if not p:
        raise HTTPException(404, "plugin not found")
    if data.execution_hooks is not None:
        bad_hooks = [h for h in data.execution_hooks if h not in PLUGIN_HOOK_TYPES]
        if bad_hooks:
            raise HTTPException(422, f"invalid execution_hooks: {bad_hooks}")
    for field in ("plugin_metadata", "permissions", "execution_hooks", "status"):
        val = getattr(data, field)
        if val is not None:
            setattr(p, field, val)
    session.commit()
    return _plugin_out(p)


def delete_plugin(session: Session, plugin_id: int, user) -> None:
    _require_manager(user)
    if not repo.delete_plugin(session, plugin_id):
        raise HTTPException(404, "plugin not found")
    session.commit()


def _plugin_exec_out(e) -> PluginExecutionOut:
    return PluginExecutionOut(
        id=e.id, plugin_id=e.plugin_id, hook_name=e.hook_name, status=e.status,
        detail=e.detail or {}, executed_at=_utc(e.executed_at),
    )


def trigger_plugin_hook(session: Session, hook_name: str, user, *, detail: dict | None = None) -> list[PluginExecutionOut]:
    if hook_name not in PLUGIN_HOOK_TYPES:
        raise HTTPException(422, f"invalid hook_name: {hook_name}")
    results = [
        repo.create_plugin_execution(session, plugin_id=p.id, hook_name=hook_name, status="success", detail=detail or {})
        for p in repo.enabled_plugins_for_hook(session, hook_name)
    ]
    session.commit()
    return [_plugin_exec_out(e) for e in results]


def list_plugin_executions(session: Session, user, *, plugin_id: int | None = None, limit: int = 50) -> list[PluginExecutionOut]:
    return [_plugin_exec_out(e) for e in repo.list_plugin_executions(session, plugin_id=plugin_id, limit=limit)]


# ================================================================== dashboard + analytics (cached)
_DASH_TTL_SECONDS = 30
_dash_cache: dict[str, tuple[float, IntegrationDashboardOut]] = {}


def _cache_key(session: Session) -> str:
    try:
        return str(session.get_bind().url)
    except Exception:
        return "default"


def integration_dashboard(session: Session, user) -> IntegrationDashboardOut:
    key = _cache_key(session)
    cached = _dash_cache.get(key)
    if cached and time.monotonic() - cached[0] < _DASH_TTL_SECONDS:
        return cached[1]

    stats = repo.delivery_stats(session)
    connectors = repo.list_connectors(session)
    health = [
        ConnectorHealthOut(
            connector_id=c.id, name=c.name, connector_type=c.connector_type, status=c.status,
            last_run_status=c.last_run_status, last_run_at=_utc(c.last_run_at),
        )
        for c in connectors
    ]
    out = IntegrationDashboardOut(
        active_integrations=repo.count_active_integrations(session),
        webhook_deliveries_total=stats["total"],
        failed_deliveries=stats["failed"],
        connector_health=health,
        api_usage_total=admin_repo.total_api_usage(session),
        plugin_status=repo.plugin_status_counts(session),
    )
    _dash_cache[key] = (time.monotonic(), out)
    return out


def integration_analytics(session: Session, user) -> IntegrationAnalyticsOut:
    stats = repo.delivery_stats(session)
    total = stats["total"]
    success_rate = round(stats["success"] / total, 4) if total else 0.0
    retry_rate = round(stats["retrying"] / total, 4) if total else 0.0
    connectors = repo.list_connectors(session)
    run_counts = repo.connector_run_counts(session)
    connector_usage = {c.name: run_counts.get(c.id, 0) for c in connectors}
    plugins = repo.list_plugins(session)
    exec_counts = repo.plugin_execution_counts(session)
    plugin_usage = {p.name: exec_counts.get(p.id, 0) for p in plugins}
    return IntegrationAnalyticsOut(
        api_requests_total=admin_repo.total_api_usage(session),
        webhook_success_rate=success_rate,
        retry_rate=retry_rate,
        connector_usage=connector_usage,
        plugin_usage=plugin_usage,
        integration_health=repo.integration_health_counts(session),
    )
