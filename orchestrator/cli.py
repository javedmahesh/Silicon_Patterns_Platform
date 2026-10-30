"""``sp-platform`` — the pipeline orchestrator CLI.

    sp-platform run industry|blog|career|decision_maker_intelligence|scoring|all [--run-engine] [--trigger daily]
    sp-platform run all --resume        # rerun only the stages that didn't succeed
    sp-platform run decision_maker_intelligence --limit 10   # benchmark: first 10 companies only
    sp-platform rerun <component|failed>
    sp-platform status                  # health: last success / failures / durations / next run
    sp-platform runs [--limit N]        # recent pipeline_runs
    sp-platform schedule                # how to wire cron / Task Scheduler

Without `pip install -e .`, invoke as: ``python -m orchestrator.cli <args>``.
"""
from __future__ import annotations

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from backend import repositories as repo
from config.enums import USER_ROLES
from master_db.models import PipelineRun, User
from orchestrator.health import health_report
from orchestrator.orchestrator import Orchestrator, StageResult
from orchestrator.stages import STAGES

app = typer.Typer(name="sp-platform", help="Silicon Patterns platform orchestrator", add_completion=False)
console = Console()

DEFAULT_DB = Path(__file__).resolve().parent.parent / "master_local.db"
_STATUS_COLOR = {"success": "green", "partial": "yellow", "skipped": "cyan", "failed": "red", "running": "blue"}


def _open(db: Path | None = None):
    """Open a Session against the authoritative platform database.

    By default (no ``--db`` override, i.e. ``db`` is ``None`` or the ``DEFAULT_DB``
    sentinel) this resolves through the SAME shared project configuration the
    FastAPI backend uses (backend.config.get_settings() -> DATABASE_URL from the
    root .env; the Supabase Postgres in this deployment) via the identical pooled
    engine (backend.database.Database). The orchestrator no longer reads the raw
    DATABASE_URL environment variable and no longer silently falls back to the local
    SQLite file — so the backend, frontend, and this pipeline always share one
    runtime database. There is exactly one source of truth by default.

    An **explicit** ``--db`` / ``db=`` pointing at a different SQLite file is still
    honored — this is the long-standing CLI contract for tooling and per-test
    isolation (e.g. ``users promote --db /tmp/x.db``). Only a genuine override
    diverts writes; the default never silently splits the runtime database.
    """
    from backend.config import Settings, get_settings
    from backend.database import Database

    if db is not None and Path(db) != DEFAULT_DB:
        settings = Settings(database_url=f"sqlite:///{Path(db).as_posix()}")
    else:
        settings = get_settings()
    return Database(settings).sessionmaker()


def _effective_run_engine(component: str, run_engine: bool | None) -> bool:
    """Decide whether to run the upstream engine (crawl) before ingesting.

    An explicit ``--run-engine`` / ``--no-run-engine`` always wins. When the flag
    is unspecified, a **single-component** run (e.g. ``run industry``) defaults to
    running its engine first — so it performs genuine fresh discovery and then
    ingests the fresh output, instead of silently re-importing a stale CSV. A full
    ``run all`` stays **ingest-only** by default (the scheduler / CI contract:
    engines may be absent, Apify costs money, crawls are slow) unless
    ``--run-engine`` is passed. Stages without an engine (scoring, leadership,
    engagement, decision_maker_intelligence, annual_list, company_news) are
    unaffected either way — the orchestrator only runs an engine when the stage
    declares an ``EngineSpec``."""
    if run_engine is not None:
        return run_engine
    return component != "all"


def _print_results(results: list[StageResult]) -> None:
    table = Table(title="Pipeline run", show_lines=False)
    for col in ("component", "status", "processed", "created", "updated", "review", "ms", "notes"):
        table.add_column(col)
    for r in results:
        color = _STATUS_COLOR.get(r.status, "white")
        table.add_row(r.component, f"[{color}]{r.status}[/{color}]", str(r.processed),
                      str(r.created), str(r.updated), str(r.review), str(r.duration_ms), r.notes[:48])
    console.print(table)


@app.command()
def run(
    component: str = typer.Argument(..., help="industry|blog|career|decision_maker_intelligence|scoring|all"),
    run_engine: bool | None = typer.Option(
        None, "--run-engine/--no-run-engine",
        help="Run the upstream engine (fresh crawl) before ingesting. Default: ON for a "
             "single component (e.g. `run industry` crawls the latest universe, then "
             "ingests), OFF for `run all` (ingest-only unless --run-engine). Pass "
             "--no-run-engine to force a fast ingest-only re-import of existing output.",
    ),
    trigger: str = typer.Option("manual", "--trigger", help="manual|daily|weekly (recorded on the run)"),
    resume: bool = typer.Option(False, "--resume", help="with 'all': rerun only stages that didn't succeed"),
    limit: int | None = typer.Option(
        None, "--limit",
        help="Benchmark mode for decision_maker_intelligence: cap it to the first N "
             "companies (by company_domain) instead of the full universe, and print "
             "a yield/cost report (companies, Apify invocations, leads returned/"
             "inserted/updated/duplicates-ignored, failed batches, runtime). Still "
             "writes to the same configured runtime database as a normal run. Every "
             "other stage, and every run where this is omitted, is unaffected — the "
             "production command (no --limit) behaves exactly as before.",
    ),
    db: Path = typer.Option(DEFAULT_DB, "--db"),
) -> None:
    """Run a single component or the full pipeline (industry->blog->career->decision_maker_intelligence->scoring)."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    comp = component.lower()
    # `all` runs the automatic PIPELINE_ORDER (no decision_maker_intelligence — it is
    # manual-only). A single-component run may still target ANY registered stage,
    # including decision_maker_intelligence, so its manual CLI path keeps working.
    if comp not in (set(STAGES) | {"all"}):
        console.print(f"[red]unknown component '{component}'. Use: {', '.join(STAGES)}, all[/red]")
        raise typer.Exit(2)
    if limit is not None and limit < 1:
        console.print("[red]--limit must be a positive integer[/red]")
        raise typer.Exit(2)
    if limit is not None and comp not in ("decision_maker_intelligence", "all"):
        console.print(
            f"[yellow]--limit only affects decision_maker_intelligence; "
            f"'{comp}' runs its normal (unlimited) scope.[/yellow]"
        )
    effective_run_engine = _effective_run_engine(comp, run_engine)
    if effective_run_engine and comp != "all":
        console.print(f"[dim]Running the {comp} engine (fresh crawl) before ingest; "
                      f"pass --no-run-engine to skip.[/dim]")
    with _open(db) as s:
        if comp == "all" and not resume:
            # A full `run all` is a Standard Run: same pipeline the scheduler runs,
            # recorded run-level in pipeline_executions (trigger='manual', no email —
            # notifications are for scheduled runs). Existing output is unchanged.
            from backend.config import get_settings
            from backend.standard_run import RunInProgress, execute_standard_run
            try:
                execution, results = execute_standard_run(
                    s, get_settings(), trigger="manual", stage_trigger=trigger,
                    run_engine=effective_run_engine, company_limit=limit, notify=False,
                )
                console.print(f"[dim]Standard Run recorded as {execution.run_id} "
                              f"(status: {execution.status})[/dim]")
            except RunInProgress as exc:
                console.print(f"[yellow]{exc}[/yellow]")
                raise typer.Exit(1)
        else:
            orch = Orchestrator(s, run_engine=effective_run_engine, trigger=trigger, company_limit=limit)
            results = orch.run_pipeline(resume=resume) if comp == "all" else [orch.run_stage(comp)]
    _print_results(results)


@app.command()
def rerun(
    component: str = typer.Argument(..., help="a component to re-run, or 'failed' to resume the last pipeline"),
    db: Path = typer.Option(DEFAULT_DB, "--db"),
) -> None:
    """Recovery: re-run one stage, or resume the last pipeline's failed/incomplete stages."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    with _open(db) as s:
        orch = Orchestrator(s, trigger="manual")
        if component.lower() == "failed":
            results = orch.run_pipeline(resume=True)
            if not results:
                console.print("[green]Nothing to resume — last pipeline fully succeeded.[/green]")
                return
        else:
            results = [orch.run_stage(component.lower())]
    _print_results(results)


@app.command()
def status(db: Path = typer.Option(DEFAULT_DB, "--db")) -> None:
    """Health: last success, failed runs, durations, next scheduled run per component."""
    with _open(db) as s:
        report = health_report(s)
    table = Table(title="Platform health")
    for col in ("component", "last status", "last success (UTC)", "failed", "avg ms", "cadence", "next run"):
        table.add_column(col)
    for h in report:
        color = _STATUS_COLOR.get(h["last_status"], "white")
        table.add_row(h["component"], f"[{color}]{h['last_status']}[/{color}]",
                      (h["last_success"] or "-"), str(h["failed_runs"]),
                      str(h["avg_duration_ms"]), h["cadence"], h["next_scheduled_run"])
    console.print(table)


@app.command()
def runs(limit: int = typer.Option(20, "--limit"), db: Path = typer.Option(DEFAULT_DB, "--db")) -> None:
    """Show the most recent pipeline_runs (audit trail)."""
    with _open(db) as s:
        rows = list(s.scalars(select(PipelineRun).order_by(PipelineRun.run_id.desc()).limit(limit)))
    table = Table(title=f"Last {len(rows)} pipeline runs")
    for col in ("id", "pipeline_id", "component", "status", "proc", "new", "upd", "ms", "started (UTC)"):
        table.add_column(col)
    for r in reversed(rows):
        color = _STATUS_COLOR.get(r.status, "white")
        table.add_row(str(r.run_id), r.pipeline_id or "-", r.component, f"[{color}]{r.status}[/{color}]",
                      str(r.records_processed), str(r.records_created), str(r.records_updated),
                      str(r.duration_ms), r.started_at.isoformat(timespec="seconds") if r.started_at else "-")
    console.print(table)


@app.command()
def schedule() -> None:
    """Print ready-to-use scheduling setup (cron / Windows Task Scheduler)."""
    console.print("[bold]Daily full pipeline[/bold] (cadence in config/schedules.json):\n")
    console.print("  Linux/macOS cron (02:00 daily):")
    console.print("    0 2 * * *  cd /path/to/Silicon_Patterns_Platform && python -m orchestrator.cli run all --trigger daily\n")
    console.print("  Windows Task Scheduler (daily 02:00):")
    console.print('    schtasks /Create /SC DAILY /ST 02:00 /TN "SP Platform Daily" ^')
    console.print('      /TR "python -m orchestrator.cli run all --trigger daily" /SD 2026-06-13\n')
    console.print("  Weekly (industry) — Mondays 03:00:")
    console.print("    0 3 * * 1  cd /path/... && python -m orchestrator.cli run industry --trigger weekly\n")
    console.print("  [dim]decision_maker_intelligence is MANUAL only (paid Apify actor) — run it per-company\n"
                  "  from the Decision Makers page, or `run decision_maker_intelligence` on demand.[/dim]\n")
    console.print("  systemd timer / GitHub Actions cron work the same way — call `run all --trigger daily`.")


users_app = typer.Typer(help="Manage user accounts (Google-SSO; deactivate, never hard-delete).")
app.add_typer(users_app, name="users")


def _find_user(s, email: str) -> User:
    user = s.scalar(select(User).where(User.email == email.lower().strip()))
    if user is None:
        console.print(f"[red]no user '{email}' — they must sign in once before being managed.[/red]")
        raise typer.Exit(1)
    return user


@users_app.command("list")
def users_list(db: Path = typer.Option(DEFAULT_DB, "--db")) -> None:
    """List all user accounts."""
    with _open(db) as s:
        rows = list(s.scalars(select(User).order_by(User.created_at.desc())))
    table = Table(title=f"{len(rows)} users")
    for col in ("id", "email", "role", "active", "last login (UTC)"):
        table.add_column(col)
    for u in rows:
        table.add_row(str(u.id), u.email, u.role, "yes" if u.is_active else "[red]no[/red]",
                      u.last_login_at.isoformat(timespec="seconds") if u.last_login_at else "-")
    console.print(table)


def _enforce_privileged_invariant(s, user, *, leaves_admin_tier: bool, leaves_super_admin: bool) -> None:
    """F1: same concurrency-safe guard the HTTP admin API uses (backend.repositories
    .lock_active_privileged_users) -- this CLI is a second, un-authenticated mutation
    path that can touch the same rows, so it must serialize against the API (and
    against itself, if run concurrently against a shared Postgres) rather than bypass
    the invariant entirely."""
    if not (leaves_admin_tier or leaves_super_admin):
        return
    cohort = repo.lock_active_privileged_users(s)
    try:
        if leaves_admin_tier:
            repo.check_keeps_an_admin(cohort, user)
        if leaves_super_admin:
            repo.check_keeps_a_super_admin(cohort, user)
    except repo.LastPrivilegedUserError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@users_app.command("promote")
def users_promote(
    email: str = typer.Argument(..., help="user email"),
    role: str = typer.Option("manager", "--role", help="admin|manager|member"),
    db: Path = typer.Option(DEFAULT_DB, "--db"),
) -> None:
    """Set a user's role (admin / manager / member)."""
    if role not in USER_ROLES:
        console.print(f"[red]invalid role '{role}'. Use: {', '.join(USER_ROLES)}[/red]")
        raise typer.Exit(2)
    with _open(db) as s:
        user = _find_user(s, email)
        leaves_admin_tier, leaves_super_admin = repo.role_change_exposure(user, role)
        _enforce_privileged_invariant(s, user, leaves_admin_tier=leaves_admin_tier,
                                      leaves_super_admin=leaves_super_admin)
        user.role = role
        s.commit()
        console.print(f"[green]{user.email} → {role}[/green]")


@users_app.command("deactivate")
def users_deactivate(email: str = typer.Argument(...), db: Path = typer.Option(DEFAULT_DB, "--db")) -> None:
    """Deactivate an account (blocks login; preserves history). Use for fake/stale users."""
    with _open(db) as s:
        user = _find_user(s, email)
        is_privileged = repo.is_active_privileged(user)
        _enforce_privileged_invariant(s, user, leaves_admin_tier=is_privileged,
                                      leaves_super_admin=is_privileged and user.role == "super_admin")
        user.is_active = False
        s.commit()
        console.print(f"[yellow]{user.email} deactivated[/yellow]")


@users_app.command("activate")
def users_activate(email: str = typer.Argument(...), db: Path = typer.Option(DEFAULT_DB, "--db")) -> None:
    """Re-activate a previously deactivated account."""
    with _open(db) as s:
        user = _find_user(s, email)
        user.is_active = True
        s.commit()
        console.print(f"[green]{user.email} activated[/green]")


# ------------------------------------------------------------------ ML foundation
# Decoupled from `run all` / the scheduler on purpose: nightly feature refresh +
# dataset build run here (cron / Task Scheduler) so scheduled pipeline runs are never
# slowed. Feature generation is incremental + cached.
ml_app = typer.Typer(help="Machine Learning foundation: feature store, embeddings, dataset (no training).")
app.add_typer(ml_app, name="ml")


@ml_app.command("status")
def ml_status(db: Path = typer.Option(DEFAULT_DB, "--db")) -> None:
    """Show ML foundation status + row counts."""
    from backend.config import get_settings
    from backend import ml_service

    with _open(db) as s:
        st = ml_service.ml_status(s, get_settings())
    table = Table(title="ML foundation")
    table.add_column("key"); table.add_column("value")
    for k, v in st.items():
        table.add_row(k, str(v))
    console.print(table)


@ml_app.command("refresh-features")
def ml_refresh_features(
    full: bool = typer.Option(False, "--full", help="Rebuild all (ignore the incremental cache)."),
    db: Path = typer.Option(DEFAULT_DB, "--db"),
) -> None:
    """Incrementally (re)build the feature store — skips companies with unchanged inputs."""
    from backend.config import get_settings
    from ml import features as feat

    with _open(db) as s:
        res = feat.build_features_batch(s, get_settings(), incremental=not full)
        s.commit()
    console.print(f"[green]features {res.feature_version}: computed={res.computed} "
                  f"reused={res.reused} total={res.total}[/green]")


@ml_app.command("build-dataset")
def ml_build_dataset(
    window: int = typer.Option(60, "--window", help="Lookback days (clamped 30..90)."),
    db: Path = typer.Option(DEFAULT_DB, "--db"),
) -> None:
    """Build the ML training dataset from recent feedback + features (no training)."""
    from backend.config import get_settings
    from ml import dataset as ds

    with _open(db) as s:
        res = ds.build_training_dataset(s, get_settings(), window_days=window)
        s.commit()
    console.print(f"[green]{res.version}: rows={res.row_count} pos={res.positive} "
                  f"neg={res.negative} cols={len(res.columns)}[/green]")


@ml_app.command("train")
def ml_train(
    window: int = typer.Option(60, "--window", help="Lookback days (clamped 30..90)."),
    db: Path = typer.Option(DEFAULT_DB, "--db"),
) -> None:
    """Train a candidate recommendation model from the dataset builder (no promotion)."""
    from backend.config import get_settings
    from ml import model as mdl

    with _open(db) as s:
        res = mdl.train_candidate(s, get_settings(), window_days=window, actor_email="cli")
        s.commit()
    m = {k: (round(v, 3) if isinstance(v, float) else v)
         for k, v in res.metrics.items() if k in ("roc_auc", "pr_auc", "f1", "log_loss")}
    console.print(f"[green]candidate {res.version} ({res.backend}) rows={res.n_rows} "
                  f"pos/neg={res.positive}/{res.negative} metrics={m}[/green]")


@ml_app.command("promote")
def ml_promote(version: str = typer.Argument(...), db: Path = typer.Option(DEFAULT_DB, "--db")) -> None:
    """Promote a candidate to production if it clears thresholds and beats the incumbent."""
    from backend.config import get_settings
    from ml import promote as promote_mod

    with _open(db) as s:
        r = promote_mod.promote(s, get_settings(), model_version=version, actor_email="cli")
    color = "green" if r.promoted else "yellow"
    console.print(f"[{color}]{version}: promoted={r.promoted} — {r.reason}[/{color}]")


@ml_app.command("rollback")
def ml_rollback(version: str = typer.Argument(...), db: Path = typer.Option(DEFAULT_DB, "--db")) -> None:
    """Roll production back to a previous model version."""
    from backend.config import get_settings
    from ml import promote as promote_mod

    with _open(db) as s:
        r = promote_mod.rollback(s, get_settings(), to_version=version, actor_email="cli")
    color = "green" if r.promoted else "yellow"
    console.print(f"[{color}]rollback to {version}: {r.promoted} — {r.reason}[/{color}]")


@ml_app.command("infer")
def ml_infer(db: Path = typer.Option(DEFAULT_DB, "--db")) -> None:
    """Run offline inference with the production model (probabilities stored separately)."""
    from backend.config import get_settings
    from ml import model as mdl

    with _open(db) as s:
        try:
            res = mdl.run_inference(s, get_settings())
            s.commit()
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)
    console.print(f"[green]inference {res.model_version}: scored={res.scored} batches={res.batches}[/green]")


@ml_app.command("embed-roles")
def ml_embed_roles(db: Path = typer.Option(DEFAULT_DB, "--db")) -> None:
    """Warm the role-embedding cache for every distinct decision-maker title."""
    from backend.config import get_settings
    from ml import embeddings as emb
    from master_db.models import DecisionMaker

    with _open(db) as s:
        titles = sorted({(dm.current_title or dm.headline or "").strip()
                         for dm in s.scalars(select(DecisionMaker)) if (dm.current_title or dm.headline)})
        before = len(titles)
        emb.embed_titles(s, titles, get_settings())
        s.commit()
    console.print(f"[green]embedded/cached {before} distinct roles[/green]")


sync_app = typer.Typer(help="Historical data synchronization (Phase 2 — companies, read-only preview).")
app.add_typer(sync_app, name="sync")


@sync_app.command("preview")
def sync_preview(
    file: Path = typer.Option(..., "--file", help="Uploaded historical Excel export"),
    db: Path = typer.Option(DEFAULT_DB, "--db"),
    sheet: str | None = typer.Option(None, "--sheet", help="Worksheet name (auto-detected if omitted)"),
    out: Path | None = typer.Option(None, "--out", help="Write the full preview JSON here"),
) -> None:
    """Reconcile a historical company export against the platform (no DB writes)."""
    import json
    from sync import load_historical_companies, reconcile_companies

    records = load_historical_companies(str(file), sheet=sheet)
    with _open(db) as s:
        preview = reconcile_companies(s, records)      # read-only
    st = preview.stats
    table = Table(title=f"Company sync preview — {len(records)} distinct companies")
    for col in ("new", "update", "unchanged", "duplicate", "conflict", "alias", "exact", "fuzzy"):
        table.add_column(col)
    table.add_row(str(st.new), str(st.updated), str(st.unchanged), str(st.duplicates),
                  str(st.conflicts), str(st.alias_matches), str(st.exact_domain_matches),
                  str(st.fuzzy_matches))
    console.print(table)
    console.print(f"[dim]fields: fill={st.fields_to_fill} update={st.fields_to_update} "
                  f"conflict={st.fields_conflicting}[/dim]")
    if out is not None:
        out.write_text(json.dumps(preview.to_dict(), indent=2), encoding="utf-8")
        console.print(f"[green]wrote {out}[/green]")


@sync_app.command("dm-preview")
def sync_dm_preview(
    file: Path = typer.Option(..., "--file", help="Uploaded historical Excel export"),
    db: Path = typer.Option(DEFAULT_DB, "--db"),
    sheet: str | None = typer.Option(None, "--sheet"),
    out: Path | None = typer.Option(None, "--out", help="Write the full preview JSON here"),
) -> None:
    """Reconcile historical decision makers against the platform (no DB writes)."""
    import json
    from sync import load_historical_decision_makers, reconcile_decision_makers

    records = load_historical_decision_makers(str(file), sheet=sheet)
    with _open(db) as s:
        preview = reconcile_decision_makers(s, records)      # read-only
    st = preview.stats
    table = Table(title=f"Decision-maker sync preview — {len(records)} rows")
    for col in ("new", "update", "unchanged", "duplicate", "conflict", "invalid", "li", "email", "name"):
        table.add_column(col)
    table.add_row(str(st.new), str(st.updated), str(st.unchanged), str(st.duplicates),
                  str(st.conflicts), str(st.invalid), str(st.linkedin_matches),
                  str(st.email_matches), str(st.name_matches))
    console.print(table)
    console.print(f"[dim]companies resolved={st.companies_resolved} unresolved={st.companies_unresolved} "
                  f"| fields fill={st.fields_to_fill} conflict={st.fields_conflicting}[/dim]")
    if out is not None:
        out.write_text(json.dumps(preview.to_dict(), indent=2), encoding="utf-8")
        console.print(f"[green]wrote {out}[/green]")


@sync_app.command("import")
def sync_import(
    file: Path = typer.Option(..., "--file", help="Uploaded historical Excel export"),
    db: Path = typer.Option(DEFAULT_DB, "--db"),
    commit: bool = typer.Option(False, "--commit/--dry-run",
                                help="Commit the transaction (default: dry-run, zero writes)"),
) -> None:
    """Apply the company+DM synchronization previews in one transaction (Phase 4)."""
    from sync import (load_historical_companies, load_historical_decision_makers,
                      reconcile_companies, reconcile_decision_makers)
    from backend.import_engine import run_import

    with _open(db) as s:
        cp = reconcile_companies(s, load_historical_companies(str(file))).to_dict()
        dp = reconcile_decision_makers(s, load_historical_decision_makers(str(file))).to_dict()
        report = run_import(s, company_preview=cp, dm_preview=dp, commit=commit)
    table = Table(title=f"Import {'COMMIT' if commit else 'DRY-RUN'} — status={report.status}")
    for col in ("co_created", "co_updated", "dm_created", "dm_updated", "unchanged",
                "dup_skip", "conflict_skip", "invalid_skip"):
        table.add_column(col)
    table.add_row(str(report.companies_created), str(report.companies_updated),
                  str(report.decision_makers_created), str(report.decision_makers_updated),
                  str(report.unchanged), str(report.duplicates_skipped),
                  str(report.conflicts_skipped), str(report.invalid_skipped))
    console.print(table)
    console.print(f"[dim]duration={report.duration_ms}ms warnings={len(report.warnings)} "
                  f"errors={len(report.errors)}[/dim]")
    for e in report.errors:
        console.print(f"[red]{e}[/red]")


@sync_app.command("refresh")
def sync_refresh(
    import_id: str = typer.Option(..., "--import-id", help="ImportJob import_id to refresh"),
    db: Path = typer.Option(DEFAULT_DB, "--db"),
    retry_failed: bool = typer.Option(False, "--retry-failed", help="Re-run only failed stages"),
) -> None:
    """Run (or retry) the Phase-7 post-import intelligence refresh for an import."""
    from backend import import_repo
    from backend.post_import_pipeline import retry_failed as _retry, run_post_import_refresh

    with _open(db) as s:
        job = import_repo.get_import_job(s, import_id)
        if job is None:
            console.print(f"[red]no import job '{import_id}'[/red]")
            raise typer.Exit(1)
        stats = job.stats or {}
        if retry_failed:
            summary = _retry(s, import_id)
        else:
            summary = run_post_import_refresh(
                s, import_id=import_id, domains=stats.get("affected_company_domains", []),
                dm_ids=stats.get("affected_dm_ids", []))
    table = Table(title=f"Post-import refresh — {import_id}")
    for col in ("stage", "status", "processed", "ms", "notes"):
        table.add_column(col)
    for st in summary.stages:
        color = "green" if st["status"] == "success" else "red"
        table.add_row(st["stage"], f"[{color}]{st['status']}[/{color}]", str(st.get("processed", 0)),
                      str(st.get("duration_ms", 0)), (st.get("notes") or st.get("error") or "")[:44])
    console.print(table)


@sync_app.command("seed-aliases")
def sync_seed_aliases(db: Path = typer.Option(DEFAULT_DB, "--db")) -> None:
    """Persist the curated well-known company aliases (AMD ↔ Advanced Micro Devices …).

    Writes CompanyAlias rows for canonical companies that already exist — reusable by
    every engine. Opt-in (this DOES write); the sync preview never calls it.
    """
    from sync.aliases import seed_persisted_aliases

    with _open(db) as s:
        n = seed_persisted_aliases(s)
        s.commit()
    console.print(f"[green]seeded {n} well-known aliases[/green]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
