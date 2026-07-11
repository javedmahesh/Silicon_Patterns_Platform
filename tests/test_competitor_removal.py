"""Service-provider (competitor) exclusion: ingestion block + purge."""
import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from integration.competitors import excluded_domains, is_excluded_domain
from integration.employer_seeds import seed_employers
from integration.resolver import CompanyResolver
from master_db.models import Base, Company, DecisionMaker, Job, LeadScore

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'comp.db').as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_excluded_domains_loaded():
    assert "mirafra.com" in excluded_domains()           # a SERVICE_PROVIDER seed
    assert is_excluded_domain("https://Mirafra.com/")    # normalized + scheme-stripped
    assert not is_excluded_domain("tenstorrent.com")


def test_resolver_refuses_competitor_domain(session):
    r = CompanyResolver(session)
    res = r.resolve(domain="mirafra.com", name="Mirafra", source_engine="career", create_stub=True)
    assert res.company_domain is None and res.created is False
    assert session.get(Company, "mirafra.com") is None
    # a normal unknown domain still stubs as before
    ok = r.resolve(domain="tenstorrent.com", name="Tenstorrent", source_engine="career", create_stub=True)
    assert ok.company_domain == "tenstorrent.com" and ok.created is True


def test_employer_seeds_skip_service_providers(session):
    created, mappings = seed_employers(session)
    assert created > 0                                   # non-excluded seeds still created
    assert session.get(Company, "mirafra.com") is None   # SERVICE_PROVIDER skipped
    assert all(domain != "mirafra.com" for _, domain in mappings)


def _load_purge():
    spec = importlib.util.spec_from_file_location(
        "purge_sp", ROOT / "scripts" / "purge_service_providers.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_purge_removes_competitors_and_dependents(session):
    session.add_all([
        Company(company_domain="mirafra.com", canonical_company_id="MIRAFRA", company_name="Mirafra",
                name_key="mirafra", prospect_type="SERVICE_PROVIDER", validation_status="VALID"),
        Company(company_domain="tenstorrent.com", canonical_company_id="TENSTORRENT",
                company_name="Tenstorrent", name_key="tenstorrent", prospect_type="PRODUCT_COMPANY",
                validation_status="VALID"),
    ])
    session.flush()
    session.add_all([
        DecisionMaker(linkedin_url="https://l/m1", company_domain="mirafra.com", match_score=5.0),
        Job(job_id="J-m1", company_domain="mirafra.com"),
        LeadScore(company_domain="mirafra.com", lead_score=5.0, grade="C", priority_rank=9, model_version="t"),
        DecisionMaker(linkedin_url="https://l/t1", company_domain="tenstorrent.com", match_score=9.0),
    ])
    session.commit()

    purge = _load_purge()
    report = purge.purge(session, apply=False)
    assert "mirafra.com" in report["domains"] and "tenstorrent.com" not in report["domains"]
    assert session.get(Company, "mirafra.com") is not None  # dry run didn't delete

    purge.purge(session, apply=True)
    assert session.get(Company, "mirafra.com") is None
    assert session.scalar(select(func.count()).select_from(DecisionMaker)
                          .where(DecisionMaker.company_domain == "mirafra.com")) == 0
    # non-competitor untouched
    assert session.get(Company, "tenstorrent.com") is not None
    assert session.scalar(select(func.count()).select_from(DecisionMaker)
                          .where(DecisionMaker.company_domain == "tenstorrent.com")) == 1
