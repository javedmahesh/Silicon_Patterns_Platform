"""Runtime-editable Standard Run schedule.

The schedule (run times / enabled / grace) DEFAULTS from the environment
(SP_SCHEDULE_TIMES, SP_SCHEDULER_ENABLED, SP_SCHEDULE_GRACE_MINUTES) but is
overridable at runtime from the Scheduler page, so operators can retime the
automated runs to suit them without a redeploy. The override persists in the
generic ``system_settings`` table (category='platform', key='scheduler') — no new
table — and the scheduler thread re-reads it every tick, so a change takes effect
within one tick.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import Settings
from master_db.models import SystemSetting

_CATEGORY = "platform"
_KEY = "scheduler"


@dataclass(slots=True)
class SchedulerConfig:
    schedule_times: list[str]
    enabled: bool
    grace_minutes: int


def parse_times(values) -> list[str]:
    """Normalize a list (or comma-string) of ``HH:MM`` slots — validated, de-duped,
    sorted. Raises ``ValueError`` on a malformed or out-of-range time."""
    if isinstance(values, str):
        values = values.split(",")
    out: list[str] = []
    for tok in values or []:
        tok = str(tok).strip()
        if not tok:
            continue
        parts = tok.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid time '{tok}' — use HH:MM (24-hour).")
        try:
            h, m = int(parts[0]), int(parts[1])
        except ValueError:
            raise ValueError(f"Invalid time '{tok}' — use HH:MM (24-hour).")
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError(f"Invalid time '{tok}' — hours 00–23, minutes 00–59.")
        out.append(f"{h:02d}:{m:02d}")
    return sorted(dict.fromkeys(out))


def _row(session: Session) -> SystemSetting | None:
    return session.scalar(
        select(SystemSetting).where(SystemSetting.category == _CATEGORY, SystemSetting.key == _KEY)
    )


def read_config(session: Session, settings: Settings) -> SchedulerConfig:
    """Effective config = the persisted override layered over the env defaults."""
    row = _row(session)
    v = row.value if row and isinstance(row.value, dict) else {}
    raw_times = v.get("schedule_times")
    try:
        times = parse_times(raw_times) if raw_times else list(settings.schedule_times)
    except ValueError:
        times = list(settings.schedule_times)   # a corrupt stored value never breaks the tick
    enabled = settings.scheduler_enabled if v.get("enabled") is None else bool(v.get("enabled"))
    grace = settings.schedule_grace_minutes if v.get("grace_minutes") is None else int(v.get("grace_minutes"))
    return SchedulerConfig(schedule_times=times, enabled=enabled, grace_minutes=max(0, grace))


def write_config(session: Session, *, schedule_times, enabled: bool, grace_minutes: int,
                 actor_id: int | None = None) -> SchedulerConfig:
    """Validate + persist the override. Raises ``ValueError`` on bad input."""
    times = parse_times(schedule_times)
    if not times:
        raise ValueError("Add at least one run time (HH:MM).")
    grace = max(0, int(grace_minutes))
    value = {"schedule_times": times, "enabled": bool(enabled), "grace_minutes": grace}
    row = _row(session)
    if row is None:
        session.add(SystemSetting(category=_CATEGORY, key=_KEY, value=value, updated_by=actor_id))
    else:
        row.value = value
        row.updated_by = actor_id
    session.commit()
    return SchedulerConfig(schedule_times=times, enabled=bool(enabled), grace_minutes=grace)
