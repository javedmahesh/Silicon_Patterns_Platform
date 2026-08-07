"""Data access for Enterprise CRM Phase 12: Data Warehouse & Advanced Business Intelligence."""
from __future__ import annotations


from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from master_db.models import (
    CustomReport,
    Kpi,
    KpiValue,
    OutreachActivity,
    ReportSchedule,
    ScheduledReportRun,
    WarehouseSnapshot,
)


# ----------------------------------------------------------------- activity aggregate (no existing
# repo function covers a type-grouped count over the whole activity log; every other
# metric_type below reuses an aggregate an earlier phase already built).
def activity_counts_by_type(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(OutreachActivity.type, func.count(OutreachActivity.id)).group_by(OutreachActivity.type)
    ).all()
    return {r[0]: r[1] for r in rows}


# ----------------------------------------------------------------- warehouse snapshots
def create_snapshot(session: Session, **kw) -> WarehouseSnapshot:
    s = WarehouseSnapshot(**kw)
    session.add(s)
    session.flush()
    return s


def list_snapshots(
    session: Session, *, metric_type: str | None = None, limit: int = 50, offset: int = 0,
) -> tuple[list[WarehouseSnapshot], int]:
    q = select(WarehouseSnapshot)
    if metric_type:
        q = q.where(WarehouseSnapshot.metric_type == metric_type)
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(WarehouseSnapshot.id.desc()).limit(limit).offset(offset)))
    return rows, total


def latest_snapshot(session: Session, metric_type: str) -> WarehouseSnapshot | None:
    return session.scalar(
        select(WarehouseSnapshot).where(WarehouseSnapshot.metric_type == metric_type)
        .order_by(WarehouseSnapshot.id.desc()).limit(1)
    )


def snapshot_counts_by_type(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(WarehouseSnapshot.metric_type, func.count(WarehouseSnapshot.id)).group_by(WarehouseSnapshot.metric_type)
    ).all()
    return {r[0]: r[1] for r in rows}


def total_snapshots(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(WarehouseSnapshot)) or 0


# ----------------------------------------------------------------- KPIs
def create_kpi(session: Session, **kw) -> Kpi:
    k = Kpi(**kw)
    session.add(k)
    session.flush()
    return k


def get_kpi(session: Session, kpi_id: int) -> Kpi | None:
    return session.get(Kpi, kpi_id)


def get_kpi_by_name(session: Session, name: str) -> Kpi | None:
    return session.scalar(select(Kpi).where(Kpi.name == name))


def list_kpis(session: Session, *, category: str | None = None) -> list[Kpi]:
    q = select(Kpi)
    if category:
        q = q.where(Kpi.category == category)
    return list(session.scalars(q.order_by(Kpi.id)))


def delete_kpi(session: Session, kpi_id: int) -> bool:
    k = session.get(Kpi, kpi_id)
    if not k:
        return False
    session.delete(k)
    return True


def create_kpi_value(session: Session, **kw) -> KpiValue:
    v = KpiValue(**kw)
    session.add(v)
    session.flush()
    return v


def latest_kpi_values(session: Session, kpi_ids: list[int]) -> dict[int, float]:
    """Latest recorded value per KPI, 1 query — no N+1 across list_kpis()."""
    if not kpi_ids:
        return {}
    rows = session.execute(
        select(KpiValue.kpi_id, func.max(KpiValue.id)).where(KpiValue.kpi_id.in_(kpi_ids)).group_by(KpiValue.kpi_id)
    ).all()
    latest_ids = [r[1] for r in rows]
    if not latest_ids:
        return {}
    values = session.execute(select(KpiValue.kpi_id, KpiValue.value).where(KpiValue.id.in_(latest_ids))).all()
    return {r[0]: r[1] for r in values}


def kpi_value_history(session: Session, kpi_id: int, *, limit: int = 50) -> list[KpiValue]:
    return list(session.scalars(
        select(KpiValue).where(KpiValue.kpi_id == kpi_id).order_by(KpiValue.id.desc()).limit(limit)
    ))


# ----------------------------------------------------------------- custom reports
def create_report(session: Session, **kw) -> CustomReport:
    r = CustomReport(**kw)
    session.add(r)
    session.flush()
    return r


def get_report(session: Session, report_id: int) -> CustomReport | None:
    return session.get(CustomReport, report_id)


def list_reports(session: Session, *, owner_id: int | None = None, status: str | None = None) -> list[CustomReport]:
    q = select(CustomReport)
    filters = []
    if owner_id is not None:
        filters.append(CustomReport.owner_id == owner_id)
    if status:
        filters.append(CustomReport.status == status)
    if filters:
        q = q.where(and_(*filters))
    return list(session.scalars(q.order_by(CustomReport.id.desc())))


def delete_report(session: Session, report_id: int) -> bool:
    r = session.get(CustomReport, report_id)
    if not r:
        return False
    session.delete(r)
    return True


def report_status_counts(session: Session) -> dict[str, int]:
    rows = session.execute(select(CustomReport.status, func.count(CustomReport.id)).group_by(CustomReport.status)).all()
    return {r[0]: r[1] for r in rows}


# ----------------------------------------------------------------- report schedules
def create_schedule(session: Session, **kw) -> ReportSchedule:
    s = ReportSchedule(**kw)
    session.add(s)
    session.flush()
    return s


def get_schedule(session: Session, schedule_id: int) -> ReportSchedule | None:
    return session.get(ReportSchedule, schedule_id)


def list_schedules(session: Session, *, report_id: int | None = None) -> list[ReportSchedule]:
    q = select(ReportSchedule)
    if report_id is not None:
        q = q.where(ReportSchedule.report_id == report_id)
    return list(session.scalars(q.order_by(ReportSchedule.id.desc())))


def due_schedules(session: Session) -> list[ReportSchedule]:
    return list(session.scalars(select(ReportSchedule).where(ReportSchedule.is_enabled.is_(True))))


def count_active_schedules(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(ReportSchedule).where(ReportSchedule.is_enabled.is_(True))
    ) or 0


def delete_schedule(session: Session, schedule_id: int) -> bool:
    s = session.get(ReportSchedule, schedule_id)
    if not s:
        return False
    session.delete(s)
    return True


# ----------------------------------------------------------------- scheduled report runs
def create_run(session: Session, **kw) -> ScheduledReportRun:
    r = ScheduledReportRun(**kw)
    session.add(r)
    session.flush()
    return r


def list_runs(session: Session, *, schedule_id: int | None = None, limit: int = 50) -> list[ScheduledReportRun]:
    q = select(ScheduledReportRun)
    if schedule_id is not None:
        q = q.where(ScheduledReportRun.schedule_id == schedule_id)
    return list(session.scalars(q.order_by(ScheduledReportRun.id.desc()).limit(limit)))


