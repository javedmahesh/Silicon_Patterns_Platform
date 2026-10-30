"""Duplicate detection and canonical resolution for discovery candidates.

Two distinct jobs, deliberately separated:

* **Within a run** — several providers report the same company. Grouped on the
  deterministic ``candidate_key`` (domain → LinkedIn slug → comparison name) and
  merged into one record carrying every contributing source. Exact-key only: no
  fuzzy matching, no AI. See :class:`DuplicateStrategy` for the extension point.

* **Against the platform** — does this candidate already exist as a ``companies``
  row? Delegated to :class:`integration.resolver.CompanyResolver`, the platform's
  existing single answer to "what is this company's domain". Discovery does not get
  a second opinion, and it runs the resolver in **read-only mode**
  (``create_stub=False``) — promoting a candidate into a company is the service's
  decision after confidence has been applied, not the resolver's side effect.

Conflicts (two sources disagreeing on a field) are recorded, never silently
resolved: the merge keeps the first non-empty value and reports the disagreement so
a human or a later enrichment pass can adjudicate.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from backend.market_discovery.normalize import candidate_key, comparison_name
from backend.market_discovery.schemas import DiscoveryCandidate

logger = logging.getLogger("market_discovery.resolver")

#: Fields where two sources disagreeing is worth reporting. Free text (description)
#: is excluded — providers phrase it differently and that is not a conflict.
CONFLICT_FIELDS = (
    "website", "linkedin_url", "country", "headquarters", "founded_year", "funding_stage",
)


@dataclass(slots=True)
class FieldConflict:
    candidate_key: str
    field: str
    kept: str
    discarded: str
    kept_source: str
    discarded_source: str

    def __str__(self) -> str:      # pragma: no cover - log formatting
        return (f"{self.field}: kept {self.kept!r} ({self.kept_source}) over "
                f"{self.discarded!r} ({self.discarded_source})")


@dataclass(slots=True)
class MergeGroup:
    """One real-world company assembled from one or more sightings."""

    key: str
    candidate: DiscoveryCandidate
    members: list[DiscoveryCandidate] = field(default_factory=list)
    conflicts: list[FieldConflict] = field(default_factory=list)

    @property
    def is_duplicate(self) -> bool:
        return len(self.members) > 1

    @property
    def source_names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(m.source for m in self.members if m.source))


class DuplicateStrategy:
    """How two candidates are judged to be the same company.

    The default is exact ``candidate_key`` equality — fully deterministic, which the
    architecture requires today. Intelligent matching (trigram similarity, embedding
    distance, an LLM adjudicator) plugs in here by subclassing and overriding
    :meth:`key_for` and/or :meth:`same_company`, with no change to the resolver, the
    pipeline or any source.
    """

    def key_for(self, candidate: DiscoveryCandidate) -> str:
        return candidate.candidate_key or candidate_key(candidate)

    def same_company(self, a: DiscoveryCandidate, b: DiscoveryCandidate) -> bool:
        return bool(self.key_for(a)) and self.key_for(a) == self.key_for(b)


class DiscoveryResolver:
    """Groups duplicates, prepares merges, and maps candidates onto the platform."""

    def __init__(
        self,
        session: Session | None = None,
        *,
        strategy: DuplicateStrategy | None = None,
    ) -> None:
        self.session = session
        self.strategy = strategy or DuplicateStrategy()

    # ------------------------------------------------------------ within a run
    def group(self, candidates: list[DiscoveryCandidate]) -> list[MergeGroup]:
        """Collapse duplicates. Input order is preserved for the first sighting of
        each company, so the output is deterministic for a deterministic input."""
        groups: dict[str, MergeGroup] = {}
        order: list[str] = []
        for candidate in candidates:
            key = self.strategy.key_for(candidate)
            if not key:
                logger.debug("[discovery] candidate without an identity key dropped from grouping")
                continue
            existing = groups.get(key)
            if existing is None:
                groups[key] = MergeGroup(key=key, candidate=candidate, members=[candidate])
                order.append(key)
                continue
            conflicts = self._conflicts(key, existing.candidate, candidate)
            existing.conflicts.extend(conflicts)
            existing.candidate = existing.candidate.merged_with(candidate)
            existing.members.append(candidate)
            if conflicts:
                logger.info("[discovery] merge conflict on %s: %s", key,
                            "; ".join(str(c) for c in conflicts))
        return [groups[k] for k in order]

    @staticmethod
    def _conflicts(key: str, kept: DiscoveryCandidate,
                   incoming: DiscoveryCandidate) -> list[FieldConflict]:
        """Report fields where both sightings have a value and the values differ."""
        out: list[FieldConflict] = []
        for name in CONFLICT_FIELDS:
            a = (getattr(kept, name, "") or "").strip()
            b = (getattr(incoming, name, "") or "").strip()
            if a and b and a.casefold() != b.casefold():
                out.append(FieldConflict(
                    candidate_key=key, field=name, kept=a, discarded=b,
                    kept_source=kept.source, discarded_source=incoming.source,
                ))
        return out

    # ------------------------------------------------ against the platform
    def resolve_to_company(self, candidate: DiscoveryCandidate) -> tuple[str | None, str]:
        """``(company_domain | None, note)`` — is this already a known company?

        Read-only: never creates a stub and never queues a review. Discovery decides
        what to persist only after confidence has been applied.
        """
        if self.session is None:
            # Cannot consult the platform, so nothing can be asserted to exist. The
            # candidate's own company_domain is only what its website claims.
            return None, "unresolved (no session to check the platform)"
        try:
            from integration.resolver import CompanyResolver

            resolution = CompanyResolver(self.session).resolve(
                domain=candidate.company_domain or None,
                name=candidate.company_name or None,
                website=candidate.website or None,
                source_engine="market_discovery",
                source_ref=candidate.source_id or candidate.source_url,
                create_stub=False,
            )
            return resolution.company_domain, f"{resolution.match_type.lower()}"
        except Exception as exc:      # noqa: BLE001 - resolution must not fail a run
            logger.error("[discovery] company resolution raised for %s",
                         candidate.company_name, exc_info=True)
            return None, f"resolution error: {exc}"

    # ------------------------------------------------------------ merge prep
    @staticmethod
    def merge_plan(group: MergeGroup) -> dict[str, object]:
        """A description of what promoting this group would write.

        Returned rather than executed: the resolver never touches the database. The
        service applies it, which keeps every write in one place.
        """
        c = group.candidate
        return {
            "candidate_key": group.key,
            "company_domain": c.company_domain or None,
            "company_name": c.company_name,
            "website": c.website,
            "sources": list(group.source_names),
            "source_count": len(group.source_names),
            "conflicts": [
                {"field": x.field, "kept": x.kept, "discarded": x.discarded,
                 "kept_source": x.kept_source, "discarded_source": x.discarded_source}
                for x in group.conflicts
            ],
            "comparison_name": comparison_name(c.company_name),
        }
