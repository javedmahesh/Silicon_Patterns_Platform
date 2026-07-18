"""Data model for the historical synchronization engine.

All dataclasses are plain, deterministic and JSON-serializable (``to_dict``) so the
same :class:`SyncPreview` can drive a test assertion, a CLI print, an API response
and — in Phase 3 — the import UI, unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Per-company classification (the bucket a company lands in).
NEW = "new"
UPDATE = "update"
UNCHANGED = "unchanged"
DUPLICATE = "duplicate"
CONFLICT = "conflict"
CLASSIFICATIONS = (NEW, UPDATE, UNCHANGED, DUPLICATE, CONFLICT)

# How the company was matched to the platform (resolution priority order).
MATCH_EXACT_DOMAIN = "EXACT_DOMAIN"   # 1) normalized website/domain
MATCH_CANONICAL_NAME = "CANONICAL_NAME"  # 2) canonical company name_key
MATCH_ALIAS = "ALIAS"                 # 3) known alias (seed or persisted)
MATCH_FUZZY_NAME = "FUZZY_NAME"       # near-match name (lower confidence)
MATCH_NEW = "NEW"                     # valid domain, no platform match
MATCH_INVALID = "INVALID"            # no usable domain and no name match

# Per-field diff action, under the update rules.
FILL = "fill"          # platform empty -> set from history
STALE = "update"       # platform value is a low-quality stub -> refresh
FIELD_CONFLICT = "conflict"  # both present & differ on a real company -> manual review


@dataclass(slots=True)
class HistoricalCompany:
    """One distinct company parsed from the uploaded historical file (company-owned
    fields only). ``fields`` holds the proposed company-owned values keyed by the
    ``companies`` column name (see ``sync.normalization.COMPANY_OWNED_FIELDS``)."""

    raw_name: str
    website: str = ""
    fields: dict[str, str] = field(default_factory=dict)
    source_ref: str = ""            # provenance (e.g. "row 42" / first row seen)
    row_count: int = 1             # how many source rows collapsed into this company

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_name": self.raw_name, "website": self.website,
            "fields": dict(self.fields), "source_ref": self.source_ref,
            "row_count": self.row_count,
        }


@dataclass(slots=True)
class FieldChange:
    field: str
    current: str
    proposed: str
    action: str  # FILL | STALE | FIELD_CONFLICT

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "current": self.current,
                "proposed": self.proposed, "action": self.action}


@dataclass(slots=True)
class CompanySyncResult:
    raw_name: str
    classification: str            # one of CLASSIFICATIONS
    match_type: str                # one of MATCH_*
    resolved_domain: str | None    # the platform company_domain this maps to
    canonical_company_id: str
    confidence: float
    changes: list[FieldChange] = field(default_factory=list)
    conflicts: list[FieldChange] = field(default_factory=list)
    duplicate_of: str | None = None   # source_ref of the earlier record it duplicates
    source_ref: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_name": self.raw_name,
            "classification": self.classification,
            "match_type": self.match_type,
            "resolved_domain": self.resolved_domain,
            "canonical_company_id": self.canonical_company_id,
            "confidence": round(self.confidence, 4),
            "changes": [c.to_dict() for c in self.changes],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "duplicate_of": self.duplicate_of,
            "source_ref": self.source_ref,
            "notes": self.notes,
        }


@dataclass(slots=True)
class SyncStats:
    total_input: int = 0
    new: int = 0
    updated: int = 0
    unchanged: int = 0
    duplicates: int = 0
    conflicts: int = 0
    alias_matches: int = 0
    exact_domain_matches: int = 0
    fuzzy_matches: int = 0
    fields_to_fill: int = 0
    fields_to_update: int = 0
    fields_conflicting: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_input": self.total_input, "new": self.new, "updated": self.updated,
            "unchanged": self.unchanged, "duplicates": self.duplicates,
            "conflicts": self.conflicts, "alias_matches": self.alias_matches,
            "exact_domain_matches": self.exact_domain_matches,
            "fuzzy_matches": self.fuzzy_matches, "fields_to_fill": self.fields_to_fill,
            "fields_to_update": self.fields_to_update,
            "fields_conflicting": self.fields_conflicting,
        }


@dataclass(slots=True)
class SyncPreview:
    """The complete, deterministic result of reconciling a historical batch.

    ``results`` is the full per-company list (deterministically ordered). The named
    buckets are filtered views over it (by ``source_ref``) so a UI can render tabs
    without re-deriving anything. ``alias_matches`` is a cross-cutting report list,
    not a mutually-exclusive bucket.
    """

    results: list[CompanySyncResult] = field(default_factory=list)
    stats: SyncStats = field(default_factory=SyncStats)
    generated_at: str = ""

    def _by(self, classification: str) -> list[CompanySyncResult]:
        return [r for r in self.results if r.classification == classification]

    @property
    def new(self) -> list[CompanySyncResult]:
        return self._by("new")

    @property
    def updated(self) -> list[CompanySyncResult]:
        return self._by("update")

    @property
    def unchanged(self) -> list[CompanySyncResult]:
        return self._by("unchanged")

    @property
    def duplicates(self) -> list[CompanySyncResult]:
        return self._by("duplicate")

    @property
    def conflicts(self) -> list[CompanySyncResult]:
        return self._by("conflict")

    @property
    def alias_matches(self) -> list[CompanySyncResult]:
        return [r for r in self.results if r.match_type in ("ALIAS", "FUZZY_NAME")]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "stats": self.stats.to_dict(),
            "results": [r.to_dict() for r in self.results],
            "buckets": {
                "new": [r.source_ref for r in self.new],
                "updated": [r.source_ref for r in self.updated],
                "unchanged": [r.source_ref for r in self.unchanged],
                "duplicates": [r.source_ref for r in self.duplicates],
                "conflicts": [r.source_ref for r in self.conflicts],
                "alias_matches": [r.source_ref for r in self.alias_matches],
            },
        }


# ===================================================================
# Decision Maker synchronization (Phase 3)
# ===================================================================

# How a DM was matched to the platform (resolution priority order).
DM_MATCH_LINKEDIN = "LINKEDIN_URL"       # 1) canonical LinkedIn URL
DM_MATCH_EMAIL = "WORK_EMAIL"            # 2) work email
DM_MATCH_COMPANY_NAME = "COMPANY_NAME"   # 3) company + full name
DM_MATCH_COMPANY_NAME_TITLE = "COMPANY_NAME_TITLE"  # 4) company + name + designation
DM_MATCH_NEW = "NEW"                     # valid identity, no platform match
DM_MATCH_INVALID = "INVALID"            # no LinkedIn URL — cannot create (unique NOT NULL)


@dataclass(slots=True)
class HistoricalDecisionMaker:
    """One decision-maker row parsed from the uploaded historical file, with the
    company context needed to resolve it to a canonical company first."""

    full_name: str
    company_name: str = ""
    company_website: str = ""
    linkedin_url: str = ""          # raw
    work_email: str = ""            # raw
    fields: dict[str, str] = field(default_factory=dict)   # DM-owned proposed values
    source_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"full_name": self.full_name, "company_name": self.company_name,
                "company_website": self.company_website, "linkedin_url": self.linkedin_url,
                "work_email": self.work_email, "fields": dict(self.fields),
                "source_ref": self.source_ref}


@dataclass(slots=True)
class DmSyncResult:
    full_name: str
    classification: str            # new | update | unchanged | duplicate | conflict | invalid
    match_type: str                # one of DM_MATCH_*
    resolved_company_domain: str | None
    matched_dm_id: int | None
    confidence: float
    changes: list[FieldChange] = field(default_factory=list)
    conflicts: list[FieldChange] = field(default_factory=list)
    duplicate_of: str | None = None
    source_ref: str = ""
    linkedin_canonical: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name, "classification": self.classification,
            "match_type": self.match_type,
            "resolved_company_domain": self.resolved_company_domain,
            "matched_dm_id": self.matched_dm_id, "confidence": round(self.confidence, 4),
            "changes": [c.to_dict() for c in self.changes],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "duplicate_of": self.duplicate_of, "source_ref": self.source_ref,
            "linkedin_canonical": self.linkedin_canonical, "notes": self.notes,
        }


@dataclass(slots=True)
class DmSyncStats:
    total_input: int = 0
    new: int = 0
    updated: int = 0
    unchanged: int = 0
    duplicates: int = 0
    conflicts: int = 0
    invalid: int = 0
    linkedin_matches: int = 0
    email_matches: int = 0
    name_matches: int = 0
    companies_resolved: int = 0
    companies_unresolved: int = 0
    fields_to_fill: int = 0
    fields_conflicting: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_input": self.total_input, "new": self.new, "updated": self.updated,
            "unchanged": self.unchanged, "duplicates": self.duplicates,
            "conflicts": self.conflicts, "invalid": self.invalid,
            "linkedin_matches": self.linkedin_matches, "email_matches": self.email_matches,
            "name_matches": self.name_matches, "companies_resolved": self.companies_resolved,
            "companies_unresolved": self.companies_unresolved,
            "fields_to_fill": self.fields_to_fill, "fields_conflicting": self.fields_conflicting,
        }


@dataclass(slots=True)
class DmSyncPreview:
    results: list[DmSyncResult] = field(default_factory=list)
    stats: DmSyncStats = field(default_factory=DmSyncStats)
    generated_at: str = ""

    def _by(self, c: str) -> list[DmSyncResult]:
        return [r for r in self.results if r.classification == c]

    @property
    def new(self):        return self._by("new")
    @property
    def updated(self):    return self._by("update")
    @property
    def unchanged(self):  return self._by("unchanged")
    @property
    def duplicates(self): return self._by("duplicate")
    @property
    def conflicts(self):  return self._by("conflict")
    @property
    def invalid(self):    return self._by("invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "stats": self.stats.to_dict(),
            "results": [r.to_dict() for r in self.results],
            "buckets": {
                "new": [r.source_ref for r in self.new],
                "updated": [r.source_ref for r in self.updated],
                "unchanged": [r.source_ref for r in self.unchanged],
                "duplicates": [r.source_ref for r in self.duplicates],
                "conflicts": [r.source_ref for r in self.conflicts],
                "invalid": [r.source_ref for r in self.invalid],
            },
        }
