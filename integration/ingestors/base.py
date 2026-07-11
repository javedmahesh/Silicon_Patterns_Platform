"""BaseIngestor — shared machinery for every engine ingestor.

Responsibilities:
  * open an ``ingestion_runs`` audit row, finalize it with counts + status;
  * read the source (a file via :mod:`integration.ingestors.readers`, OR an
    in-memory list of rows via :meth:`ingest_rows` — used by the Supabase adapter);
  * iterate rows with per-row error isolation (one bad row never aborts a run);
  * resolve company identity through :class:`~integration.resolver.CompanyResolver`;
  * idempotent upserts so re-running a source updates in place (never duplicates).

Subclasses implement :meth:`process_row` and declare ``engine_name``. They never
touch tables they do not own.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from integration.ingestors.readers import read_rows
from integration.resolver import CompanyResolver, Resolution
from master_db.models import IngestionRun

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class RowResult:
    """What happened to one source row."""

    written: bool = False        # an engine row was inserted/updated
    review_queued: bool = False  # a resolution review item was created
    rejected: bool = False       # the row could not be ingested
    duplicate: bool = False      # the row matched a record already in the table
    reason: str = ""
    # Bulk path only: the resolved values dict to upsert (None = skip this row).
    values: dict[str, Any] | None = None


@dataclass(slots=True)
class IngestionResult:
    """Aggregate outcome of an ingest() call (also persisted to ingestion_runs)."""

    engine: str
    source_path: str = ""
    rows_in: int = 0
    rows_upserted: int = 0
    rows_rejected: int = 0
    rows_review_queued: int = 0
    rows_duplicate: int = 0
    status: str = "success"
    notes: str = ""
    errors: list[str] = field(default_factory=list)


class BaseIngestor:
    engine_name: str = "base"
    # High-volume ingestors set these to opt into a single bulk upsert instead of
    # per-row writes. They implement build_row() (resolve + map, no write).
    bulk_model: type | None = None
    bulk_conflict: tuple[str, ...] = ()

    def __init__(
        self,
        session: Session,
        *,
        resolver: CompanyResolver | None = None,
        create_stub: bool = True,
        mode: str = "standalone",
    ) -> None:
        self.session = session
        self.resolver = resolver or CompanyResolver(session)
        self.create_stub = create_stub
        self.mode = mode

    # ------------------------------------------------------------------ run

    def ingest(self, source_path: str | Path) -> IngestionResult:
        """Read *source_path* (file) and ingest its rows."""
        result = IngestionResult(engine=self.engine_name, source_path=str(source_path))
        try:
            rows = self.read(source_path)
        except FileNotFoundError:
            return self._fail(result, f"source not found: {source_path}")
        except Exception as exc:  # malformed file, etc.
            logger.exception("[%s] failed to read %s", self.engine_name, source_path)
            return self._fail(result, f"could not read source: {exc}")
        result.notes = self._stale_source_note(source_path)
        return self._execute(rows, str(source_path), result)

    def _stale_source_note(self, source_path: str | Path) -> str:
        """Flag when *source_path* has not changed since the last successful
        ingest of this exact file — a strong signal the upstream engine was not
        re-run (e.g. ``run all`` without ``--run-engine``), so this ingest can
        only re-confirm already-known records and no new discovery is possible.

        Purely informational (surfaces in ``pipeline_runs.notes``); it never
        rejects rows or blocks the ingest.
        """
        try:
            mtime = datetime.fromtimestamp(Path(source_path).stat().st_mtime, tz=timezone.utc)
        except OSError:
            return ""
        prior = self.session.scalar(
            select(IngestionRun.finished_at)
            .where(
                IngestionRun.engine == self.engine_name,
                IngestionRun.source_path == str(source_path),
                IngestionRun.status.in_(("success", "partial")),
                IngestionRun.finished_at.is_not(None),
            )
            .order_by(IngestionRun.run_id.desc())
        )
        if prior is None:
            return ""
        prior_utc = prior if prior.tzinfo is not None else prior.replace(tzinfo=timezone.utc)
        if mtime <= prior_utc:
            return (
                f"source unchanged since last ingest ({prior_utc.isoformat(timespec='seconds')}) "
                "- upstream engine likely not re-run; no new discovery is possible from this file"
            )
        return ""

    def ingest_rows(self, rows: list[dict[str, Any]], source_label: str = "") -> IngestionResult:
        """Ingest an in-memory list of rows (e.g. fetched from Supabase REST)."""
        result = IngestionResult(engine=self.engine_name, source_path=source_label)
        return self._execute(rows, source_label, result)

    def _execute(
        self, rows: list[dict[str, Any]], source_label: str, result: IngestionResult
    ) -> IngestionResult:
        run = IngestionRun(
            engine=self.engine_name, mode=self.mode, status="running", source_path=source_label
        )
        self.session.add(run)
        self.session.flush()

        result.rows_in = len(rows)
        if self.bulk_model is not None:
            self._run_bulk(rows, result)
        else:
            self._run_per_row(rows, result)

        result.status = "success" if result.rows_rejected == 0 else "partial"
        self._finalize(run, result)
        logger.info(
            "[%s] in=%d upserted=%d rejected=%d review=%d dup=%d (%s)",
            self.engine_name, result.rows_in, result.rows_upserted, result.rows_rejected,
            result.rows_review_queued, result.rows_duplicate, result.status,
        )
        return result

    def _run_per_row(self, rows: list[dict[str, Any]], result: IngestionResult) -> None:
        for i, row in enumerate(rows):
            try:
                outcome = self.process_row(row)
            except Exception as exc:  # isolate one bad row
                result.rows_rejected += 1
                msg = f"row {i}: {exc}"
                result.errors.append(msg)
                logger.warning("[%s] %s", self.engine_name, msg)
                continue
            if outcome.written:
                result.rows_upserted += 1
            if outcome.duplicate:
                result.rows_duplicate += 1
            if outcome.review_queued:
                result.rows_review_queued += 1
            if outcome.rejected and not outcome.written:
                result.rows_rejected += 1

    def _run_bulk(self, rows: list[dict[str, Any]], result: IngestionResult) -> None:
        """Resolve every row via build_row(), then upsert the batch in ONE statement.

        created/updated are derived from a before/after row count (one bulk write
        can't report per-row insert-vs-update), so duplicate = upserted - created.
        """
        from master_db.bulk import bulk_upsert

        before = self.session.scalar(select(func.count()).select_from(self.bulk_model)) or 0
        collected: dict[tuple, dict[str, Any]] = {}
        for i, row in enumerate(rows):
            try:
                outcome = self.build_row(row)
            except Exception as exc:
                result.rows_rejected += 1
                result.errors.append(f"row {i}: {exc}")
                logger.warning("[%s] %s", self.engine_name, str(exc))
                continue
            if outcome.review_queued:
                result.rows_review_queued += 1
            if outcome.values is None:
                if outcome.rejected:
                    result.rows_rejected += 1
                continue
            key = tuple(outcome.values[c] for c in self.bulk_conflict)
            collected[key] = outcome.values  # de-dupe within the batch, last wins

        rowdicts = list(collected.values())
        if rowdicts:
            bulk_upsert(self.session, self.bulk_model, rowdicts, list(self.bulk_conflict))
            self.session.flush()
        after = self.session.scalar(select(func.count()).select_from(self.bulk_model)) or 0
        created = max(0, after - before)
        result.rows_upserted = len(rowdicts)
        result.rows_duplicate = max(0, len(rowdicts) - created)

    def _fail(self, result: IngestionResult, msg: str) -> IngestionResult:
        run = IngestionRun(
            engine=self.engine_name, mode=self.mode, status="running", source_path=result.source_path
        )
        self.session.add(run)
        self.session.flush()
        result.status = "failed"
        result.notes = msg
        self._finalize(run, result)
        logger.warning("[%s] %s", self.engine_name, msg)
        return result

    def _finalize(self, run: IngestionRun, result: IngestionResult) -> None:
        run.rows_in = result.rows_in
        run.rows_upserted = result.rows_upserted
        run.rows_rejected = result.rows_rejected
        run.rows_review_queued = result.rows_review_queued
        run.status = result.status
        run.notes = result.notes
        run.finished_at = _utcnow()
        self.session.commit()

    # ------------------------------------------------------------------ hooks

    def read(self, source_path: str | Path) -> list[dict[str, Any]]:
        return read_rows(source_path)

    def process_row(self, row: dict[str, Any]) -> RowResult:  # pragma: no cover
        """Per-row path: resolve AND write, return a RowResult. (default ingestors)"""
        raise NotImplementedError

    def build_row(self, row: dict[str, Any]) -> RowResult:  # pragma: no cover
        """Bulk path: resolve + map only (no write); return RowResult with .values
        set (or None to skip). Used when bulk_model is declared."""
        raise NotImplementedError

    # --------------------------------------------------------------- helpers

    def resolve(
        self,
        *,
        domain: str | None = None,
        name: str | None = None,
        website: str | None = None,
        source_ref: str = "",
    ) -> Resolution:
        return self.resolver.resolve(
            domain=domain, name=name, website=website,
            source_engine=self.engine_name, source_ref=source_ref,
            create_stub=self.create_stub,
        )

    def upsert(self, model: type, pk_value: Any, values: dict[str, Any]):
        """Insert or update *model* by primary-key value. Idempotent."""
        obj = self.session.get(model, pk_value)
        if obj is None:
            obj = model(**values)
            self.session.add(obj)
        else:
            for key, value in values.items():
                setattr(obj, key, value)
        self.session.flush()
        return obj

    def upsert_by(self, model: type, column, value: Any, values: dict[str, Any]) -> tuple[Any, bool]:
        """Insert or update *model* by a unique non-PK column (e.g. linkedin_url).

        Returns ``(obj, existed)`` where ``existed`` is True when a row was already
        present (i.e. this was a duplicate/update, not a fresh insert).
        """
        obj = self.session.scalar(select(model).where(column == value))
        existed = obj is not None
        if obj is None:
            obj = model(**values)
            self.session.add(obj)
        else:
            for key, val in values.items():
                setattr(obj, key, val)
        self.session.flush()
        return obj, existed

    # --- value coercion (CSV gives strings; JSON gives native types) ---

    @staticmethod
    def s(value: Any) -> str:
        return "" if value is None else str(value).strip()

    @staticmethod
    def i(value: Any, default: int = 0) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def f(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def b(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}
