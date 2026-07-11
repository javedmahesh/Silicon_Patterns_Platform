"""Integration tests for the P1 ingestors, run against in-memory SQLite.

Covers: authoritative company ingest, idempotency, stub creation + review queue,
the ATS-host guard, name-based LinkedIn resolution, and ingestion_runs logging.
"""
from pathlib import Path

import pytest
from sqlalchemy import func, select

from integration.ingestors.backfill import run_backfill
from integration.ingestors.blog import BlogIngestor
from integration.ingestors.career import (
    CompanyRollupsIngestor,
    DemandSignalsIngestor,
    JobsIngestor,
)
from integration.ingestors.apify import ApifyIngestor
from integration.ingestors.industry import IndustryIngestor
from integration.ingestors.linkedin import LinkedInIngestor
from master_db.local import make_session_factory
from master_db.models import (
    Company,
    CompanyRollup,
    DecisionMaker,
    DemandSignal,
    IngestionRun,
    Job,
    Opportunity,
    ResolutionReviewQueue,
)

FIX = Path(__file__).parent / "fixtures"


def _sources() -> dict[str, Path]:
    return {
        "industry": FIX / "industry_companies.csv",
        "blog": FIX / "blog_opportunities.jsonl",
        "career_jobs": FIX / "career_jobs.csv",
        "career_demand": FIX / "career_demand_signals.csv",
        "career_intel": FIX / "company_intelligence.csv",
        "linkedin": FIX / "linkedin_candidates.json",
    }


@pytest.fixture()
def session():
    Session = make_session_factory(":memory:")
    with Session() as s:
        yield s


def _count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


# --------------------------------------------------------------- industry
def test_industry_ingest_creates_authoritative_companies(session):
    res = IndustryIngestor(session).ingest(FIX / "industry_companies.csv")
    assert (res.rows_in, res.rows_upserted, res.rows_rejected) == (2, 2, 0)
    groq = session.get(Company, "groq.com")
    assert groq is not None and groq.is_stub is False and groq.validation_status == "VALID"
    # www. was stripped to the registrable domain.
    assert session.get(Company, "tenstorrent.com") is not None
    # region_flag mapped to compliance_flag (not geo).
    assert groq.compliance_flag == "APPROVED"
    # canonical id recomputed centrally from the domain.
    assert groq.canonical_company_id == "GROQ"


def test_industry_idempotent(session):
    IndustryIngestor(session).ingest(FIX / "industry_companies.csv")
    IndustryIngestor(session).ingest(FIX / "industry_companies.csv")
    assert _count(session, Company) == 2


# --------------------------------------------------------------- blog
def test_blog_known_stub_and_unresolved(session):
    IndustryIngestor(session).ingest(FIX / "industry_companies.csv")
    res = BlogIngestor(session).ingest(FIX / "blog_opportunities.jsonl")
    assert res.rows_in == 3
    assert res.rows_upserted == 2          # groq (known) + etched (new stub)
    assert res.rows_rejected == 1          # mystery: no domain, no match
    # Etched became a low-confidence stub company.
    etched = session.get(Company, "etched.ai")
    assert etched is not None and etched.is_stub and etched.validation_status == "STUB"
    assert _count(session, Opportunity) == 2
    # Review queue holds the stub + the unresolved mystery company.
    assert _count(session, ResolutionReviewQueue) >= 2


# --------------------------------------------------------------- career
def test_career_jobs_ats_host_never_becomes_company(session):
    IndustryIngestor(session).ingest(FIX / "industry_companies.csv")
    res = JobsIngestor(session).ingest(FIX / "career_jobs.csv")
    # Groq job ingested; the jobs.lever.co row is rejected (ATS host, name unknown).
    assert res.rows_upserted == 1
    assert res.rows_rejected == 1
    assert session.get(Company, "lever.co") is None
    assert session.get(Company, "jobs.lever.co") is None
    assert _count(session, Job) == 1
    # The Groq job carried the geographic region into geo_region.
    job = session.scalar(select(Job))
    assert job.geo_region == "North America" and job.company_domain == "groq.com"


def test_demand_and_rollups_one_to_one(session):
    IndustryIngestor(session).ingest(FIX / "industry_companies.csv")
    DemandSignalsIngestor(session).ingest(FIX / "career_demand_signals.csv")
    CompanyRollupsIngestor(session).ingest(FIX / "company_intelligence.csv")
    ds = session.get(DemandSignal, "groq.com")
    assert ds is not None and ds.total_engineering_jobs == 6 and ds.hiring_trend == "GROWING"
    roll = session.get(CompanyRollup, "groq.com")
    assert roll is not None and roll.priority_rank == "A"


# --------------------------------------------------------------- linkedin
def test_linkedin_resolves_by_name_and_keeps_unresolved(session):
    IndustryIngestor(session).ingest(FIX / "industry_companies.csv")  # registers "groq" alias
    res = LinkedInIngestor(session).ingest(FIX / "linkedin_candidates.json")
    assert res.rows_upserted == 2          # both people are written
    jane = session.scalar(select(DecisionMaker).where(DecisionMaker.first_name == "Jane"))
    assert jane.company_domain == "groq.com" and jane.seniority == "senior"
    bob = session.scalar(select(DecisionMaker).where(DecisionMaker.first_name == "Bob"))
    assert bob.company_domain is None      # unresolved employer -> NULL, not dropped
    assert res.rows_review_queued >= 1
    # No junk company was created for the unresolved employer.
    assert _count(session, Company) == 2


# --------------------------------------------------------------- apify (decision makers)
def _apify_company(session):
    session.add(Company(company_domain="nvidia.com", canonical_company_id="NV", company_name="NVIDIA",
                        name_key="nvidia", prospect_type="PRODUCT_COMPANY", validation_status="VALID"))
    session.commit()


def test_apify_maps_all_professional_fields_and_preserves_raw(session):
    _apify_company(session)
    row = {
        "linkedinUrl": "https://linkedin.com/in/jane", "firstName": "Jane", "lastName": "Doe",
        "position": "VP of Engineering", "organizationName": "NVIDIA",
        "organizationWebsite": "https://www.nvidia.com", "email": "jane@nvidia.com",
        "contactEmailStatus": "verified", "phone_numbers": "+1-555-0142",
        "city": "Santa Clara", "state": "California", "country": "United States",
        "seniority": "Vice President", "organizationLinkedinUrl": "https://linkedin.com/company/nvidia",
        "personId": "abc123",
    }
    row["functional"] = "Engineering"
    row["organizationId"] = "org-987"
    v = ApifyIngestor(session).build_row(row).values
    assert v["full_name"] == "Jane Doe"
    assert v["functional_area"] == "Engineering"
    assert v["work_email"] == "jane@nvidia.com" and v["email_status"] == "verified"
    assert v["work_phone"] == "+1-555-0142"
    assert (v["city"], v["state_region"], v["country"]) == ("Santa Clara", "California", "United States")
    assert v["organization_website"] == "https://www.nvidia.com"
    assert v["organization_linkedin"] == "https://linkedin.com/company/nvidia"
    # metadata kept in profile_data (not promoted to columns)
    assert v["profile_data"]["organization_id"] == "org-987"
    # the COMPLETE raw actor record is preserved for future enrichment
    assert v["profile_data"]["raw"] == row


def test_apify_leaves_absent_fields_null_not_placeholder(session):
    _apify_company(session)
    row = {"linkedinUrl": "https://l/x", "firstName": "No", "lastName": "Phone",
           "position": "Director", "organizationName": "NVIDIA", "organizationWebsite": "nvidia.com"}
    v = ApifyIngestor(session).build_row(row).values
    assert v["work_email"] is None and v["work_phone"] is None
    assert v["city"] is None and v["state_region"] is None and v["country"] is None
    assert v["email_status"] is None and v["functional_area"] is None


def test_apify_persists_structured_columns_to_db(session):
    from master_db.bulk import bulk_upsert

    _apify_company(session)
    row = {"linkedinUrl": "https://l/cto", "firstName": "Ada", "lastName": "Lin",
           "position": "Chief Technology Officer", "organizationName": "NVIDIA",
           "organizationWebsite": "nvidia.com", "email": "ada@nvidia.com", "country": "USA"}
    rr = ApifyIngestor(session).build_row(row)
    bulk_upsert(session, DecisionMaker, [rr.values], ["linkedin_url"])
    session.commit()
    dm = session.scalar(select(DecisionMaker).where(DecisionMaker.first_name == "Ada"))
    assert dm.work_email == "ada@nvidia.com" and dm.country == "USA"
    assert dm.work_phone is None  # absent -> NULL column, not ""


# --------------------------------------------------------------- backfill
def test_full_backfill_is_idempotent(session):
    run_backfill(session, sources=_sources())
    snapshot = tuple(
        _count(session, m)
        for m in (Company, Opportunity, Job, DemandSignal, CompanyRollup, DecisionMaker)
    )
    # companies: groq, tenstorrent (industry) + etched (blog stub) = 3
    assert snapshot == (3, 2, 1, 1, 1, 2)
    run_backfill(session, sources=_sources())
    snapshot2 = tuple(
        _count(session, m)
        for m in (Company, Opportunity, Job, DemandSignal, CompanyRollup, DecisionMaker)
    )
    assert snapshot == snapshot2           # re-running changes no row counts


def test_ingestion_run_is_logged(session):
    IndustryIngestor(session).ingest(FIX / "industry_companies.csv")
    run = session.scalar(select(IngestionRun))
    assert run.engine == "industry"
    assert run.status == "success"
    assert run.rows_upserted == 2
    assert run.finished_at is not None


def test_missing_source_is_skipped_not_fatal(session):
    res = IndustryIngestor(session).ingest(FIX / "does_not_exist.csv")
    assert res.status == "failed" and res.rows_in == 0
    # A failed run is still logged for the audit trail.
    assert _count(session, IngestionRun) == 1
