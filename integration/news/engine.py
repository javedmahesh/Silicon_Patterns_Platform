"""News Intelligence Engine — collect -> extract -> resolve -> opportunities.

Ties the pieces together while reusing the existing downstream pipeline:

    adapters.fetch  ->  news_articles      (source metadata, article-level dedup)
    extraction      ->  N signals/article  (multi-signal)
    resolver        ->  company_domain     (existing CompanyResolver, unchanged)
    dedup           ->  one opportunity per business event, all reporting sources
                        attached; different events for a company stay separate
    -> opportunities (rich AI fields) -> lead scoring/dashboard read them unchanged

Nothing downstream is redesigned: opportunities remain the same table the scorer,
company timeline, and API already consume.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from integration.ingestors.ats_hosts import company_domain_or_blank
from integration.news import adapters, dedup
from integration.news.extraction import (
    ExtractedSignal,
    extract_opportunities,
    extract_primary_company,
)
from integration.resolver import CompanyResolver
from master_db.models import (
    IngestionRun,
    NewsArticle,
    NewsSource,
    Opportunity,
    OpportunityArticle,
    OpportunityReview,
)

logger = logging.getLogger("integration.news.engine")


@dataclass
class NewsRunMetrics:
    articles_collected: int = 0
    articles_new: int = 0
    opportunities_created: int = 0
    opportunities_updated: int = 0
    sources_attached: int = 0
    duplicates_merged: int = 0
    review_queued: int = 0
    rejected: int = 0
    errors: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def status(self) -> str:
        if self.rejected and not (self.opportunities_created or self.opportunities_updated):
            return "partial" if self.opportunities_created + self.opportunities_updated == 0 and self.articles_collected else "failed"
        return "success"


def _opp_id(fingerprint: str) -> str:
    return "OPP-" + fingerprint.upper()


def _group_id(company_domain: str, seed: str) -> str:
    return "GRP-" + hashlib.sha1(f"{company_domain}|{seed}".encode()).hexdigest()[:12].upper()


def _iso_date(value: str | None) -> str:
    """Feed date -> 'YYYY-MM-DD' (chronologically sortable). Unparseable/blank in ->
    the trimmed original out (never invents a date)."""
    dt = dedup._parse_date(value or "")
    return dt.date().isoformat() if dt is not None else (value or "").strip()


def _published_on_or_before(published_at: str | None, cutoff: datetime) -> bool:
    """True when an article's publish time parses to <= *cutoff* (already seen). An
    unparseable / missing date returns False (safe: process it, dedup is the backstop)."""
    dt = dedup._parse_date(published_at or "")
    if dt is None:
        return False
    cutoff = cutoff if cutoff.tzinfo is not None else cutoff.replace(tzinfo=timezone.utc)
    return dt <= cutoff


class NewsIntelligenceEngine:
    """Runs the News Collection Engine over one or more sources / article batches."""

    def __init__(self, session: Session, *, resolver: CompanyResolver | None = None,
                 create_stub: bool = True, mode: str = "pipeline") -> None:
        self.session = session
        self.resolver = resolver or CompanyResolver(session)
        self.create_stub = create_stub
        self.mode = mode

    # ---------------------------------------------------------------- collect
    def collect(self, sources: Iterable[NewsSource], *,
                raw_by_source: dict[int, str] | None = None,
                rows_by_source: dict[int, list[dict[str, Any]]] | None = None,
                incremental: bool = True) -> list[dict[str, Any]]:
        """Fetch + normalize articles from each enabled source. Returns article dicts
        (also persisted as ``news_articles`` when new). Never raises on a dead feed.

        Incremental: each live source sends its ``last_collected_at`` as
        ``If-Modified-Since`` (skip whole feed on 304) AND articles published at or
        before ``last_collected_at`` are dropped — so a re-run only processes genuinely
        new items. Article-level ``content_hash`` dedup is the final backstop."""
        raw_by_source = raw_by_source or {}
        rows_by_source = rows_by_source or {}
        collected: list[dict[str, Any]] = []
        for src in sources:
            if not getattr(src, "enabled", True):
                continue
            prev = getattr(src, "last_collected_at", None) if incremental else None
            raw = raw_by_source.get(src.id)
            try:
                arts = adapters.fetch_articles(
                    src, raw=raw, rows=rows_by_source.get(src.id),
                    incremental=(incremental and raw is None))
            except Exception as exc:  # isolate one bad source
                logger.warning("[news] source %s failed: %s", getattr(src, "name", "?"), exc)
                continue
            kept = 0
            for a in arts:
                if prev is not None and _published_on_or_before(a.get("published_at"), prev):
                    continue  # already seen in a prior run — incremental skip
                a.setdefault("source_id", getattr(src, "id", None))
                a.setdefault("source_credibility", getattr(src, "credibility", 50))
                collected.append(a)
                kept += 1
            logger.info("[news] source '%s': %d new (of %d fetched)",
                        getattr(src, "name", "?"), kept, len(arts))
            src.last_collected_at = datetime.now(timezone.utc)
        return collected

    # ------------------------------------------------------------- ingest
    def ingest_articles(self, articles: Iterable[dict[str, Any]]) -> NewsRunMetrics:
        """Extract -> resolve -> upsert opportunities for a batch of article dicts."""
        m = NewsRunMetrics()
        for article in articles:
            m.articles_collected += 1
            try:
                self._ingest_one(article, m)
            except Exception as exc:  # one bad article never aborts the batch
                m.rejected += 1
                m.errors.append(str(exc))
                logger.warning("[news] article failed: %s", exc)
        return m

    def _ingest_one(self, article: dict[str, Any], m: NewsRunMetrics) -> None:
        name = (article.get("company_name") or "").strip()
        raw_domain = article.get("company_domain") or article.get("website") or ""
        domain = company_domain_or_blank(raw_domain)

        signals = extract_opportunities(article)
        if not signals:
            return
        # Live RSS/Google-Alerts articles carry no company field — derive the company
        # from the headline/extracted organizations so the resolver can match/stub it.
        if not name and not domain:
            orgs = signals[0].organizations if signals else []
            name = extract_primary_company(article.get("title") or "", orgs)
            article["company_name"] = name

        res = self.resolver.resolve(
            domain=domain or None, name=name or None,
            website=(article.get("website") or None), source_engine="news",
            source_ref=(article.get("url") or ""), create_stub=self.create_stub,
        )
        if res.review_queued:
            m.review_queued += 1
        if res.company_domain is None:
            # opportunities.company_domain is NOT NULL -> cannot attach.
            m.rejected += 1
            return

        na = self._persist_article(article, res.company_domain, name)

        canon = dedup.canonical_url(article.get("url") or "")
        # Normalize to ISO (YYYY-MM-DD) so published_date sorts/filters chronologically
        # regardless of the feed's format (RFC-822 pubDate vs ISO vs bare date).
        published = _iso_date(article.get("published_at"))
        title = (article.get("title") or "").strip()

        group_id = ""
        for sig in signals:
            fp = dedup.entity_fingerprint(res.company_domain, sig.opportunity_type,
                                          sig.salient_entities(), published)
            existing = self._find_existing(res.company_domain, sig.opportunity_type, fp,
                                            title, published)
            if existing is not None:
                group_id = group_id or existing.related_group_id or _group_id(res.company_domain, fp)
                attached = self._attach_source(existing, article, canon, na)
                if attached:
                    m.sources_attached += 1
                m.duplicates_merged += 1
                m.opportunities_updated += 1
                if not existing.related_group_id:
                    existing.related_group_id = group_id
            else:
                group_id = group_id or _group_id(res.company_domain, fp)
                opp = self._create_opportunity(res, name, sig, fp, canon, title, published,
                                               article, group_id)
                self._attach_source(opp, article, canon, na)
                m.sources_attached += 1
                m.opportunities_created += 1
        self.session.flush()

    # ------------------------------------------------------------- helpers
    def _persist_article(self, article: dict[str, Any], company_domain: str,
                         company_name: str) -> NewsArticle | None:
        canon = dedup.canonical_url(article.get("url") or "")
        ntitle = dedup.normalize_title(article.get("title") or "")
        chash = dedup.content_hash(canon, ntitle)
        if not chash:
            return None
        existing = self.session.scalar(select(NewsArticle).where(NewsArticle.content_hash == chash))
        if existing is not None:
            return existing
        na = NewsArticle(
            source_id=article.get("source_id"),
            adapter_type=article.get("adapter_type") or "file",
            publisher=article.get("publisher") or "",
            source_name=article.get("source_name") or "",
            url=(article.get("url") or "")[:1024],
            canonical_url=canon[:1024],
            title=article.get("title") or "",
            normalized_title=ntitle[:512],
            body=article.get("body") or "",
            company_domain=company_domain,
            company_name=company_name,
            entities={},
            content_hash=chash,
            published_at=(article.get("published_at") or "")[:64],
            processed=True,
        )
        self.session.add(na)
        self.session.flush()
        return na

    def _find_existing(self, company_domain: str, event_type: str, fingerprint: str,
                       title: str, published_at: str) -> Opportunity | None:
        opp = self.session.get(Opportunity, _opp_id(fingerprint))
        if opp is not None:
            return opp
        candidates = self.session.scalars(
            select(Opportunity).where(
                Opportunity.company_domain == company_domain,
                Opportunity.opportunity_type == event_type,
            )
        ).all()
        for c in candidates:
            if dedup.is_same_event(
                company_domain=company_domain, opportunity_type=event_type,
                title=title, published_at=published_at,
                other_title=c.article_title, other_published_at=c.published_date,
                same_company=True,
            ):
                return c
        return None

    def _create_opportunity(self, res, company_name: str, sig: ExtractedSignal, fingerprint: str,
                            canonical: str, title: str, published: str,
                            article: dict[str, Any], group_id: str) -> Opportunity:
        feed_row = article.get("_feed_row") or {}
        opp = Opportunity(
            opportunity_id=_opp_id(fingerprint),
            company_domain=res.company_domain,
            canonical_company_id=res.canonical_company_id or "",
            company_name=company_name,
            country=(sig.countries[0] if sig.countries else (feed_row.get("country") or "")),
            article_title=title,
            article_url=(article.get("url") or "")[:1024],
            source=article.get("publisher") or article.get("source_name") or "",
            source_type=article.get("source_type") or article.get("adapter_type") or "",
            published_date=published,
            opportunity_type=sig.opportunity_type,
            opportunity_category="NEWS_INTEL",
            summary=sig.ai_summary,
            opportunity_score=sig.opportunity_score,
            effective_opportunity_score=sig.effective_opportunity_score,
            confidence_score=sig.confidence,
            lead_readiness_score=sig.lead_readiness_score,
            validation_status="REVIEW_REQUIRED",
            # rich AI intelligence
            executive_summary=sig.executive_summary,
            ai_summary=sig.ai_summary,
            why_this_matters=sig.why_this_matters,
            business_impact=sig.business_impact,
            ai_reasoning=sig.ai_reasoning,
            opportunity_subtype=sig.opportunity_subtype,
            technologies=sig.technologies,
            products=sig.products,
            people=sig.people,
            organizations=sig.organizations,
            countries=sig.countries,
            keywords=sig.keywords,
            confidence_breakdown=sig.confidence_breakdown,
            source_credibility=sig.source_credibility,
            lifecycle_status="NEW",
            is_relevant=True,
            canonical_url=canonical[:1024],
            normalized_title=dedup.normalize_title(title)[:512],
            entity_fingerprint=fingerprint,
            related_group_id=group_id,
        )
        self.session.add(opp)
        self.session.flush()
        return opp

    def _attach_source(self, opp: Opportunity, article: dict[str, Any], canonical: str,
                       na: NewsArticle | None) -> bool:
        """Attach a reporting source to *opp* (dedup by canonical url). Returns True if new."""
        canon = canonical or dedup.canonical_url(article.get("url") or "") or (article.get("url") or "")
        exists = self.session.scalar(
            select(OpportunityArticle).where(
                OpportunityArticle.opportunity_id == opp.opportunity_id,
                OpportunityArticle.canonical_url == canon,
            )
        )
        if exists is not None:
            return False
        self.session.add(OpportunityArticle(
            opportunity_id=opp.opportunity_id,
            article_id=(na.id if na is not None else None),
            url=(article.get("url") or "")[:1024],
            canonical_url=canon[:1024],
            publisher=article.get("publisher") or "",
            source_name=article.get("source_name") or "",
            source_type=article.get("source_type") or article.get("adapter_type") or "",
            title=article.get("title") or "",
            credibility=int(article.get("source_credibility") or 0),
            published_at=(article.get("published_at") or "")[:64],
        ))
        return True

    # --------------------------------------------------------------- run
    def run(self, *, sources: Iterable[NewsSource] | None = None,
            articles: Iterable[dict[str, Any]] | None = None,
            raw_by_source: dict[int, str] | None = None,
            rows_by_source: dict[int, list[dict[str, Any]]] | None = None) -> NewsRunMetrics:
        """Collect from *sources* and/or ingest an explicit *articles* batch, recording
        an ``ingestion_runs`` audit row like every other engine."""
        run = IngestionRun(engine="news", mode=self.mode, status="running", source_path="news")
        self.session.add(run)
        self.session.flush()

        batch: list[dict[str, Any]] = list(articles or [])
        if sources is not None:
            batch += self.collect(sources, raw_by_source=raw_by_source, rows_by_source=rows_by_source)

        m = self.ingest_articles(batch)
        m.articles_new = sum(1 for _ in batch)  # collected this run
        run.status = "success" if not m.errors else "partial"
        run.finished_at = datetime.now(timezone.utc)
        run.rows_in = m.articles_collected
        run.rows_upserted = m.opportunities_created + m.opportunities_updated
        run.rows_rejected = m.rejected
        run.rows_review_queued = m.review_queued
        self.session.flush()
        logger.info("[news] collected=%d created=%d updated=%d dup=%d rejected=%d",
                    m.articles_collected, m.opportunities_created, m.opportunities_updated,
                    m.duplicates_merged, m.rejected)
        return m


# ---------------------------------------------------------- orchestrator glue
def enrich_opportunity(session: Session, opp: Opportunity, *, force: bool = False) -> bool:
    """Backfill the rich AI intelligence fields on an *existing* opportunity in place.

    Used by the daily pipeline after the blog / company-news ingestors write their
    rows (single-signal, count-preserving): it derives the rich fields from the row's
    own article_title + summary and ensures a self ``opportunity_articles`` source
    exists. Never changes opportunity_type or the numeric scores that lead scoring
    reads, and never overwrites already-populated intelligence unless ``force``.
    """
    if opp.ai_summary and not force:
        return False
    article = {
        "title": opp.article_title or opp.summary or opp.company_news_signal,
        "body": opp.summary or "",
        "company_name": opp.company_name,
        "company_domain": opp.company_domain,
        "url": opp.article_url,
        "published_at": opp.published_date,
        "publisher": opp.source,
        "source_type": opp.source_type,
        "_feed_row": {
            "opportunity_type": opp.opportunity_type,
            "technology_mentioned": opp.technology_mentioned,
            "product_mentioned": opp.product_mentioned,
            "partner_company": opp.partner_company,
            "country": opp.country,
            "source_tier": opp.source_tier,
        },
    }
    signals = extract_opportunities(article)
    if not signals:
        return False
    sig = next((s for s in signals if s.opportunity_type == opp.opportunity_type), signals[0])
    opp.executive_summary = opp.executive_summary or sig.executive_summary
    opp.ai_summary = sig.ai_summary
    opp.why_this_matters = opp.why_this_matters or sig.why_this_matters
    opp.business_impact = opp.business_impact or sig.business_impact
    opp.ai_reasoning = opp.ai_reasoning or sig.ai_reasoning
    opp.opportunity_subtype = opp.opportunity_subtype or sig.opportunity_subtype
    opp.technologies = opp.technologies or sig.technologies
    opp.products = opp.products or sig.products
    opp.people = opp.people or sig.people
    opp.organizations = opp.organizations or sig.organizations
    opp.countries = opp.countries or sig.countries
    opp.keywords = opp.keywords or sig.keywords
    opp.confidence_breakdown = opp.confidence_breakdown or sig.confidence_breakdown
    opp.source_credibility = opp.source_credibility or sig.source_credibility
    opp.lifecycle_status = opp.lifecycle_status or "NEW"
    if not opp.canonical_url:
        opp.canonical_url = dedup.canonical_url(opp.article_url or "")[:1024]
    if not opp.normalized_title:
        opp.normalized_title = dedup.normalize_title(opp.article_title or "")[:512]
    if not opp.entity_fingerprint:
        opp.entity_fingerprint = dedup.entity_fingerprint(
            opp.company_domain, opp.opportunity_type, sig.salient_entities(), opp.published_date)
    if not opp.related_group_id:
        opp.related_group_id = _group_id(opp.company_domain, opp.entity_fingerprint)
    _ensure_self_source(session, opp)
    return True


def _ensure_self_source(session: Session, opp: Opportunity) -> None:
    canon = opp.canonical_url or dedup.canonical_url(opp.article_url or "") or opp.opportunity_id
    exists = session.scalar(
        select(OpportunityArticle).where(
            OpportunityArticle.opportunity_id == opp.opportunity_id,
            OpportunityArticle.canonical_url == canon,
        )
    )
    if exists is not None:
        return
    session.add(OpportunityArticle(
        opportunity_id=opp.opportunity_id, url=opp.article_url or "", canonical_url=canon[:1024],
        publisher=opp.source, source_name=opp.source, source_type=opp.source_type,
        title=opp.article_title or "", credibility=opp.source_credibility,
        published_at=opp.published_date or "",
    ))


def enrich_new_opportunities(session: Session, *, limit: int | None = None) -> int:
    """Enrich every opportunity still missing AI intelligence. Returns the count enriched."""
    q = select(Opportunity).where(
        (Opportunity.ai_summary == "") | (Opportunity.ai_summary.is_(None))
    )
    if limit:
        q = q.limit(limit)
    n = 0
    for opp in session.scalars(q):
        if enrich_opportunity(session, opp):
            n += 1
    session.flush()
    return n


def refresh_opportunities(session: Session, *, sources: Iterable[NewsSource] | None = None,
                          articles: Iterable[dict[str, Any]] | None = None,
                          rows_by_source: dict[int, list[dict[str, Any]]] | None = None,
                          raw_by_source: dict[int, str] | None = None,
                          wipe: bool = True) -> NewsRunMetrics:
    """Delete ONLY opportunity/news signal data, then regenerate from the upgraded
    engine. Companies, users, lead scores, career data and configuration are left
    untouched (news_sources config is preserved).

    Guard: refuses to wipe when there is nothing to regenerate from (no sources and
    no articles), so it can never silently empty the Opportunities page.
    """
    have_input = bool(articles) or bool(sources)
    if wipe and not have_input:
        raise ValueError("refresh_opportunities: nothing to regenerate from — pass sources/articles")
    if wipe:
        # children first (FKs), then opportunities. News sources config is kept.
        session.execute(delete(OpportunityReview))
        session.execute(delete(OpportunityArticle))
        session.execute(delete(Opportunity))
        session.execute(delete(NewsArticle))
        session.flush()
    engine = NewsIntelligenceEngine(session)
    return engine.run(sources=sources, articles=articles,
                      rows_by_source=rows_by_source, raw_by_source=raw_by_source)


# --------------------------------------------------------- source configuration
def enabled_news_sources(session: Session) -> list[NewsSource]:
    """Configured, enabled sources with a usable URL — what the pipeline collects."""
    return list(session.scalars(
        select(NewsSource).where(NewsSource.enabled.is_(True), NewsSource.url != "")
        .order_by(NewsSource.name)
    ))


def seed_news_sources(session: Session, feeds: Iterable[dict[str, Any]] | None = None) -> dict[str, int]:
    """Idempotently upsert the curated production feeds into ``news_sources``.

    Config/DB-driven: matches an existing row by (name) so re-seeding never
    duplicates and never clobbers an analyst's manual enable/disable or a pasted
    Google-Alerts URL (URL is only filled when still blank). Returns created/updated
    counts."""
    from integration.news.adapters import DEFAULT_SEMI_FEEDS

    feeds = list(feeds if feeds is not None else DEFAULT_SEMI_FEEDS)
    created = updated = 0
    for f in feeds:
        row = session.scalar(select(NewsSource).where(NewsSource.name == f["name"]))
        if row is None:
            session.add(NewsSource(
                name=f["name"], adapter_type=f.get("adapter_type", "rss"),
                url=f.get("url", ""), publisher=f.get("publisher", ""),
                credibility=int(f.get("credibility", 50)), enabled=bool(f.get("enabled", True)),
            ))
            created += 1
        else:
            # Keep analyst edits: only backfill a blank URL / publisher; never flip enabled.
            if not row.url and f.get("url"):
                row.url = f["url"]
            if not row.publisher and f.get("publisher"):
                row.publisher = f["publisher"]
            updated += 1
    session.flush()
    return {"created": created, "updated": updated, "total": len(feeds)}
