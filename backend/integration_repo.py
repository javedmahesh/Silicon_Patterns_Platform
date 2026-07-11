"""Data access for Enterprise CRM Phase 10: Integration Platform & Developer Ecosystem."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from master_db.models import (
    Connector,
    ConnectorRun,
    Integration,
    IntegrationEvent,
    OAuthCredential,
    Plugin,
    PluginExecution,
    Webhook,
    WebhookDelivery,
)


# ----------------------------------------------------------------- integrations
def create_integration(session: Session, **kw) -> Integration:
    i = Integration(**kw)
    session.add(i)
    session.flush()
    return i


def get_integration(session: Session, integration_id: int) -> Integration | None:
    return session.get(Integration, integration_id)


def list_integrations(
    session: Session, *, category: str | None = None, status: str | None = None,
    limit: int = 50, offset: int = 0,
) -> tuple[list[Integration], int]:
    q = select(Integration)
    filters = []
    if category:
        filters.append(Integration.category == category)
    if status:
        filters.append(Integration.status == status)
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(Integration.id.desc()).limit(limit).offset(offset)))
    return rows, total


def delete_integration(session: Session, integration_id: int) -> bool:
    i = session.get(Integration, integration_id)
    if not i:
        return False
    session.delete(i)
    return True


def count_active_integrations(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(Integration).where(Integration.status == "active")
    ) or 0


def integration_health_counts(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(Integration.health_status, func.count(Integration.id)).group_by(Integration.health_status)
    ).all()
    return {r[0]: r[1] for r in rows}


# ----------------------------------------------------------------- webhooks
def create_webhook(session: Session, **kw) -> Webhook:
    w = Webhook(**kw)
    session.add(w)
    session.flush()
    return w


def get_webhook(session: Session, webhook_id: int) -> Webhook | None:
    return session.get(Webhook, webhook_id)


def list_webhooks(
    session: Session, *, event_type: str | None = None, status: str | None = None,
    limit: int = 50, offset: int = 0,
) -> tuple[list[Webhook], int]:
    q = select(Webhook)
    filters = []
    if event_type:
        filters.append(Webhook.event_type == event_type)
    if status:
        filters.append(Webhook.status == status)
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(Webhook.id.desc()).limit(limit).offset(offset)))
    return rows, total


def enabled_webhooks_for_event(session: Session, event_type: str) -> list[Webhook]:
    """Webhooks subscribed to this exact event_type, or to '*' (all events). 1 query."""
    return list(session.scalars(
        select(Webhook).where(
            Webhook.status == "enabled",
            Webhook.event_type.in_((event_type, "*")),
        )
    ))


def delete_webhook(session: Session, webhook_id: int) -> bool:
    w = session.get(Webhook, webhook_id)
    if not w:
        return False
    session.delete(w)
    return True


def get_webhook_names(session: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = session.execute(select(Webhook.id, Webhook.name).where(Webhook.id.in_(ids))).all()
    return {r[0]: r[1] for r in rows}


# ----------------------------------------------------------------- webhook deliveries
def create_delivery(session: Session, **kw) -> WebhookDelivery:
    d = WebhookDelivery(**kw)
    session.add(d)
    session.flush()
    return d


def get_delivery(session: Session, delivery_id: int) -> WebhookDelivery | None:
    return session.get(WebhookDelivery, delivery_id)


def list_deliveries(
    session: Session, *, webhook_id: int | None = None, status: str | None = None,
    limit: int = 50, offset: int = 0,
) -> tuple[list[WebhookDelivery], int]:
    q = select(WebhookDelivery)
    filters = []
    if webhook_id is not None:
        filters.append(WebhookDelivery.webhook_id == webhook_id)
    if status:
        filters.append(WebhookDelivery.status == status)
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(WebhookDelivery.id.desc()).limit(limit).offset(offset)))
    return rows, total


def delivery_stats(session: Session) -> dict:
    """Total/success/failed/retrying counts. 1 query."""
    row = session.execute(
        select(
            func.count(WebhookDelivery.id),
            func.count(WebhookDelivery.id).filter(WebhookDelivery.status == "success"),
            func.count(WebhookDelivery.id).filter(WebhookDelivery.status == "failed"),
            func.count(WebhookDelivery.id).filter(WebhookDelivery.status == "retrying"),
            func.coalesce(func.sum(WebhookDelivery.attempt_count), 0),
        )
    ).one()
    total, success, failed, retrying, attempts = row
    return {"total": total, "success": success, "failed": failed, "retrying": retrying, "attempts": attempts}


def retrying_deliveries(session: Session) -> list[WebhookDelivery]:
    return list(session.scalars(select(WebhookDelivery).where(WebhookDelivery.status == "retrying")))


# ----------------------------------------------------------------- oauth credentials
def create_oauth_credential(session: Session, **kw) -> OAuthCredential:
    c = OAuthCredential(**kw)
    session.add(c)
    session.flush()
    return c


def get_oauth_credential(session: Session, credential_id: int) -> OAuthCredential | None:
    return session.get(OAuthCredential, credential_id)


def list_oauth_credentials(session: Session, *, owner_id: int | None = None) -> list[OAuthCredential]:
    q = select(OAuthCredential)
    if owner_id is not None:
        q = q.where(OAuthCredential.owner_id == owner_id)
    return list(session.scalars(q.order_by(OAuthCredential.id.desc())))


# ----------------------------------------------------------------- event bus
def create_event(session: Session, **kw) -> IntegrationEvent:
    e = IntegrationEvent(**kw)
    session.add(e)
    session.flush()
    return e


def list_events(
    session: Session, *, category: str | None = None, event_type: str | None = None,
    limit: int = 50, offset: int = 0,
) -> tuple[list[IntegrationEvent], int]:
    q = select(IntegrationEvent)
    filters = []
    if category:
        filters.append(IntegrationEvent.category == category)
    if event_type:
        filters.append(IntegrationEvent.event_type == event_type)
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(IntegrationEvent.id.desc()).limit(limit).offset(offset)))
    return rows, total


# ----------------------------------------------------------------- connectors
def create_connector(session: Session, **kw) -> Connector:
    c = Connector(**kw)
    session.add(c)
    session.flush()
    return c


def get_connector(session: Session, connector_id: int) -> Connector | None:
    return session.get(Connector, connector_id)


def list_connectors(
    session: Session, *, connector_type: str | None = None, status: str | None = None,
) -> list[Connector]:
    q = select(Connector)
    filters = []
    if connector_type:
        filters.append(Connector.connector_type == connector_type)
    if status:
        filters.append(Connector.status == status)
    if filters:
        q = q.where(and_(*filters))
    return list(session.scalars(q.order_by(Connector.id.desc())))


def delete_connector(session: Session, connector_id: int) -> bool:
    c = session.get(Connector, connector_id)
    if not c:
        return False
    session.delete(c)
    return True


def create_connector_run(session: Session, **kw) -> ConnectorRun:
    r = ConnectorRun(**kw)
    session.add(r)
    session.flush()
    return r


def list_connector_runs(session: Session, connector_id: int, *, limit: int = 50) -> list[ConnectorRun]:
    return list(session.scalars(
        select(ConnectorRun).where(ConnectorRun.connector_id == connector_id)
        .order_by(ConnectorRun.id.desc()).limit(limit)
    ))


def connector_run_counts(session: Session) -> dict[int, int]:
    """Run count per connector, 1 query — used by analytics (connector usage)."""
    rows = session.execute(
        select(ConnectorRun.connector_id, func.count(ConnectorRun.id)).group_by(ConnectorRun.connector_id)
    ).all()
    return {r[0]: r[1] for r in rows}


def connector_health_counts(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(Connector.last_run_status, func.count(Connector.id)).group_by(Connector.last_run_status)
    ).all()
    return {(r[0] or "never_run"): r[1] for r in rows}


# ----------------------------------------------------------------- plugins
def create_plugin(session: Session, **kw) -> Plugin:
    p = Plugin(**kw)
    session.add(p)
    session.flush()
    return p


def get_plugin(session: Session, plugin_id: int) -> Plugin | None:
    return session.get(Plugin, plugin_id)


def list_plugins(session: Session, *, status: str | None = None) -> list[Plugin]:
    q = select(Plugin)
    if status:
        q = q.where(Plugin.status == status)
    return list(session.scalars(q.order_by(Plugin.id.desc())))


def enabled_plugins_for_hook(session: Session, hook_name: str) -> list[Plugin]:
    """ponytail: filters in Python after one fetch of enabled plugins — the JSON
    execution_hooks column isn't indexable portably across SQLite/Postgres at this
    scale (a handful of plugins). Upgrade path: a plugin_hooks join table if the
    plugin count grows into the hundreds."""
    rows = session.scalars(select(Plugin).where(Plugin.status == "enabled"))
    return [p for p in rows if hook_name in (p.execution_hooks or [])]


def delete_plugin(session: Session, plugin_id: int) -> bool:
    p = session.get(Plugin, plugin_id)
    if not p:
        return False
    session.delete(p)
    return True


def plugin_status_counts(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(Plugin.status, func.count(Plugin.id)).group_by(Plugin.status)
    ).all()
    return {r[0]: r[1] for r in rows}


def create_plugin_execution(session: Session, **kw) -> PluginExecution:
    e = PluginExecution(**kw)
    session.add(e)
    session.flush()
    return e


def list_plugin_executions(session: Session, *, plugin_id: int | None = None, limit: int = 50) -> list[PluginExecution]:
    q = select(PluginExecution)
    if plugin_id is not None:
        q = q.where(PluginExecution.plugin_id == plugin_id)
    return list(session.scalars(q.order_by(PluginExecution.id.desc()).limit(limit)))


def plugin_execution_counts(session: Session) -> dict[int, int]:
    """Execution count per plugin, 1 query — used by analytics (plugin usage)."""
    rows = session.execute(
        select(PluginExecution.plugin_id, func.count(PluginExecution.id)).group_by(PluginExecution.plugin_id)
    ).all()
    return {r[0]: r[1] for r in rows}
