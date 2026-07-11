"""Annual List Ingestor -> opportunities (opportunity_type = ANNUAL_LIST).

Maps a company's appearance on an annual list / ranking (Fortune 500, Inc. 5000,
Forbes AI 50, CNBC Disruptor 50, EE Times Silicon 100, …) to an ``opportunities``
row, so it flows into the existing Opportunities views, the Company-Profile
timeline, and the lead **opportunity** sub-score with no scorer change. The rank
is captured in the shared ``company_news_signal`` column ("Rank: N").

Feed: annual_lists.jsonl / .csv / .xlsx with columns:
  company_name, company_domain / website, list_name, list_year, list_rank,
  list_publisher, article_url, country, company_tier, prospect_type,
  compliance_flag, summary
"""
from __future__ import annotations

import hashlib
from typing import Any

from config.enums import normalize_compliance_flag, normalize_prospect_type, normalize_tier
from integration.ingestors.ats_hosts import company_domain_or_blank
from integration.ingestors.base import BaseIngestor, RowResult
from master_db.models import Opportunity


def _list_id(company_domain: str, list_name: str, list_year: str) -> str:
    base = f"{company_domain}|{list_name}|{list_year}"
    return "LST-" + hashlib.sha1(base.encode()).hexdigest()[:12].upper()


class AnnualListIngestor(BaseIngestor):
    engine_name = "annual_list"

    def process_row(self, row: dict[str, Any]) -> RowResult:
        name = self.s(row.get("company_name"))
        website = self.s(row.get("website"))
        domain = company_domain_or_blank(row.get("company_domain") or website)

        res = self.resolve(
            domain=domain or None,
            name=name or None,
            website=website or None,
            source_ref=self.s(row.get("article_url")),
        )
        if res.company_domain is None:
            return RowResult(rejected=True, review_queued=res.review_queued,
                             reason="company unresolved")

        list_name = self.s(row.get("list_name")) or "UNKNOWN_LIST"
        list_year = self.s(row.get("list_year")) or ""
        list_rank = self.s(row.get("list_rank")) or ""
        list_publisher = self.s(row.get("list_publisher")) or ""

        opp_id = _list_id(res.company_domain, list_name, list_year)

        auto_summary = f"Appeared on {list_name}"
        if list_year:
            auto_summary += f" ({list_year})"
        if list_rank:
            auto_summary += f", ranked #{list_rank}"
        if list_publisher:
            auto_summary += f" — {list_publisher}"

        values = {
            "opportunity_id": opp_id,
            "company_domain": res.company_domain,
            "canonical_company_id": res.canonical_company_id or "",
            "company_name": name,
            "company_tier": normalize_tier(row.get("company_tier")),
            "prospect_type": normalize_prospect_type(row.get("prospect_type")),
            "country": self.s(row.get("country")),
            "compliance_flag": normalize_compliance_flag(
                row.get("region_flag") or row.get("compliance_flag")
            ),
            "article_title": f"{list_name} {list_year}".strip(),
            "article_url": self.s(row.get("article_url")),
            "source": list_publisher or self.s(row.get("source")),
            "source_type": "annual_list",
            "published_date": self.s(row.get("published_date")) or list_year,
            "event_age_days": self.i(row.get("event_age_days"), default=-1),
            "opportunity_type": "ANNUAL_LIST",
            "opportunity_category": list_name,
            "summary": self.s(row.get("summary")) or auto_summary,
            "company_news_signal": f"Rank: {list_rank}" if list_rank else "",
            "opportunity_score": self.i(row.get("opportunity_score"), default=60),
            "effective_opportunity_score": self.i(
                row.get("effective_opportunity_score"), default=60
            ),
            "recency_weight": self.f(row.get("recency_weight"), default=1.0),
            "confidence_score": self.i(row.get("confidence_score"), default=80),
            "lead_readiness_score": self.i(row.get("lead_readiness_score"), default=50),
            "validation_status": self.s(row.get("validation_status")) or "REVIEW_REQUIRED",
            "source_tier": self.i(row.get("source_tier"), default=2),
            "discovery_date": self.s(row.get("discovery_date")),
        }
        self.upsert(Opportunity, opp_id, values)
        return RowResult(written=True, review_queued=res.review_queued)
