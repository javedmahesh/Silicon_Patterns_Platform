"""Blog Crawler -> opportunities.

Routes each event's company through the resolver (creating a stub + review item
for a never-before-seen domain). ``opportunities.company_domain`` is NOT NULL, so
a row that cannot be resolved to any domain is rejected (and the resolver has
already queued it for review).

Source: blog_opportunities.jsonl (richest) / .csv / .xlsx.
"""
from __future__ import annotations

import hashlib
from typing import Any

from config.enums import normalize_compliance_flag, normalize_prospect_type, normalize_tier
from integration.ingestors.ats_hosts import company_domain_or_blank
from integration.ingestors.base import BaseIngestor, RowResult
from master_db.models import Opportunity


def _opportunity_id(article_url: str, company_domain: str, opp_type: str) -> str:
    base = article_url or f"{company_domain}|{opp_type}"
    return "OPP-" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:12].upper()


class BlogIngestor(BaseIngestor):
    engine_name = "blog"

    def process_row(self, row: dict[str, Any]) -> RowResult:
        name = self.s(row.get("company_name"))
        website = self.s(row.get("website"))
        domain = company_domain_or_blank(row.get("company_domain") or website)

        res = self.resolve(domain=domain or None, name=name or None, website=website or None,
                           source_ref=self.s(row.get("opportunity_id")) or self.s(row.get("article_url")))
        if res.company_domain is None:
            # Cannot attach an opportunity without a company (FK NOT NULL).
            return RowResult(rejected=True, review_queued=res.review_queued,
                             reason="company unresolved")

        opp_id = self.s(row.get("opportunity_id")) or _opportunity_id(
            self.s(row.get("article_url")), res.company_domain, self.s(row.get("opportunity_type"))
        )
        values = {
            "opportunity_id": opp_id,
            "company_domain": res.company_domain,
            "canonical_company_id": res.canonical_company_id or "",
            "company_name": name,
            "company_tier": normalize_tier(row.get("company_tier")),
            "prospect_type": normalize_prospect_type(row.get("prospect_type")),
            "country": self.s(row.get("country")),
            "compliance_flag": normalize_compliance_flag(row.get("region_flag") or row.get("compliance_flag")),
            "article_title": self.s(row.get("article_title")),
            "article_url": self.s(row.get("article_url")),
            "source": self.s(row.get("source")),
            "source_type": self.s(row.get("source_type")),
            "published_date": self.s(row.get("published_date")),
            "event_age_days": self.i(row.get("event_age_days"), default=-1),
            "opportunity_type": self.s(row.get("opportunity_type")),
            "opportunity_category": self.s(row.get("opportunity_category")),
            "funding_stage": self.s(row.get("funding_stage")),
            "funding_amount": self.s(row.get("funding_amount")),
            "product_mentioned": self.s(row.get("product_mentioned")),
            "technology_mentioned": self.s(row.get("technology_mentioned")),
            "technology_focus": self.s(row.get("technology_focus")),
            "conference_mentioned": self.s(row.get("conference_mentioned")),
            "partnership_mentioned": self.s(row.get("partnership_mentioned")),
            "expansion_mentioned": self.s(row.get("expansion_mentioned")),
            "partner_company": self.s(row.get("partner_company")),
            "foundry_partner": self.s(row.get("foundry_partner")),
            "eda_partner": self.s(row.get("eda_partner")),
            "opportunity_score": self.i(row.get("opportunity_score")),
            "effective_opportunity_score": self.i(row.get("effective_opportunity_score")),
            "recency_weight": self.f(row.get("recency_weight"), default=1.0),
            "confidence_score": self.i(row.get("confidence_score")),
            "lead_readiness_score": self.i(row.get("lead_readiness_score")),
            "summary": self.s(row.get("summary")),
            "validation_status": self.s(row.get("validation_status")) or "REVIEW_REQUIRED",
            "source_tier": self.i(row.get("source_tier")),
            "discovery_date": self.s(row.get("discovery_date")),
        }
        self.upsert(Opportunity, opp_id, values)
        return RowResult(written=True, review_queued=res.review_queued)
