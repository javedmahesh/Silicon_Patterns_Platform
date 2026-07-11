"""Industry Discovery -> companies.

Industry Discovery OWNS the companies table, so this ingestor writes *authoritative*
(non-stub) rows directly, recomputing the canonical id / name key centrally and
mapping the engine's ``region_flag`` to ``compliance_flag`` (NOT geo). If a
resolver stub already existed for a domain, this enriches it and clears is_stub.

Source: master_company_universe.xlsx / .csv (columns per the engine's exporter).
"""
from __future__ import annotations

from typing import Any

from config.enums import (
    EXCLUDED_PROSPECT_TYPES,
    normalize_compliance_flag,
    normalize_prospect_type,
    normalize_tier,
)
from integration.competitors import is_excluded_domain
from integration.ingestors.ats_hosts import company_domain_or_blank
from integration.ingestors.base import BaseIngestor, RowResult
from integration.normalizer import canonical_company_id, name_key, normalize_domain
from master_db.models import Company


class IndustryIngestor(BaseIngestor):
    engine_name = "industry"

    def process_row(self, row: dict[str, Any]) -> RowResult:
        # The company's own domain. Guard against an ATS/publisher slipping in.
        domain = company_domain_or_blank(row.get("company_domain") or row.get("website"))
        if not domain:
            # No usable domain => cannot key a company. Industry rows should
            # always have one; reject loudly rather than mint a bad key.
            return RowResult(rejected=True, reason="missing/unusable company_domain")

        name = self.s(row.get("company_name"))
        values = {
            "company_domain": domain,
            "canonical_company_id": canonical_company_id(domain, name),
            "company_name": name,
            "name_key": name_key(name),
            "website": self.s(row.get("website")),
            "company_linkedin": self.s(row.get("linkedin_url") or row.get("company_linkedin")),
            "country": self.s(row.get("country")),
            "city": self.s(row.get("city")),
            "headquarters": self.s(row.get("headquarters")),
            "compliance_flag": normalize_compliance_flag(row.get("region_flag") or row.get("compliance_flag")),
            "industry_category": self.s(row.get("company_category") or row.get("industry_category")),
            "sub_category": self.s(row.get("sub_category")),
            "industry_type": self.s(row.get("industry_type")),
            "technology_focus": self.s(row.get("technology_focus")),
            "prospect_type": normalize_prospect_type(row.get("prospect_type")),
            "company_tier": normalize_tier(row.get("company_tier")),
            "company_status": self.s(row.get("company_status")),
            "founded_year": self.s(row.get("founded_year")),
            "source": self.s(row.get("source")),
            "source_type": self.s(row.get("source_type")),
            "discovery_date": self.s(row.get("discovery_date")),
            "confidence_score": self.f(row.get("confidence_score")),
            "validation_status": self.s(row.get("validation_status")) or "VALID",
            "is_stub": False,  # authoritative row — clear any prior stub flag
        }
        if values["prospect_type"] in EXCLUDED_PROSPECT_TYPES or is_excluded_domain(domain):
            # Competitor (service provider) — refuse to store it.
            return RowResult(reason="excluded competitor (service provider)")
        self.upsert(Company, domain, values)
        if name:
            self.resolver.register_alias(name, domain, source=self.engine_name)
        return RowResult(written=True)
