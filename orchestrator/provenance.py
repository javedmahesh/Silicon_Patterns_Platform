"""Per-run, per-engine record provenance capture.

A Standard Run's orchestrator sets a :class:`ProvenanceRecorder` on the session
(``session.info``) around each stage. Any writer that already holds that session —
the shared ``BaseIngestor`` upsert helpers, the scoring / leadership / engagement
derivations, the news engine — records the canonical records it touched via the
module-level :func:`record` helper, with zero constructor plumbing. Outside a
Standard Run (standalone ingest, tests) no recorder is attached, so every
:func:`record` call is a cheap no-op and nothing changes.

The recorder buffers plain dicts (not ORM objects), so the business writes' own
commits never touch it; the orchestrator flushes the buffer once per stage, only on
success. Flushing is best-effort and never raises into the pipeline — provenance is
an observability aid, not part of the run's correctness.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger("orchestrator.provenance")

_KEY = "run_provenance"


class ProvenanceRecorder:
    def __init__(self, run_id: str, engine: str) -> None:
        self.run_id = run_id
        self.engine = engine
        self._buf: list[dict] = []

    def add(self, entity_table: str, entity_id, operation: str, detail: dict | None = None) -> None:
        if entity_id is None:
            return
        self._buf.append({
            "run_id": self.run_id,
            "engine": self.engine,
            "entity_table": entity_table,
            "entity_id": str(entity_id),
            "operation": operation,
            "detail": detail or {},
        })

    def __len__(self) -> int:
        return len(self._buf)


# --------------------------------------------------------------- lifecycle (orchestrator)
def begin_stage(session: Session, run_id: str, engine: str) -> ProvenanceRecorder:
    """Attach a fresh recorder for one stage of run *run_id*. Returns it (also stored
    on ``session.info`` so writers reach it without being passed the recorder)."""
    rec = ProvenanceRecorder(run_id, engine)
    session.info[_KEY] = rec
    return rec


def detach(session: Session) -> None:
    """Remove the recorder from the session (call in a finally, always)."""
    session.info.pop(_KEY, None)


def flush(session: Session, recorder: ProvenanceRecorder | None) -> int:
    """Persist a stage's buffered references. Best-effort: a failure here is logged
    and swallowed so provenance can never break a run."""
    if not recorder or not len(recorder):
        return 0
    from master_db.models import RunEngineRecord

    try:
        session.bulk_insert_mappings(RunEngineRecord, recorder._buf)
        session.commit()
        return len(recorder)
    except Exception:  # pragma: no cover - observability aid, never fatal
        logger.warning("provenance flush failed for run=%s engine=%s",
                       recorder.run_id, recorder.engine, exc_info=True)
        session.rollback()
        return 0


# --------------------------------------------------------------- writers
def record(session: Session, entity_table: str, entity_id, operation: str,
           detail: dict | None = None) -> None:
    """Record that *engine* (the active stage) touched one canonical record. No-op
    unless a Standard Run attached a recorder to this session."""
    rec = session.info.get(_KEY)
    if rec is not None:
        rec.add(entity_table, entity_id, operation, detail)
