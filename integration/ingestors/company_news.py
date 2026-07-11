"""Company-News Ingestor -> opportunities (executive hires / leadership & role
changes / other notable company news).

This is the Blog-Crawler "company intelligence" feed: instead of only product /
funding / expansion events, it captures *people & leadership* movements and other
important company news, e.g.

  * a new senior hire                     -> opportunity_type = EXECUTIVE_HIRE
  * a high-level decision maker switching -> opportunity_type = LEADERSHIP_CHANGE
  * someone changing role internally      -> opportunity_type = ROLE_CHANGE
  * any other notable company news        -> opportunity_type = COMPANY_NEWS

Each row becomes one ``opportunities`` record (the table already models "an event
about a company"), so company news flows into the Company Profile timeline AND the
lead score's opportunity sub-score with no scorer changes. The human-readable
``company_news_signal`` column (migration 0016) holds a one-line summary of the move.
The director+ leadership rows are also picked up by the person-level
``leadership_signals`` derivation (its blog-event feeder).

Feed: company_news.jsonl / .csv / .xlsx with columns (all optional except a
company identifier + news_type):

  company_name, company_domain, website, news_type, person_name, person_title,
  previous_company, previous_title, new_role, headline, article_url, source,
  source_type, published_date, summary, country, company_tier, prospect_type,
  compliance_flag, opportunity_score, effective_opportunity_score,
  confidence_score, lead_readiness_score, source_tier, discovery_date
"""
from __future__ import annotations

import hashlib
from typing import Any

from config.enums import normalize_compliance_flag, normalize_prospect_type, normalize_tier
from integration.ingestors.ats_hosts import company_domain_or_blank
from integration.ingestors.base import BaseIngestor, RowResult
from master_db.models import Opportunity

# The four company-news opportunity types (kept in sync with the backend
# `_COMPANY_NEWS_TYPES` in backend/repositories.py and the `company_news_only` filter).
NEWS_TYPES = ("EXECUTIVE_HIRE", "LEADERSHIP_CHANGE", "ROLE_CHANGE", "COMPANY_NEWS")

# Loose synonyms an upstream feed might emit -> canonical news_type.
_NEWS_ALIASES = {
    "HIRE": "EXECUTIVE_HIRE", "NEW_HIRE": "EXECUTIVE_HIRE", "HIRING": "EXECUTIVE_HIRE",
    "APPOINTMENT": "EXECUTIVE_HIRE", "JOINED": "EXECUTIVE_HIRE",
    "LEADERSHIP": "LEADERSHIP_CHANGE", "EXEC_CHANGE": "LEADERSHIP_CHANGE",
    "EXECUTIVE_CHANGE": "LEADERSHIP_CHANGE", "DEPARTURE": "LEADERSHIP_CHANGE",
    "SWITCH": "LEADERSHIP_CHANGE", "MOVE": "LEADERSHIP_CHANGE",
    "PROMOTION": "ROLE_CHANGE", "ROLE": "ROLE_CHANGE", "REORG": "ROLE_CHANGE",
    "NEWS": "COMPANY_NEWS", "GENERAL": "COMPANY_NEWS",
}


def _news_id(company_domain: str, news_type: str, person: str, ref: str) -> str:
    base = f"{company_domain}|{news_type}|{person}|{ref}"
    return "NEWS-" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:12].upper()


def normalize_news_type(value: Any) -> str:
    v = (str(value).strip().upper().replace(" ", "_").replace("-", "_")) if value else ""
    if v in NEWS_TYPES:
        return v
    return _NEWS_ALIASES.get(v, "COMPANY_NEWS")


def _signal_for(news_type: str, person: str, title: str, prev_company: str,
                prev_title: str, new_role: str, headline: str) -> str:
    """One-line, human-readable summary of the move (-> company_news_signal)."""
    if news_type == "EXECUTIVE_HIRE" and person:
        s = f"{person} joined" + (f" as {title}" if title else "")
        return s + (f" (ex-{prev_company})" if prev_company else "")
    if news_type == "LEADERSHIP_CHANGE" and person:
        s = f"{person}"
        if prev_title and (title or new_role):
            s += f": {prev_title} -> {title or new_role}"
        elif title or new_role:
            s += f" -> {title or new_role}"
        return s + (f" (from {prev_company})" if prev_company else "")
    if news_type == "ROLE_CHANGE" and person:
        return f"{person}: {prev_title or title} -> {new_role or title}".strip(" :->")
    return headline or "Company news"


class CompanyNewsIngestor(BaseIngestor):
    engine_name = "company_news"

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
            # opportunities.company_domain is NOT NULL -> reject (resolver queued review).
            return RowResult(rejected=True, review_queued=res.review_queued,
                             reason="company unresolved")

        news_type = normalize_news_type(row.get("news_type") or row.get("opportunity_type"))
        person = self.s(row.get("person_name") or row.get("executive_name"))
        title = self.s(row.get("person_title") or row.get("title"))
        prev_company = self.s(row.get("previous_company"))
        prev_title = self.s(row.get("previous_title"))
        new_role = self.s(row.get("new_role"))
        headline = self.s(row.get("headline") or row.get("article_title"))

        signal = _signal_for(news_type, person, title, prev_company, prev_title, new_role, headline)
        article_title = headline or signal
        published = self.s(row.get("published_date"))

        opp_id = _news_id(res.company_domain, news_type, person,
                          self.s(row.get("article_url")) or published)

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
            "article_title": article_title,
            "article_url": self.s(row.get("article_url")),
            "source": self.s(row.get("source")),
            "source_type": self.s(row.get("source_type")) or "company_news",
            "published_date": published,
            "event_age_days": self.i(row.get("event_age_days"), default=-1),
            "opportunity_type": news_type,
            "opportunity_category": self.s(row.get("opportunity_category")) or "COMPANY_INTEL",
            "summary": self.s(row.get("summary")) or signal,
            "company_news_signal": signal,
            "opportunity_score": self.i(row.get("opportunity_score"), default=55),
            "effective_opportunity_score": self.i(
                row.get("effective_opportunity_score"), default=55
            ),
            "recency_weight": self.f(row.get("recency_weight"), default=1.0),
            "confidence_score": self.i(row.get("confidence_score"), default=70),
            "lead_readiness_score": self.i(row.get("lead_readiness_score"), default=55),
            "validation_status": self.s(row.get("validation_status")) or "REVIEW_REQUIRED",
            "source_tier": self.i(row.get("source_tier"), default=2),
            "discovery_date": self.s(row.get("discovery_date")),
        }
        self.upsert(Opportunity, opp_id, values)
        return RowResult(written=True, review_queued=res.review_queued)
