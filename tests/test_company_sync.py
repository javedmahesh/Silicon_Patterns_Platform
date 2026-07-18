"""Phase 2 historical synchronization engine — company reconciliation (read-only)."""
import openpyxl
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from integration.normalizer import name_key
from master_db.local import make_session_factory
from master_db.models import Base, Company, CompanyAlias
from sync import HistoricalCompany, load_historical_companies, reconcile_companies
from sync.aliases import canonical_name_key, seed_persisted_aliases
from sync.normalization import COMPANY_OWNED_FIELDS, PLATFORM_OWNED_FIELDS, clear_caches


def _company(domain, name, **over):
    base = dict(
        company_domain=domain, canonical_company_id=name_key(name).upper().replace(" ", ""),
        company_name=name, name_key=name_key(name), validation_status="VALID", is_stub=False,
    )
    base.update(over)
    return Company(**base)


@pytest.fixture()
def session():
    clear_caches()
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add(_company("amd.com", "Advanced Micro Devices", website="https://www.amd.com/",
                       industry_category=""))
        s.add(_company("nvidia.com", "NVIDIA Corporation", website="https://www.nvidia.com/",
                       industry_category="Semiconductors"))
        s.add(_company("stub.com", "Stub Co", website="https://stub.com", is_stub=True,
                       validation_status="STUB", industry_category="OldGuess"))
        s.commit()
        yield s


def _rec(name, website="", **fields):
    return HistoricalCompany(raw_name=name, website=website, fields=dict(fields),
                             source_ref=f"row:{name}")


# ----------------------------------------------------------------- matching
def test_exact_domain_match_fill_missing(session):
    p = reconcile_companies(session, [_rec("AMD", "https://amd.com", industry_category="Semiconductors")])
    r = p.results[0]
    assert r.classification == "update" and r.match_type == "EXACT_DOMAIN"
    assert [(c.field, c.action) for c in r.changes] == [("industry_category", "fill")]
    assert r.conflicts == []


def test_exact_domain_unchanged_when_equivalent(session):
    # same domain, normalized-equal name, no new info -> unchanged
    p = reconcile_companies(session, [_rec("Advanced Micro Devices", "http://www.amd.com/careers")])
    assert p.results[0].classification == "unchanged" and p.stats.unchanged == 1


def test_conflict_never_overwrites_richer_data(session):
    # nvidia already has industry_category="Semiconductors"; a different value is a CONFLICT,
    # not a silent overwrite.
    p = reconcile_companies(session, [_rec("NVIDIA", "https://nvidia.com", industry_category="GPUs")])
    r = p.results[0]
    assert r.classification == "conflict"
    assert r.conflicts and r.conflicts[0].field == "industry_category"
    assert r.conflicts[0].current == "Semiconductors"   # platform value reported, not lost
    assert r.changes == []


def test_stub_is_refreshed_not_conflicted(session):
    # a low-quality stub CAN be updated by richer historical data
    p = reconcile_companies(session, [_rec("Stub Co", "https://stub.com", industry_category="Photonics")])
    r = p.results[0]
    assert r.classification == "update"
    assert [(c.field, c.action) for c in r.changes] == [("industry_category", "update")]


def test_alias_match_amd(session):
    # no domain on the record; "AMD" resolves to Advanced Micro Devices via the alias seed
    p = reconcile_companies(session, [_rec("AMD")])
    r = p.results[0]
    assert r.resolved_domain == "amd.com" and r.match_type == "ALIAS"
    assert r in p.alias_matches


def test_canonical_name_match_without_domain(session):
    p = reconcile_companies(session, [_rec("Advanced Micro Devices")])
    assert p.results[0].match_type == "CANONICAL_NAME" and p.results[0].resolved_domain == "amd.com"


def test_new_company(session):
    p = reconcile_companies(session, [_rec("Groq", "https://groq.com", industry_category="AI")])
    r = p.results[0]
    assert r.classification == "new" and r.resolved_domain == "groq.com"
    assert {c.field for c in r.changes} == {"company_name", "website", "industry_category"}


def test_duplicate_within_batch(session):
    recs = [_rec("Groq", "https://groq.com"), _rec("Groq Inc", "https://www.groq.com/careers")]
    p = reconcile_companies(session, recs)
    classes = sorted(r.classification for r in p.results)
    assert classes == ["duplicate", "new"] and p.stats.duplicates == 1


def test_invalid_no_domain_no_name(session):
    # a website that is a LinkedIn URL -> no usable domain, and an unknown name -> conflict
    p = reconcile_companies(session, [_rec("Totally Unknown Co", "https://www.linkedin.com/company/x")])
    r = p.results[0]
    assert r.classification == "conflict" and r.match_type == "INVALID" and r.resolved_domain is None


def test_fuzzy_name_match(session):
    p = reconcile_companies(session, [_rec("Advanced Micro Devicess")])   # one-letter typo, no domain
    assert p.results[0].match_type in ("FUZZY_NAME", "ALIAS")
    assert p.results[0].resolved_domain == "amd.com"


# ------------------------------------------------------ invariants / rules
def test_never_touches_platform_owned_fields(session):
    recs = [_rec("AMD", "https://amd.com", industry_category="Semiconductors"),
            _rec("Groq", "https://groq.com")]
    p = reconcile_companies(session, recs)
    for r in p.results:
        for ch in r.changes + r.conflicts:
            assert ch.field in COMPANY_OWNED_FIELDS
            assert ch.field not in PLATFORM_OWNED_FIELDS


def test_reconcile_is_read_only(session):
    before = session.query(Company).count()
    reconcile_companies(session, [_rec("Groq", "https://groq.com"), _rec("AMD", "https://amd.com")])
    assert session.query(Company).count() == before
    assert not session.new and not session.dirty


def test_deterministic(session):
    recs = [_rec("Groq", "https://groq.com"), _rec("AMD", "https://amd.com"),
            _rec("NVIDIA", "https://nvidia.com")]
    a = reconcile_companies(session, list(recs)).to_dict()
    b = reconcile_companies(session, list(reversed(recs))).to_dict()
    a["generated_at"] = b["generated_at"] = ""
    assert a == b


# ----------------------------------------------------------- alias system
def test_alias_canonicalization():
    assert canonical_name_key("AMD") == name_key("Advanced Micro Devices")
    assert canonical_name_key("Nvidia") == name_key("NVIDIA Corporation")
    assert canonical_name_key("Some Random Co") == name_key("Some Random Co")


def test_seed_persisted_aliases_writes_rows(session):
    n = seed_persisted_aliases(session)
    session.commit()
    assert n >= 2   # amd + nvidia canonical companies exist in the fixture
    keys = {a.name_key for a in session.query(CompanyAlias).all()}
    assert name_key("AMD") in keys


# ----------------------------------------------------------- excel adapter
def _write_xlsx(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales_Research_Master_v7"
    ws.append(["Date", "Intern Name", "Region", "Company Name", "Company Website",
               "Company Type", "Product Category", "Contact First Name", "LinkedIn URL"])
    # Groq denormalized across 2 contact rows -> 1 company; plus existing AMD
    ws.append(["1-1-2026", "T", "US", "Groq", "https://groq.com", "Product", "AI",
               "Gavin", "https://linkedin.com/in/a"])
    ws.append(["1-1-2026", "T", "US", "Groq ", "https://www.groq.com/", "Product", "AI",
               "Leandro", "https://linkedin.com/in/b"])
    ws.append(["1-1-2026", "T", "US", "AMD", "https://amd.com", "Product", "CPU",
               "Lisa", "https://linkedin.com/in/c"])
    wb.save(path)


def test_load_historical_companies_dedupes(tmp_path):
    clear_caches()
    xl = tmp_path / "hist.xlsx"
    _write_xlsx(xl)
    recs = load_historical_companies(str(xl))
    by_name = {r.raw_name.strip(): r for r in recs}
    assert len(recs) == 2                       # Groq (2 rows collapsed) + AMD
    assert by_name["Groq"].row_count == 2
    assert by_name["Groq"].fields["industry_category"] == "AI"


def test_preview_endpoint(tmp_path):
    clear_caches()
    xl = tmp_path / "hist.xlsx"
    _write_xlsx(xl)
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'sync.db').as_posix()}",
        historical_import_path=str(xl), log_json=False,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(_company("amd.com", "Advanced Micro Devices"))
            s.commit()
        # member is blocked; manager gets the read-only preview
        assert c.post("/sync/companies/preview", headers={"X-Dev-Role": "member"}).status_code == 403
        resp = c.post("/sync/companies/preview", headers={"X-Dev-Role": "manager"})
        assert resp.status_code == 200
        stats = resp.json()["stats"]
        assert stats["total_input"] == 2 and stats["new"] == 1   # Groq new, AMD matched


def test_preview_endpoint_422_when_unconfigured(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 's2.db').as_posix()}",
                              log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        assert c.post("/sync/companies/preview", headers={"X-Dev-Role": "manager"}).status_code == 422
