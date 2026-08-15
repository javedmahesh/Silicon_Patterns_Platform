"""Standard Run scheduler — a background thread that fires the Standard Run at each
configured slot (SP_SCHEDULE_TIMES, default 09:00 & 21:00 server-local time).

Design goals from the phase spec, and how each is met:
  * starts automatically with the backend  → started from the app lifespan (main.py).
  * survives backend restarts               → each slot is fired at most once per day;
                                               "already fired" is decided from the
                                               persisted pipeline_executions rows, so a
                                               restart never re-fires a done slot.
  * graceful recovery after restart         → a slot missed while the process was down
                                               still fires when it returns within the
                                               grace window (SP_SCHEDULE_GRACE_MINUTES).
  * prevents overlapping executions         → execute_standard_run holds an advisory /
                                               in-process lock; the scheduler also won't
                                               start a slot whose run row already exists.
  * unique run id / start / finish / etc.   → all recorded by execute_standard_run.

Times are interpreted in the server's local timezone (what a human means by "09:00");
all timestamp math is done in UTC internally so SQLite (naive) and Postgres (aware)
compare correctly.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend.config import Settings
from backend.scheduler_config import read_config
from backend.standard_run import RunInProgress, execute_standard_run, reap_stale_runs
from master_db.models import PipelineExecution

logger = logging.getLogger("backend.scheduler")

_TICK_SECONDS = 20


def _as_utc(dt: datetime | None) -> datetime | None:
    """Normalize a DB timestamp to aware-UTC. SQLite hands back naive UTC; Postgres
    hands back aware — this makes both comparable without a mismatch error."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _slot_today_utc(now_local: datetime, slot: str) -> datetime:
    """Today's occurrence of 'HH:MM' (local) as an aware-UTC instant."""
    h, m = (int(x) for x in slot.split(":"))
    return now_local.replace(hour=h, minute=m, second=0, microsecond=0).astimezone(timezone.utc)


class PipelineScheduler:
    def __init__(self, sessionmaker, settings: Settings) -> None:
        self._sessionmaker = sessionmaker
        self._settings = settings
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    # ------------------------------------------------------------- lifecycle
    def start(self) -> None:
        if not self._settings.scheduler_enabled:
            logger.info("Standard Run scheduler DISABLED (SP_SCHEDULER_ENABLED=false)")
            return
        if self._thread is not None and self._thread.is_alive():
            return
        # A run interrupted by the restart that just brought us up is still marked
        # 'running'; close it out before the first tick so it can't masquerade as live.
        try:
            with self._sessionmaker() as session:
                reaped = reap_stale_runs(session)
            if reaped:
                logger.info("marked %d abandoned Standard Run(s) as failed on startup", reaped)
        except Exception:   # never let bookkeeping stop the scheduler from starting
            logger.exception("stale-run reap failed (continuing)")
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="standard-run-scheduler", daemon=True)
        self._thread.start()
        logger.info(
            "Standard Run scheduler STARTED — slots=%s (server-local), grace=%dmin",
            ",".join(self._settings.schedule_times) or "(none)", self._settings.schedule_grace_minutes,
        )

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------- loop
    def _loop(self) -> None:
        # Event.wait returns True the moment stop() is called, False on timeout — so
        # this both paces the ticks and shuts down promptly on backend teardown.
        while not self._stop.wait(_TICK_SECONDS):
            try:
                self._tick()
            except Exception:  # a bad tick must never kill the scheduler
                logger.exception("scheduler tick failed (continuing)")

    def _window(self, grace_minutes: int) -> timedelta:
        # Grace controls how late a MISSED slot may still fire; floor it above a few
        # ticks so a normal on-time fire is always caught.
        return max(timedelta(minutes=grace_minutes), timedelta(seconds=_TICK_SECONDS * 3))

    def _reap(self, session) -> None:
        """Close out abandoned runs. Bookkeeping — never allowed to stop a tick.

        Runs on every tick, not only at startup: the run that most needs reaping is the
        one the restart just killed, and at startup it is seconds old — far younger than
        STALE_RUN_AFTER — so the boot pass always skips it. Ticking catches it once it is
        provably dead, which is what makes the threshold safe to leave at 6 hours.
        Reaping is idempotent and cheap: with nothing stale it is one indexed read.
        """
        try:
            reaped = reap_stale_runs(session)
        except Exception:      # noqa: BLE001 - a bad reap must not cost us the slot
            logger.exception("stale-run reap failed (continuing)")
            return
        if reaped:
            logger.info("marked %d abandoned run row(s) as failed", reaped)

    def _tick(self) -> None:
        now_local = datetime.now().astimezone()
        now_utc = datetime.now(timezone.utc)
        # Re-read the (runtime-editable) schedule every tick, so a change made on the
        # Scheduler page takes effect within one tick — no restart needed.
        with self._sessionmaker() as session:
            self._reap(session)
            cfg = read_config(session, self._settings)
            if not cfg.enabled:
                return
            window = self._window(cfg.grace_minutes)
            for slot in cfg.schedule_times:
                slot_utc = _slot_today_utc(now_local, slot)
                if not (slot_utc <= now_utc <= slot_utc + window):
                    continue
                if self._already_ran(session, slot, slot_utc):
                    continue
                self._fire(session, slot)

    def _already_ran(self, session, slot: str, slot_utc: datetime) -> bool:
        """True if a scheduled run for this slot already started at/after this
        occurrence — the persisted, restart-proof dedup (yesterday's same-slot run
        started ~24h earlier, so it's correctly excluded)."""
        last = session.scalar(
            select(PipelineExecution)
            .where(PipelineExecution.trigger == "scheduled", PipelineExecution.scheduled_slot == slot)
            .order_by(PipelineExecution.id.desc())
        )
        return last is not None and (_as_utc(last.started_at) or slot_utc) >= slot_utc

    def _fire(self, session, slot: str) -> None:
        logger.info("scheduler firing Standard Run for slot %s", slot)
        try:
            execution, _ = execute_standard_run(
                session, self._settings, trigger="scheduled", slot=slot, notify=True,
            )
            logger.info(
                "scheduled run %s complete: status=%s notified=%s(%d)",
                execution.run_id, execution.status, execution.notification_status,
                execution.notified_count,
            )
        except RunInProgress as exc:
            logger.info("scheduler skipped slot %s: %s", slot, exc)
        except Exception:
            logger.exception("scheduled run for slot %s failed", slot)

    # ------------------------------------------------------------- introspection
    def next_run_at(self, times: list[str] | None = None) -> datetime | None:
        """The soonest upcoming slot boundary (aware-UTC), or None if no slots.

        ``times`` lets the caller pass the effective (runtime-overridden) schedule;
        defaults to the env-configured slots when omitted."""
        slots = times if times is not None else self._settings.schedule_times
        if not slots:
            return None
        now_local = datetime.now().astimezone()
        now_utc = datetime.now(timezone.utc)
        candidates: list[datetime] = []
        for slot in slots:
            today = _slot_today_utc(now_local, slot)
            candidates.append(today if today > now_utc else today + timedelta(days=1))
        return min(candidates)
