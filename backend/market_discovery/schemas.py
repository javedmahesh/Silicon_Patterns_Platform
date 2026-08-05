"""Source-agnostic discovery types.

These are the contract between *data providers* (discovery sources) and the
*Market Discovery Engine*. A source's entire job is to return
:class:`DiscoveryCandidate` objects; everything downstream — validation, resolution,
duplicate detection, confidence, persistence — belongs to the engine.

Nothing here imports a source, a connector, an HTTP client, or a database session.
That is deliberate: a candidate must be constructible, comparable and testable
without any of them, which is what keeps the pipeline deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CandidateStatus(str, Enum):
    """Where a candidate ended up after one pipeline pass."""

    NEW = "new"                  # first time the platform has seen it
    UPDATED = "updated"          # already known; fields refreshed
    DUPLICATE = "duplicate"      # resolves to a candidate/company already seen this run
    REJECTED = "rejected"        # failed validation — never persisted
    BELOW_THRESHOLD = "below_threshold"   # valid but not confident enough to promote


class SourceStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"        # reachable but partially failing (rate-limited, stale)
    UNAVAILABLE = "unavailable"  # unreachable or unconfigured
    DISABLED = "disabled"        # switched off by configuration


@dataclass(slots=True, frozen=True)
class SourceCapabilities:
    """What a source can do, so the engine can plan without knowing who it is.

    Frozen because the registry caches these; a source that needs to change its
    capabilities at runtime should return a new instance from ``capabilities()``.
    """

    name: str
    # Fields this source can populate. Lets the engine skip a source when a run only
    # needs, say, funding data, and lets confidence weight corroboration correctly.
    provides: frozenset[str] = frozenset()
    supports_incremental: bool = False    # can fetch "since last run" rather than all
    supports_pagination: bool = False
    requires_credentials: bool = False
    rate_limit_per_minute: int = 0        # 0 = unspecified/unlimited
    description: str = ""

    def can_provide(self, field_name: str) -> bool:
        return field_name in self.provides


@dataclass(slots=True)
class SourceHealth:
    name: str
    status: SourceStatus = SourceStatus.OK
    detail: str = ""
    checked_at: datetime = field(default_factory=_utcnow)

    @property
    def usable(self) -> bool:
        return self.status in (SourceStatus.OK, SourceStatus.DEGRADED)


@dataclass(slots=True)
class DiscoveryContext:
    """Per-run inputs a source may use. Passed by the engine, never constructed by
    a source. ``since`` is None on a full run and set on an incremental one."""

    run_id: str = ""
    since: datetime | None = None
    limit: int | None = None              # max candidates a source should return
    now: datetime = field(default_factory=_utcnow)
    options: dict[str, Any] = field(default_factory=dict)
    # Candidate keys the platform has already stored. Supplied by the engine (which
    # owns the database) so a source can skip re-fetching a company it has seen —
    # incremental discovery without a source ever running a query. Empty on a full
    # run; a source that ignores it is still correct, only slower.
    known_candidate_keys: frozenset[str] = frozenset()
    # Provider-native ids already stored, keyed by source name. A connector usually
    # knows only this at listing time — a Wellfound slug, a Crunchbase uuid — whereas
    # candidate_key is derived from the company's domain, which is learned later from
    # the detail page. Both are supplied so a source can skip on whichever it has.
    known_source_ids: dict[str, frozenset[str]] = field(default_factory=dict)

    def already_known(self, candidate_key: str) -> bool:
        return bool(candidate_key) and candidate_key in self.known_candidate_keys

    def already_seen(self, source: str, source_id: str) -> bool:
        """Has this exact provider record been stored before?"""
        if not source or not source_id:
            return False
        return source_id in self.known_source_ids.get(source, frozenset())


@dataclass(slots=True)
class DiscoveryCandidate:
    """One potential market entrant, normalized and source-independent.

    Identity is deliberately weak here — a candidate may arrive with only a name.
    Turning that into the platform's canonical ``company_domain`` is the resolver's
    job, not the source's.
    """

    company_name: str = ""
    website: str = ""
    linkedin_url: str = ""
    description: str = ""
    industry: str = ""
    headquarters: str = ""
    country: str = ""
    founded_year: str = ""
    employee_count: str = ""
    funding_stage: str = ""
    technologies: tuple[str, ...] = ()
    markets: tuple[str, ...] = ()

    # Provenance — which provider surfaced this, and its identifier over there.
    source: str = ""
    source_id: str = ""
    source_url: str = ""

    first_seen: datetime = field(default_factory=_utcnow)
    last_seen: datetime = field(default_factory=_utcnow)
    confidence: float = 0.0

    # Untouched provider response, kept for audit and for re-normalizing later
    # without re-fetching. Never read by business logic.
    raw_payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ---- engine-populated (a source must not set these) --------------------
    # The normalized domain the resolver settled on, and the candidate's stable key.
    company_domain: str = ""
    candidate_key: str = ""

    def merged_with(self, other: "DiscoveryCandidate") -> "DiscoveryCandidate":
        """Combine two sightings of the same company.

        Field-level rule: a non-empty existing value wins over an incoming one, so a
        later, thinner sighting can never blank out data already gathered. Collections
        union. ``first_seen`` keeps the earliest, ``last_seen`` the latest, and
        confidence takes the max — corroboration is applied separately by the
        confidence engine, which can see the full source set.
        """
        def pick(a: str, b: str) -> str:
            return a if a else b

        def union(a: tuple[str, ...], b: tuple[str, ...]) -> tuple[str, ...]:
            return tuple(dict.fromkeys([*a, *b]))

        sources = tuple(dict.fromkeys(
            [*self.metadata.get("sources", (self.source,) if self.source else ()),
             *other.metadata.get("sources", (other.source,) if other.source else ())]
        ))
        metadata = {**other.metadata, **self.metadata, "sources": sources}
        return replace(
            self,
            company_name=pick(self.company_name, other.company_name),
            website=pick(self.website, other.website),
            linkedin_url=pick(self.linkedin_url, other.linkedin_url),
            description=pick(self.description, other.description),
            industry=pick(self.industry, other.industry),
            headquarters=pick(self.headquarters, other.headquarters),
            country=pick(self.country, other.country),
            founded_year=pick(self.founded_year, other.founded_year),
            employee_count=pick(self.employee_count, other.employee_count),
            funding_stage=pick(self.funding_stage, other.funding_stage),
            technologies=union(self.technologies, other.technologies),
            markets=union(self.markets, other.markets),
            company_domain=pick(self.company_domain, other.company_domain),
            first_seen=min(self.first_seen, other.first_seen),
            last_seen=max(self.last_seen, other.last_seen),
            confidence=max(self.confidence, other.confidence),
            raw_payload=self.raw_payload or other.raw_payload,
            metadata=metadata,
        )

    @property
    def sources(self) -> tuple[str, ...]:
        """Every provider that has surfaced this candidate (>1 after a merge)."""
        recorded = self.metadata.get("sources")
        if recorded:
            return tuple(recorded)
        return (self.source,) if self.source else ()


@dataclass(slots=True)
class ValidationIssue:
    field: str
    reason: str


@dataclass(slots=True)
class ProcessedCandidate:
    """A candidate plus everything the pipeline decided about it."""

    candidate: DiscoveryCandidate
    status: CandidateStatus
    issues: list[ValidationIssue] = field(default_factory=list)
    confidence_factors: dict[str, float] = field(default_factory=dict)
    resolution_notes: str = ""
    duplicate_of: str = ""       # candidate_key of the record it merged into
    # Set ONLY when the platform resolver matched an existing `companies` row. The
    # candidate's own `company_domain` is merely what it claims (from its website), so
    # the two must not be conflated: provenance writes FK to companies.
    resolved_company_domain: str = ""

    @property
    def accepted(self) -> bool:
        return self.status in (CandidateStatus.NEW, CandidateStatus.UPDATED)


@dataclass(slots=True)
class SourceOutcome:
    """One source's contribution to a run — including how it failed."""

    name: str
    status: SourceStatus = SourceStatus.OK
    fetched: int = 0
    duration_ms: int = 0
    error: str = ""

    @property
    def failed(self) -> bool:
        return bool(self.error)


@dataclass(slots=True)
class DiscoveryResult:
    """The outcome of one full discovery run."""

    run_id: str = ""
    started_at: datetime = field(default_factory=_utcnow)
    finished_at: datetime | None = None
    duration_ms: int = 0
    sources: list[SourceOutcome] = field(default_factory=list)
    processed: list[ProcessedCandidate] = field(default_factory=list)

    @property
    def fetched(self) -> int:
        return sum(s.fetched for s in self.sources)

    def _count(self, status: CandidateStatus) -> int:
        return sum(1 for p in self.processed if p.status is status)

    @property
    def new(self) -> int:
        return self._count(CandidateStatus.NEW)

    @property
    def updated(self) -> int:
        return self._count(CandidateStatus.UPDATED)

    @property
    def duplicates(self) -> int:
        return self._count(CandidateStatus.DUPLICATE)

    @property
    def rejected(self) -> int:
        return self._count(CandidateStatus.REJECTED)

    @property
    def below_threshold(self) -> int:
        return self._count(CandidateStatus.BELOW_THRESHOLD)

    @property
    def accepted(self) -> list[ProcessedCandidate]:
        return [p for p in self.processed if p.accepted]

    @property
    def failed_sources(self) -> list[SourceOutcome]:
        return [s for s in self.sources if s.failed]

    @property
    def status(self) -> str:
        """success | partial | failed — mirrors the orchestrator's stage vocabulary."""
        if not self.sources:
            return "success"          # a run with zero sources is a valid no-op
        if len(self.failed_sources) == len(self.sources):
            return "failed"
        return "partial" if self.failed_sources else "success"

    def summary(self) -> str:
        return (f"sources={len(self.sources)} fetched={self.fetched} new={self.new} "
                f"updated={self.updated} duplicates={self.duplicates} "
                f"rejected={self.rejected} below_threshold={self.below_threshold}")
