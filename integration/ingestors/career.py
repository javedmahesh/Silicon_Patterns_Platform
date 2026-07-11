"""Career Scraper -> jobs, demand_signals, company_rollups.

Three ingestors (the Career Scraper produces three deliverables). Each routes the
company through the resolver and maps the Career ``region_flag`` — which is a
GEOGRAPHIC region — into ``geo_region`` (never ``compliance_flag``).

Sources:
  * career_jobs.xlsx / .csv            -> JobsIngestor
  * career_demand_signals.xlsx / .csv  -> DemandSignalsIngestor
  * company_intelligence.xlsx / .csv   -> CompanyRollupsIngestor
"""
from __future__ import annotations

import hashlib
from typing import Any

from config.enums import normalize_tier
from integration.ingestors.ats_hosts import company_domain_or_blank
from integration.ingestors.base import BaseIngestor, RowResult
from master_db.models import CompanyRollup, DemandSignal, Job


def _job_id(domain: str, job_url: str) -> str:
    return hashlib.sha1(f"{domain}|{job_url}".encode("utf-8")).hexdigest()[:32]


class JobsIngestor(BaseIngestor):
    engine_name = "career_jobs"
    # High-volume: bulk-upsert jobs in one statement (keyed on job_id PK).
    bulk_model = Job
    bulk_conflict = ("job_id",)

    def build_row(self, row: dict[str, Any]) -> RowResult:
        name = self.s(row.get("company_name"))
        # Career's company_domain is derived from the company website, but a job
        # board host (jobs.lever.co) must NOT become the company — guard it.
        domain = company_domain_or_blank(row.get("company_domain"))
        res = self.resolve(domain=domain or None, name=name or None,
                           source_ref=self.s(row.get("job_url")))
        if res.company_domain is None:
            return RowResult(rejected=True, review_queued=res.review_queued,
                             reason="company unresolved")

        job_url = self.s(row.get("job_url"))
        job_id = self.s(row.get("job_id")) or _job_id(res.company_domain, job_url)
        return RowResult(review_queued=res.review_queued, values={
            "job_id": job_id,
            "company_domain": res.company_domain,
            "company_name": name,
            "company_tier": normalize_tier(row.get("company_tier")),
            "job_title": self.s(row.get("job_title")),
            "job_category": self.s(row.get("job_category")),
            "department": self.s(row.get("department")),
            "location": self.s(row.get("location")),
            "country": self.s(row.get("country")),
            "geo_region": self.s(row.get("region_flag") or row.get("geo_region")),  # GEOGRAPHIC
            "employment_type": self.s(row.get("employment_type")),
            "posted_date": self.s(row.get("posted_date")),
            "ats_provider": self.s(row.get("ats_provider")),
            "technologies": self.s(row.get("technologies")),
            "seniority": self.s(row.get("seniority")),
            "engineering_relevance_score": self.i(row.get("engineering_relevance_score")),
            "job_url": job_url,
            "source_url": self.s(row.get("source_url")),
            "scrape_date": self.s(row.get("scrape_date")),
        })


class DemandSignalsIngestor(BaseIngestor):
    engine_name = "career_demand"

    def process_row(self, row: dict[str, Any]) -> RowResult:
        name = self.s(row.get("company_name"))
        domain = company_domain_or_blank(row.get("company_domain"))
        res = self.resolve(domain=domain or None, name=name or None,
                           source_ref=domain)
        if res.company_domain is None:
            return RowResult(rejected=True, review_queued=res.review_queued,
                             reason="company unresolved")

        values = {
            "company_domain": res.company_domain,
            "canonical_company_id": res.canonical_company_id or "",
            "company_name": name,
            "country": self.s(row.get("country")),
            "geo_region": self.s(row.get("region_flag") or row.get("geo_region")),  # GEOGRAPHIC
            "rtl_jobs": self.i(row.get("rtl_jobs")),
            "asic_jobs": self.i(row.get("asic_jobs")),
            "verification_jobs": self.i(row.get("verification_jobs")),
            "physical_design_jobs": self.i(row.get("physical_design_jobs")),
            "dft_jobs": self.i(row.get("dft_jobs")),
            "sta_jobs": self.i(row.get("sta_jobs")),
            "validation_jobs": self.i(row.get("validation_jobs")),
            "fpga_jobs": self.i(row.get("fpga_jobs")),
            "embedded_jobs": self.i(row.get("embedded_jobs")),
            "architecture_jobs": self.i(row.get("architecture_jobs")),
            "total_engineering_jobs": self.i(row.get("total_engineering_jobs")),
            "technologies_detected": self.s(row.get("technologies_detected")),
            "primary_focus": self.s(row.get("primary_focus")),
            "demand_score": self.f(row.get("demand_score")),
            "normalized_demand_score": self.f(row.get("normalized_demand_score")),
            "demand_signal": self.s(row.get("demand_signal")),
            "hiring_trend": self.s(row.get("hiring_trend")),
            "lead_readiness_score": self.f(row.get("lead_readiness_score")),
            "newest_job_date": self.s(row.get("newest_job_date")),
            "hiring_regions": self.s(row.get("hiring_regions")),
            "india_hiring_flag": self.b(row.get("india_hiring_flag")),
            "ats_provider": self.s(row.get("ats_provider")),
        }
        self.upsert(DemandSignal, res.company_domain, values)
        return RowResult(written=True, review_queued=res.review_queued)


class CompanyRollupsIngestor(BaseIngestor):
    engine_name = "career_intel"

    def process_row(self, row: dict[str, Any]) -> RowResult:
        name = self.s(row.get("company_name"))
        domain = company_domain_or_blank(row.get("company_domain"))
        res = self.resolve(domain=domain or None, name=name or None, source_ref=domain)
        if res.company_domain is None:
            return RowResult(rejected=True, review_queued=res.review_queued,
                             reason="company unresolved")

        values = {
            "company_domain": res.company_domain,
            "company_name": name,
            "company_tier": normalize_tier(row.get("company_tier")),
            "country": self.s(row.get("country")),
            "geo_region": self.s(row.get("region_flag") or row.get("geo_region")),
            "demand_score": self.f(row.get("demand_score")),
            "lead_readiness_score": self.f(row.get("lead_readiness_score")),
            "demand_signal": self.s(row.get("demand_signal")),
            "total_engineering_jobs": self.i(row.get("total_engineering_jobs")),
            "primary_focus": self.s(row.get("primary_focus")),
            "technologies_detected": self.s(row.get("technologies_detected")),
            "newest_job_date": self.s(row.get("newest_job_date")),
            "hiring_regions": self.s(row.get("hiring_regions")),
            "india_hiring_flag": self.b(row.get("india_hiring_flag")),
            "priority_rank": self.s(row.get("priority_rank")) or "C",
            "next_action": self.s(row.get("next_action")),
        }
        self.upsert(CompanyRollup, res.company_domain, values)
        return RowResult(written=True, review_queued=res.review_queued)
