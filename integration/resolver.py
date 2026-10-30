"""Canonical company resolution.

Turns whatever identity a source record carries (a domain, a website, a raw
company name, or some combination) into the master join key ``company_domain``,
creating data only under the confirmed **stub + review queue** policy:

  * **Exact domain** — the normalized domain already exists in ``companies`` →
    resolved with full confidence.
  * **New stub** — a *valid domain* with no company row yet → create a
    low-confidence stub company (``is_stub=True``, ``validation_status='STUB'``)
    and queue it for review. Downstream rows (opportunities/jobs) can attach
    immediately; a human later confirms or merges the stub.
  * **Alias / fuzzy name** — no domain, but the name matches a known alias
    (exact) or an existing company name (fuzzy) → resolved to that domain.
  * **Unresolved** — no domain and no confident name match → queued for review,
    returns ``company_domain=None``. The pipeline never blocks on this. This is
    the common path for LinkedIn decision-makers whose employer can't yet be
    mapped to a domain.

The resolver never deletes or rewrites engine data and never touches the four
engines. It depends only on :mod:`integration.normalizer` and the three
resolution-layer ORM models, so it runs against a local SQLite database in P0.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from integration.normalizer import (
    canonical_company_id,
    name_key as make_name_key,
    normalize_domain,
)
from integration.competitors import is_excluded_domain
from master_db.models import Company, CompanyAlias, ResolutionReviewQueue

# Confidence assigned to each resolution outcome (0–1).
_CONF_EXACT = 1.0
_CONF_ALIAS = 0.95
_CONF_STUB = 0.30


@dataclass(slots=True)
class Resolution:
    """Outcome of a resolve() call."""

    company_domain: str | None
    canonical_company_id: str | None
    match_type: str          # EXACT_DOMAIN | ALIAS | FUZZY_NAME | NEW_STUB | UNRESOLVED
    confidence: float
    created: bool            # a stub company row was created
    review_queued: bool      # a review_queue row was created
    notes: str = ""

    @property
    def resolved(self) -> bool:
        return self.company_domain is not None


class CompanyResolver:
    """Resolves company identity against the master DB.

    Parameters
    ----------
    session:
        An open SQLAlchemy :class:`~sqlalchemy.orm.Session` bound to the master
        DB (Postgres in production, SQLite locally for P0).
    fuzzy_threshold:
        Minimum similarity (0–1) for a name-only fuzzy match to count.
    enable_fuzzy:
        Toggle the difflib name matcher. The fuzzy pass is O(n) over company
        name keys — fine for P0/local; in production it is replaced by a
        ``pg_trgm`` GIN-indexed similarity query (see migration 0001).
    """

    def __init__(
        self,
        session: Session,
        *,
        fuzzy_threshold: float = 0.90,
        trgm_threshold: float = 0.45,
        enable_fuzzy: bool = True,
    ) -> None:
        self.session = session
        self.fuzzy_threshold = fuzzy_threshold      # difflib ratio (SQLite fallback)
        self.trgm_threshold = trgm_threshold        # pg_trgm similarity (Postgres)
        self.enable_fuzzy = enable_fuzzy

    # ------------------------------------------------------------------ public

    def resolve(
        self,
        *,
        domain: str | None = None,
        name: str | None = None,
        website: str | None = None,
        source_engine: str = "",
        source_ref: str = "",
        create_stub: bool = True,
    ) -> Resolution:
        """Resolve a source record to a ``company_domain``. See module docstring
        for the decision order."""
        norm_domain = normalize_domain(domain) or normalize_domain(website)

        if norm_domain:
            return self._resolve_by_domain(
                norm_domain, name, website, source_engine, source_ref, create_stub
            )
        return self._resolve_by_name(name, website, source_engine, source_ref)

    def register_alias(
        self, name: str, company_domain: str, *, source: str = "", confidence: float = 1.0
    ) -> CompanyAlias | None:
        """Record a name→domain alias (idempotent on ``name_key`` + domain).

        Returns the alias row, or ``None`` when the name has no usable key or the
        target company does not exist.
        """
        key = make_name_key(name)
        if not key or not self._get_company(company_domain):
            return None
        existing = self.session.scalar(
            select(CompanyAlias).where(
                CompanyAlias.name_key == key,
                CompanyAlias.company_domain == company_domain,
            )
        )
        if existing:
            return existing
        alias = CompanyAlias(
            alias=name.strip(),
            name_key=key,
            company_domain=company_domain,
            source=source,
            confidence=confidence,
        )
        self.session.add(alias)
        self.session.flush()
        return alias

    # --------------------------------------------------------------- internals

    def _resolve_by_domain(
        self,
        domain: str,
        name: str | None,
        website: str | None,
        source_engine: str,
        source_ref: str,
        create_stub: bool,
    ) -> Resolution:
        if is_excluded_domain(domain):
            # Competitor (service provider) domain — never store, stub, or queue it.
            return Resolution(None, None, "UNRESOLVED", 0.0, created=False,
                              review_queued=False, notes="excluded competitor domain")
        company = self._get_company(domain)
        if company is not None:
            # Known company: opportunistically learn the name spelling.
            if name:
                self.register_alias(name, domain, source=source_engine or "resolve")
            return Resolution(
                company_domain=domain,
                canonical_company_id=company.canonical_company_id,
                match_type="EXACT_DOMAIN",
                confidence=_CONF_EXACT,
                created=False,
                review_queued=False,
            )

        # Valid, unknown domain.
        if create_stub:
            stub = self._create_stub(domain, name, website, source_engine)
            self._queue_review(
                raw_name=name, raw_domain=domain, raw_website=website,
                source_engine=source_engine, source_ref=source_ref,
                suggested_domain=domain, match_type="NEW_STUB", confidence=_CONF_STUB,
                notes="Stub company created from a domain not yet in Industry Discovery.",
            )
            return Resolution(
                company_domain=domain,
                canonical_company_id=stub.canonical_company_id,
                match_type="NEW_STUB",
                confidence=_CONF_STUB,
                created=True,
                review_queued=True,
                notes="stub created",
            )

        # Caller declined stub creation: queue and leave unattached.
        self._queue_review(
            raw_name=name, raw_domain=domain, raw_website=website,
            source_engine=source_engine, source_ref=source_ref,
            suggested_domain=domain, match_type="UNRESOLVED", confidence=0.0,
            notes="Valid domain with no company row; stub creation disabled.",
        )
        return Resolution(None, None, "UNRESOLVED", 0.0, created=False, review_queued=True)

    def _resolve_by_name(
        self,
        name: str | None,
        website: str | None,
        source_engine: str,
        source_ref: str,
    ) -> Resolution:
        key = make_name_key(name)
        if not key:
            # Nothing actionable at all — do not clutter the review queue.
            return Resolution(None, None, "UNRESOLVED", 0.0, created=False, review_queued=False)

        # 1) Exact alias hit.
        alias = self.session.scalar(
            select(CompanyAlias).where(CompanyAlias.name_key == key)
        )
        if alias is not None:
            company = self._get_company(alias.company_domain)
            cid = company.canonical_company_id if company else canonical_company_id(alias.company_domain, name)
            return Resolution(
                company_domain=alias.company_domain,
                canonical_company_id=cid,
                match_type="ALIAS",
                confidence=_CONF_ALIAS,
                created=False,
                review_queued=False,
            )

        # 2) Fuzzy match against existing company name keys.
        if self.enable_fuzzy:
            hit = self._fuzzy_find(key)
            if hit is not None:
                domain, score = hit
                # Learn the new spelling so next time it is an exact alias hit.
                self.register_alias(name, domain, source=f"{source_engine}:fuzzy", confidence=score)
                company = self._get_company(domain)
                cid = company.canonical_company_id if company else canonical_company_id(domain, name)
                return Resolution(
                    company_domain=domain,
                    canonical_company_id=cid,
                    match_type="FUZZY_NAME",
                    confidence=score,
                    created=False,
                    review_queued=False,
                    notes=f"fuzzy score={score:.2f}",
                )

        # 3) No domain, no confident name match → queue for review.
        self._queue_review(
            raw_name=name, raw_domain="", raw_website=website,
            source_engine=source_engine, source_ref=source_ref,
            suggested_domain="", match_type="UNRESOLVED", confidence=0.0,
            notes="Name-only record with no alias or fuzzy match (e.g. LinkedIn employer).",
        )
        return Resolution(None, None, "UNRESOLVED", 0.0, created=False, review_queued=True)

    def _get_company(self, domain: str) -> Company | None:
        return self.session.get(Company, domain)

    def _fuzzy_find(self, key: str) -> tuple[str, float] | None:
        """Best (company_domain, score) whose name_key is similar to *key*.

        On PostgreSQL this is an index-ordered KNN query backed by the GiST
        ``ix_companies_name_key_gist`` index (``ORDER BY name_key <-> :k LIMIT 1``)
        — index-ordered and scale-independent, no full-table sort. On SQLite
        (local/tests) it falls back to the stdlib difflib scan.
        """
        if self.session.get_bind().dialect.name == "postgresql":
            return self._fuzzy_find_trgm(key)
        return self._fuzzy_find_difflib(key)

    def _fuzzy_find_trgm(self, key: str) -> tuple[str, float] | None:
        # KNN nearest-match: `name_key <-> :k` (trigram distance = 1 - similarity) is
        # served index-ordered by the GiST gist_trgm_ops index, so the single nearest
        # row is returned without scanning/sorting the whole table.
        row = self.session.execute(
            text(
                "SELECT company_domain, name_key <-> :k AS dist "
                "FROM companies WHERE name_key <> '' "
                "ORDER BY name_key <-> :k LIMIT 1"
            ),
            {"k": key},
        ).first()
        if row is None:
            return None
        similarity = 1.0 - float(row[1])
        return (str(row[0]), similarity) if similarity >= self.trgm_threshold else None

    def _fuzzy_find_difflib(self, key: str) -> tuple[str, float] | None:
        rows = self.session.execute(
            select(Company.company_domain, Company.name_key).where(Company.name_key != "")
        ).all()
        best_domain: str | None = None
        best_score = 0.0
        for domain, cand_key in rows:
            score = difflib.SequenceMatcher(None, key, cand_key).ratio()
            if score > best_score:
                best_domain, best_score = domain, score
        if best_domain is not None and best_score >= self.fuzzy_threshold:
            return best_domain, best_score
        return None

    def _create_stub(
        self, domain: str, name: str | None, website: str | None, source_engine: str
    ) -> Company:
        display_name = (name or domain).strip()
        stub = Company(
            company_domain=domain,
            canonical_company_id=canonical_company_id(domain, display_name),
            company_name=display_name,
            name_key=make_name_key(display_name),
            website=(website or "").strip(),
            validation_status="STUB",
            is_stub=True,
            confidence_score=_CONF_STUB,
            source=source_engine or "resolver",
            source_type="stub",
            prospect_type="UNKNOWN",
            company_tier="UNKNOWN",
            compliance_flag="UNKNOWN",
        )
        self.session.add(stub)
        self.session.flush()
        if name:
            self.register_alias(name, domain, source=source_engine or "resolver", confidence=_CONF_STUB)
        return stub

    def _queue_review(
        self,
        *,
        raw_name: str | None,
        raw_domain: str | None,
        raw_website: str | None,
        source_engine: str,
        source_ref: str,
        suggested_domain: str,
        match_type: str,
        confidence: float,
        notes: str,
    ) -> ResolutionReviewQueue:
        # Idempotent across re-ingestions: reuse an existing pending entry for the
        # same source record instead of stacking duplicate review rows.
        if source_ref:
            existing = self.session.scalar(
                select(ResolutionReviewQueue).where(
                    ResolutionReviewQueue.source_engine == source_engine,
                    ResolutionReviewQueue.source_record_ref == source_ref,
                    ResolutionReviewQueue.status == "pending",
                )
            )
            if existing is not None:
                return existing
        item = ResolutionReviewQueue(
            raw_name=(raw_name or "").strip(),
            raw_domain=(raw_domain or "").strip(),
            raw_website=(raw_website or "").strip(),
            source_engine=source_engine,
            source_record_ref=source_ref,
            suggested_domain=suggested_domain,
            match_type=match_type,
            confidence=confidence,
            status="pending",
            notes=notes,
        )
        self.session.add(item)
        self.session.flush()
        return item

