"""End-to-end validation of production-only functionality against real Postgres.

Safe to run back-to-back against the same live Postgres/Supabase project: every run
resets a dedicated `sp_validation` SCHEMA (dropped + recreated up front, dropped again
on exit) and points every connection at it via the DSN's `options=-c search_path=...`.
Migrations, seed data, and every check below land only in `sp_validation` — `public`
and any other existing schema/table/data are never dropped, truncated, or altered.

    # PowerShell
    $env:DATABASE_URL = "postgresql://user:pass@host:5432/dbname"
    python scripts/validate_postgres.py

Optional: $env:SEED_N = "10000"  (companies to seed; default 10000)

Covers, in order: (0) static model<->migration parity (no DB connection — run
scripts/check_migration_model_parity.py first as a fast fail before touching a real
DB), (1) every migration file present (globbed, not a fixed range — currently
0001-0040), (2) pg_trgm, (3) resolver index plan, (4) bulk upserts, (5) Enterprise CRM
Phase 6-13 smoke CRUD (workflow, custom object/record, AI insight, org, webhook, KB
article, KPI — the schema those phases actually added, exercised against the live
migrations rather than just applying them), (6) API, (7) orchestrator, (8) lead scoring.
"""
from __future__ import annotations

import atexit
import os
from dotenv import load_dotenv
import random
import string
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

env_file = ROOT / ".env"
load_dotenv(env_file)

RAW = os.environ.get("DATABASE_URL", "").strip()
if not RAW:
    print('ERROR: set DATABASE_URL, e.g. $env:DATABASE_URL = "postgresql://user:pass@host:5432/db"')
    raise SystemExit(2)
PG_URL = RAW.replace("postgresql+psycopg://", "postgresql://", 1)
SA_URL = RAW if RAW.startswith("postgresql+psycopg://") else RAW.replace("postgresql://", "postgresql+psycopg://", 1)
SEED_N = int(os.environ.get("SEED_N", "10000"))

import psycopg
from psycopg.pq import ExecStatus
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from integration.normalizer import canonical_company_id, name_key
from integration.resolver import CompanyResolver
from master_db.bulk import bulk_upsert
from master_db.models import Company, DecisionMaker, LeadScore, PipelineRun

MIGRATIONS = ROOT / "master_db" / "migrations"
VALIDATION_SCHEMA = "sp_validation"  # dedicated + disposable; only this script ever drops it


def section(t: str) -> None:
    print(f"\n{'=' * 4} {t} {'=' * 4}")


def _with_search_path(url: str, schema: str) -> str:
    """Bake `-c search_path=<schema>,public` into a DSN via libpq's `options` param, so
    every connection opened from this URL — including the API's own internal engine,
    built from this same SA_URL in the section below — lands in the isolated schema
    with no changes needed anywhere else. `public` stays second so pg_trgm's operator
    classes still resolve."""
    opt = urllib.parse.quote(f"-c search_path={schema},public", safe="")
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}options={opt}"


def _drop_validation_schema() -> None:
    try:
        with psycopg.connect(PG_URL, autocommit=True) as conn:
            conn.execute(f"DROP SCHEMA IF EXISTS {VALIDATION_SCHEMA} CASCADE")
        section(f"CLEANUP — `{VALIDATION_SCHEMA}` dropped, no validation artifacts left behind")
    except Exception as exc:  # best-effort — never mask the real validation result
        section(f"CLEANUP WARNING — drop failed ({exc}); next run's reset removes it regardless")


# --- 0. static parity (no DB connection — fail fast before touching Postgres) --------
section("0. STATIC MODEL <-> MIGRATION PARITY (no DB connection)")
from scripts.check_migration_model_parity import main as check_parity
if check_parity() != 0:
    print("  FAILED — fix drift (see above) before validating against a live database.")
    raise SystemExit(1)

# --- isolation: reset a dedicated schema before anything else touches Postgres -------
# Migrations are a forward-only ledger, not all individually guarded for reruns (e.g.
# 0023's `ADD COLUMN` has no `IF NOT EXISTS` — correct for a single clean 0001->0040
# replay, but errors if replayed again against a database that already has the column).
# A fresh schema every run sidesteps that, instead of patching migrations to compensate
# for validator state.
section(f"ISOLATION — resetting dedicated schema `{VALIDATION_SCHEMA}`")
with psycopg.connect(PG_URL, autocommit=True) as _boot:
    _boot.execute(f"DROP SCHEMA IF EXISTS {VALIDATION_SCHEMA} CASCADE")
    _boot.execute(f"CREATE SCHEMA {VALIDATION_SCHEMA}")
print(f"  `{VALIDATION_SCHEMA}` dropped + recreated — clean slate; no other schema touched")

PG_URL = _with_search_path(PG_URL, VALIDATION_SCHEMA)
SA_URL = _with_search_path(SA_URL, VALIDATION_SCHEMA)
atexit.register(_drop_validation_schema)  # success, SystemExit, and uncaught exceptions all trigger this

# --- 1. migrations -------------------------------------------------------
_migration_files = sorted(MIGRATIONS.glob("0*.sql"))
section(f"1. MIGRATIONS {_migration_files[0].stem[:4]}-{_migration_files[-1].stem[:4]} ({len(_migration_files)} files)")
with psycopg.connect(PG_URL, autocommit=True) as conn:
    for sql_file in _migration_files:
        res = conn.pgconn.exec_(sql_file.read_text(encoding="utf-8").encode("utf-8"))
        ok = res.status in (ExecStatus.COMMAND_OK, ExecStatus.TUPLES_OK)
        if ok:
            print(f"  {sql_file.name}: OK")
        else:
            print(f"  {sql_file.name}: FAILED -> {res.error_message.decode(errors='replace')}")
            raise SystemExit(1)

# --- 2. pg_trgm ----------------------------------------------------------
section("2. pg_trgm EXTENSION + TRIGRAM INDEXES")
with psycopg.connect(PG_URL) as conn:
    ext = conn.execute("SELECT extname, extversion FROM pg_extension WHERE extname='pg_trgm'").fetchone()
    print(f"  pg_trgm installed: {ext}")
    idx = conn.execute(
        "SELECT indexname, CASE WHEN indexdef ILIKE '%gist%' THEN 'gist' ELSE 'gin' END AS kind "
        f"FROM pg_indexes WHERE indexdef ILIKE '%trgm_ops%' AND schemaname = '{VALIDATION_SCHEMA}' ORDER BY indexname"
    ).fetchall()
    print(f"  trigram indexes: {[(r[0], r[1]) for r in idx]}")

engine = create_engine(SA_URL, future=True, pool_pre_ping=True)
SM = sessionmaker(bind=engine, future=True, expire_on_commit=False)

# --- seed ----------------------------------------------------------------
section(f"SEED {SEED_N} companies (bulk) + ANALYZE")
# DIVERSE names so trigram similarity is SELECTIVE (real company names are). Uniform
# names make `name_key % x` match ~everything -> planner correctly seq-scans (the
# earlier artifact). A seed makes this reproducible.
random.seed(42)
_SUFFIX = ["systems", "labs", "micro", "semiconductors", "technologies", "networks",
           "devices", "silicon", "logic", "works", "dynamics", "integrated"]


def _diverse_name(i: int) -> str:
    tok = "".join(random.choices(string.ascii_lowercase, k=random.randint(6, 10)))
    return f"{tok} {random.choice(_SUFFIX)}"


with SM() as s:
    s.execute(text("TRUNCATE companies CASCADE"))
    s.commit()
    rows = []
    for i in range(SEED_N):
        nm = _diverse_name(i)
        rows.append(dict(company_domain=f"co{i}.example",
                         canonical_company_id=canonical_company_id(f"co{i}.example", nm),
                         company_name=nm, name_key=name_key(nm), validation_status="VALID"))
    t0 = time.perf_counter()
    bulk_upsert(s, Company, rows, ["company_domain"])
    s.commit()
    print(f"  inserted {SEED_N} diverse-named companies in {time.perf_counter() - t0:.2f}s")
    # A few realistic known companies for match probes.
    known = [("tenstorrent.com", "Tenstorrent"), ("cerebras.net", "Cerebras Systems"),
             ("untether.ai", "Untether AI"), ("groq.com", "Groq"), ("sambanova.ai", "SambaNova Systems")]
    bulk_upsert(s, Company, [dict(company_domain=d, canonical_company_id=canonical_company_id(d, n),
                company_name=n, name_key=name_key(n), company_tier="SCALEUP",
                prospect_type="PRODUCT_COMPANY", compliance_flag="APPROVED", validation_status="VALID")
                for d, n in known], ["company_domain"])
    s.commit()
    s.execute(text("ANALYZE companies"))
    s.commit()

# --- 3. query plan -------------------------------------------------------
section("3. QUERY PLAN — resolver KNN (expect index-ordered GiST scan, no sort)")
_EXPLAIN = ("EXPLAIN (ANALYZE, BUFFERS) SELECT company_domain, name_key <-> :k AS dist "
            "FROM companies WHERE name_key <> '' ORDER BY name_key <-> :k LIMIT 1")
with SM() as s:
    plan = "\n".join("    " + r[0] for r in s.execute(text(_EXPLAIN), {"k": "tenstorent"}).fetchall())
    print(plan)
    used = "ix_companies_name_key_gist" in plan
    sorted_in_mem = "Sort Key" in plan
    print("  -> GiST KNN index used:", "YES" if used else "NO")
    print("  -> full sort avoided (index-ordered):", "YES" if (used and not sorted_in_mem) else "NO")

# --- 4. resolver perf ----------------------------------------------------
section("4. RESOLVER PERFORMANCE (GiST KNN, index-ordered)")
with SM() as s:
    r = CompanyResolver(s)
    M = 200
    t0 = time.perf_counter()
    for j in range(M):
        r._fuzzy_find(f"zzqprobe{j} aerospace")  # selective — matches ~nothing, so the index does the work
    ms = (time.perf_counter() - t0) / M * 1000
    print(f"  {M} selective resolves over {SEED_N} companies: {ms:.2f} ms/resolve")
    print("  (each includes one client<->DB round-trip to the remote pooler — server cost is the EXPLAIN time)")
    print(f"  correctness — typo 'tenstorent' resolves to: {r._fuzzy_find('tenstorent')}")

# --- 5. bulk upserts -----------------------------------------------------
section("5. BULK UPSERT PERFORMANCE (decision_makers)")
dms = [dict(linkedin_url=f"https://lnkd.in/{i}", company_domain=None, resolved_company_name="X",
            first_name=f"P{i}", last_name="", headline="", current_title="Engineer", seniority="",
            location="", match_score=50.0, agent_score=None, agent_reasoning="", status="sourced",
            profile_data={}, source="linkedin") for i in range(5000)]
SAMPLE = 150
with SM() as s:  # per-row sample (the OLD pattern) — round-trip bound on remote PG
    s.execute(text("DELETE FROM decision_makers")); s.commit()
    t0 = time.perf_counter()
    for d in dms[:SAMPLE]:
        if s.scalar(select(DecisionMaker).where(DecisionMaker.linkedin_url == d["linkedin_url"])) is None:
            s.add(DecisionMaker(**d))
        s.flush()
    s.commit(); per_row = time.perf_counter() - t0
with SM() as s:
    s.execute(text("DELETE FROM decision_makers")); s.commit()
    t0 = time.perf_counter(); bulk_upsert(s, DecisionMaker, dms[:SAMPLE], ["linkedin_url"]); s.commit()
    bulk_s = time.perf_counter() - t0
print(f"  {SAMPLE} rows: per-row {per_row * 1000:.0f} ms vs bulk {bulk_s * 1000:.0f} ms -> {per_row / bulk_s:.0f}x faster (remote PG, round-trip bound)")
with SM() as s:
    s.execute(text("DELETE FROM decision_makers")); s.commit()
    t0 = time.perf_counter(); bulk_upsert(s, DecisionMaker, dms, ["linkedin_url"]); s.commit()
    t_ins = time.perf_counter() - t0
    t0 = time.perf_counter(); bulk_upsert(s, DecisionMaker, dms, ["linkedin_url"]); s.commit()
    t_upd = time.perf_counter() - t0
    print(f"  5000 inserts: {t_ins * 1000:.0f} ms | 5000 conflict-updates: {t_upd * 1000:.0f} ms")
    print(f"  decision_makers count (idempotent — expect 5000): {s.scalar(select(func.count()).select_from(DecisionMaker))}")

# --- 5. Enterprise CRM Phase 6-13 smoke CRUD ------------------------------
# Applying the migrations only proves the DDL is syntactically valid — it does not
# prove the ORM models actually match what got created (see migrations 0037/0038,
# both found by exactly this gap: DDL that "applied" but didn't match models.py).
# One representative insert+read per phase's core table closes that gap.
section("5. ENTERPRISE CRM PHASE 6-13 SMOKE CRUD (workflow/custom-object/AI/admin/integration/search/BI)")
from master_db.models import (
    AiInsight, CustomObject, CustomRecord, Integration, KbArticle, Kpi,
    Organization, Webhook, Workflow,
)
with SM() as s:
    s.execute(text("TRUNCATE workflows, custom_objects, ai_insights, organizations, "
                    "integrations, kb_articles, kpis CASCADE"))
    s.commit()
    wf = Workflow(name="smoke", trigger_event="deal_created", conditions={}, actions=[])
    s.add(wf); s.flush()
    obj = CustomObject(name="Smoke Object", api_name="smoke_object", status="active")
    s.add(obj); s.flush()
    s.add(CustomRecord(object_id=obj.id, data={"x": 1}))
    s.add(AiInsight(insight_type="deal", entity_type="deal", entity_id="1", title="smoke", severity="low", confidence="low"))
    s.add(Organization(name="Smoke Org", slug="smoke-org"))
    integ = Integration(name="Smoke Integration", category="crm", status="active")
    s.add(integ); s.flush()
    s.add(Webhook(name="smoke", event_type="*", target_url="https://example.com/hook", secret="x"))
    s.add(KbArticle(title="Smoke Article", body="x", status="draft"))
    s.add(Kpi(name="Smoke KPI", category="sales"))
    s.commit()
    counts = {
        "workflows": s.scalar(select(func.count()).select_from(Workflow)),
        "custom_objects": s.scalar(select(func.count()).select_from(CustomObject)),
        "custom_records": s.scalar(select(func.count()).select_from(CustomRecord)),
        "ai_insights": s.scalar(select(func.count()).select_from(AiInsight)),
        "organizations": s.scalar(select(func.count()).select_from(Organization)),
        "integrations": s.scalar(select(func.count()).select_from(Integration)),
        "webhooks": s.scalar(select(func.count()).select_from(Webhook)),
        "kb_articles": s.scalar(select(func.count()).select_from(KbArticle)),
        "kpis": s.scalar(select(func.count()).select_from(Kpi)),
    }
    print(f"  inserted + read back 1 row in each of: {counts}")
    assert all(v == 1 for v in counts.values()), f"expected 1 row each, got {counts}"
    print("  OK — Phase 6-13 ORM models match the live Postgres schema")

# --- 6/7. scoring + orchestrator ----------------------------------------
section("6+7. LEAD SCORING + ORCHESTRATOR on Postgres")
with SM() as s:
    s.execute(text(
        "INSERT INTO demand_signals (company_domain, demand_score, lead_readiness_score, total_engineering_jobs) "
        "VALUES ('tenstorrent.com', 90, 70, 40) "
        "ON CONFLICT (company_domain) DO UPDATE SET demand_score = EXCLUDED.demand_score"
    ))
    s.commit()
    from lead_scoring.service import score_all
    from orchestrator.orchestrator import Orchestrator

    t0 = time.perf_counter()
    summ = score_all(s)
    print(f"  lead scoring: scored {summ.scored} companies in {time.perf_counter() - t0:.2f}s; grades={summ.grade_counts}")
    res = Orchestrator(s).run_stage("scoring")
    print(f"  orchestrator scoring stage: status={res.status}, processed={res.processed}")
    print(f"  pipeline_runs rows: {s.scalar(select(func.count()).select_from(PipelineRun))}")
    print(f"  lead_scores rows:   {s.scalar(select(func.count()).select_from(LeadScore))}")

# --- API -----------------------------------------------------------------
section("API on Postgres (in-process TestClient)")
from backend.config import Settings
from backend.main import create_app
from fastapi.testclient import TestClient

# dev_auth_bypass=True keeps these smoke reads open: now that Microsoft Entra ID is
# configured in .env, the zero-config bypass is off by default (security._bypass_on),
# so an unauthenticated /companies would 401. This throwaway in-process app (isolated
# sp_validation schema) just checks the data endpoints answer over Postgres — it isn't
# exercising auth, which has its own test suite.
app = create_app(Settings(database_url=SA_URL, log_json=False, dev_auth_bypass=True))
with TestClient(app) as c:
    print("  GET /health:", c.get("/health").json())
    print("  GET /companies total:", c.get("/companies").json()["total"])
    a = c.get("/analytics/summary").json()
    print(f"  GET /analytics/summary: companies={a['total_companies']} leads={a['total_leads']} grades={a['grade_distribution']}")

print("\n==== VALIDATION COMPLETE ====")
