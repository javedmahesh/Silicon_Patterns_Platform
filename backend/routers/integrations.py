"""Enterprise CRM Phase 10: Integration Platform & Developer Ecosystem endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import admin_service
from backend import integration_service as svc
from backend.dependencies import get_session
from backend.schemas import (
    ApiKeyOut,
    ConnectorCreate,
    ConnectorOut,
    ConnectorPatch,
    ConnectorRunOut,
    EventPublishIn,
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
from backend.security import get_current_user
from master_db.models import User

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ============================================================ integration registry
@router.get("", response_model=Page)
def list_integrations(
    category: str | None = Query(None), status_: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_integrations(session, user, category=category, status=status_, limit=limit, offset=offset)


@router.post("", response_model=IntegrationOut, status_code=status.HTTP_201_CREATED)
def create_integration(
    data: IntegrationCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_integration(session, data, user)


# ============================================================ webhooks
@router.get("/webhooks", response_model=Page)
def list_webhooks(
    event_type: str | None = Query(None), status_: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_webhooks(session, user, event_type=event_type, status=status_, limit=limit, offset=offset)


@router.post("/webhooks", response_model=WebhookCreatedOut, status_code=status.HTTP_201_CREATED)
def create_webhook(
    data: WebhookCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_webhook(session, data, user)


@router.get("/webhooks/{webhook_id}", response_model=WebhookOut)
def get_webhook(
    webhook_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.get_webhook(session, webhook_id, user)


@router.patch("/webhooks/{webhook_id}", response_model=WebhookOut)
def patch_webhook(
    webhook_id: int, data: WebhookPatch,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.patch_webhook(session, webhook_id, data, user)


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    svc.delete_webhook(session, webhook_id, user)


@router.get("/webhooks/deliveries/list", response_model=Page)
def list_deliveries(
    webhook_id: int | None = Query(None), status_: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_deliveries(session, user, webhook_id=webhook_id, status=status_, limit=limit, offset=offset)


@router.post("/webhooks/deliveries/{delivery_id}/replay", response_model=WebhookDeliveryOut)
def replay_delivery(
    delivery_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.replay_delivery(session, delivery_id, user)


@router.post("/webhooks/retry-tick")
def run_retry_tick(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.run_retry_tick(session, user)


# ============================================================ API credentials (API keys + OAuth)
# API keys are owned by the existing administration module (Phase 9) — this is a thin,
# read-only reuse, not a parallel implementation. Create/rotate/revoke stay on
# /governance/api-keys, the single source of truth for that table.
@router.get("/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return admin_service.list_api_keys(session, user, owner_id=user.id)


@router.get("/oauth-credentials", response_model=list[OAuthCredentialOut])
def list_oauth_credentials(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_oauth_credentials(session, user)


@router.post("/oauth-credentials", response_model=OAuthCredentialCreatedOut, status_code=status.HTTP_201_CREATED)
def create_oauth_credential(
    data: OAuthCredentialCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_oauth_credential(session, data, user)


@router.post("/oauth-credentials/{credential_id}/revoke", response_model=OAuthCredentialOut)
def revoke_oauth_credential(
    credential_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.revoke_oauth_credential(session, credential_id, user)


@router.post("/oauth-credentials/{credential_id}/rotate", response_model=OAuthCredentialCreatedOut)
def rotate_oauth_credential(
    credential_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.rotate_oauth_credential(session, credential_id, user)


# ============================================================ event bus
@router.get("/events", response_model=Page)
def list_events(
    category: str | None = Query(None), event_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_events(session, user, category=category, event_type=event_type, limit=limit, offset=offset)


@router.post("/events/publish", response_model=IntegrationEventOut, status_code=status.HTTP_201_CREATED)
def publish_event(
    data: EventPublishIn,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.publish_event_api(session, data, user)


# ============================================================ connector framework
@router.get("/connectors", response_model=list[ConnectorOut])
def list_connectors(
    connector_type: str | None = Query(None), status_: str | None = Query(None, alias="status"),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_connectors(session, user, connector_type=connector_type, status=status_)


@router.post("/connectors", response_model=ConnectorOut, status_code=status.HTTP_201_CREATED)
def create_connector(
    data: ConnectorCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_connector(session, data, user)


@router.patch("/connectors/{connector_id}", response_model=ConnectorOut)
def patch_connector(
    connector_id: int, data: ConnectorPatch,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.patch_connector(session, connector_id, data, user)


@router.delete("/connectors/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connector(
    connector_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    svc.delete_connector(session, connector_id, user)


@router.post("/connectors/{connector_id}/run", response_model=ConnectorRunOut)
def run_connector(
    connector_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.run_connector(session, connector_id, user)


@router.get("/connectors/{connector_id}/runs", response_model=list[ConnectorRunOut])
def list_connector_runs(
    connector_id: int, limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_connector_runs(session, connector_id, user, limit=limit)


# ============================================================ plugin framework
@router.get("/plugins", response_model=list[PluginOut])
def list_plugins(
    status_: str | None = Query(None, alias="status"),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_plugins(session, user, status=status_)


@router.post("/plugins", response_model=PluginOut, status_code=status.HTTP_201_CREATED)
def register_plugin(
    data: PluginCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.register_plugin(session, data, user)


@router.patch("/plugins/{plugin_id}", response_model=PluginOut)
def patch_plugin(
    plugin_id: int, data: PluginPatch,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.patch_plugin(session, plugin_id, data, user)


@router.delete("/plugins/{plugin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plugin(
    plugin_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    svc.delete_plugin(session, plugin_id, user)


@router.post("/plugins/hooks/{hook_name}/trigger", response_model=list[PluginExecutionOut])
def trigger_plugin_hook(
    hook_name: str,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.trigger_plugin_hook(session, hook_name, user)


@router.get("/plugins/executions/list", response_model=list[PluginExecutionOut])
def list_plugin_executions(
    plugin_id: int | None = Query(None), limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_plugin_executions(session, user, plugin_id=plugin_id, limit=limit)


# ============================================================ dashboard + analytics
@router.get("/dashboard/summary", response_model=IntegrationDashboardOut)
def integration_dashboard(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.integration_dashboard(session, user)


@router.get("/analytics/summary", response_model=IntegrationAnalyticsOut)
def integration_analytics(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.integration_analytics(session, user)


# ============================================================ integration registry (by id)
# Registered last: this catch-all single-segment path must not shadow the more specific
# literal routes above (/webhooks, /connectors, /plugins, /events, /api-keys, ...).
@router.get("/{integration_id}", response_model=IntegrationOut)
def get_integration(
    integration_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.get_integration(session, integration_id, user)


@router.patch("/{integration_id}", response_model=IntegrationOut)
def patch_integration(
    integration_id: int, data: IntegrationPatch,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.patch_integration(session, integration_id, data, user)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(
    integration_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    svc.delete_integration(session, integration_id, user)
