"""The company reconciliation engine — deterministic, read-only, batch.

Given a batch of :class:`HistoricalCompany` records, match each against the platform
(priority: normalized domain → canonical name → alias → fuzzy name), diff the
company-owned fields under the update rules, detect in-batch duplicates, and return a
:class:`SyncPreview`. **Nothing is written to the database.**
"""
from __future__ import annotations

import difflib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from master_db.models import Company, CompanyAlias
from sync.aliases import canonical_name_key
from sync.models import (
    CompanySyncResult,
    FieldChange,
    HistoricalCompany,
    SyncPreview,
    SyncStats,
    FIELD_CONFLICT,
    FILL,
    STALE,
    MATCH_ALIAS,
    MATCH_CANONICAL_NAME,
    MATCH_EXACT_DOMAIN,
    MATCH_FUZZY_NAME,
    MATCH_INVALID,
    MATCH_NEW,
)
from sync.normalization import (
    COMPANY_OWNED_FIELDS,
    cached_canonical_id,
    cached_name_key,
    clean_text,
    usable_domain,
)

_FUZZY_THRESHOLD = 0.90
_CONF = {
    MATCH_EXACT_DOMAIN: 1.0, MATCH_CANONICAL_NAME: 0.97,
    MATCH_ALIAS: 0.95, MATCH_NEW: 0.0, MATCH_INVALID: 0.0,
}


class PlatformCompanyIndex:
    """In-memory snapshot of the companies table, loaded once per batch.

    Turns per-record resolution into O(1) dict lookups (plus one bounded difflib scan
    for fuzzy) instead of a query per record — the "batch reconciliation / incremental
    comparison" requirement. Built from ordered SELECTs only; holds no session and
    never writes.
    """

    __slots__ = ("by_domain", "by_name_key", "alias_map", "_name_keys_sorted")

    def __init__(self) -> None:
        self.by_domain: dict[str, dict] = {}
        self.by_name_key: dict[str, str] = {}
        self.alias_map: dict[str, str] = {}
        self._name_keys_sorted: list[str] = []

    @classmethod
    def build(cls, session: Session) -> "PlatformCompanyIndex":
        idx = cls()
        rows = session.execute(
            select(Company).order_by(Company.company_domain)
        ).scalars()
        for c in rows:
            snap = {f: getattr(c, f, "") or "" for f in COMPANY_OWNED_FIELDS}
            snap["is_stub"] = bool(c.is_stub)
            snap["name_key"] = c.name_key or ""
            snap["canonical_company_id"] = c.canonical_company_id or ""
            idx.by_domain[c.company_domain] = snap
            if c.name_key:
                idx.by_name_key.setdefault(c.name_key, c.company_domain)
        for name_key_, domain in session.execute(
            select(CompanyAlias.name_key, CompanyAlias.company_domain)
            .order_by(CompanyAlias.company_domain)
        ).all():
            if name_key_:
                idx.alias_map.setdefault(name_key_, domain)
        idx._name_keys_sorted = sorted(idx.by_name_key)
        return idx

    def match(self, raw_name: str, website: str) -> tuple[str | None, str, float]:
        """Resolve one record to ``(domain|None, match_type, confidence)``. Read-only."""
        dom = usable_domain(website)
        if dom and dom in self.by_domain:
            return dom, MATCH_EXACT_DOMAIN, 1.0

        nk = cached_name_key(raw_name)
        cnk = canonical_name_key(raw_name)  # alias-canonicalized key
        if nk and nk in self.by_name_key:
            return self.by_name_key[nk], MATCH_CANONICAL_NAME, _CONF[MATCH_CANONICAL_NAME]
        if cnk and cnk != nk and cnk in self.by_name_key:
            return self.by_name_key[cnk], MATCH_ALIAS, _CONF[MATCH_ALIAS]
        if nk and nk in self.alias_map:
            return self.alias_map[nk], MATCH_ALIAS, _CONF[MATCH_ALIAS]
        if cnk and cnk in self.alias_map:
            return self.alias_map[cnk], MATCH_ALIAS, _CONF[MATCH_ALIAS]

        fuzzy = self._fuzzy(nk)
        if fuzzy is not None:
            return fuzzy[0], MATCH_FUZZY_NAME, fuzzy[1]

        if dom:
            return dom, MATCH_NEW, 0.0
        return None, MATCH_INVALID, 0.0

    def _fuzzy(self, key: str) -> tuple[str, float] | None:
        if not key or not self._name_keys_sorted:
            return None
        best_key, best_score = None, 0.0
        for cand in self._name_keys_sorted:           # sorted -> deterministic ties
            score = difflib.SequenceMatcher(None, key, cand).ratio()
            if score > best_score:
                best_key, best_score = cand, score
        if best_key is not None and best_score >= _FUZZY_THRESHOLD:
            return self.by_name_key[best_key], best_score
        return None


def _norm_equal(field: str, a: str, b: str) -> bool:
    if field == "website":
        da, db = usable_domain(a), usable_domain(b)
        if da or db:
            return da == db
    if field == "company_name":
        return cached_name_key(a) == cached_name_key(b)
    return a.casefold() == b.casefold()


# The company's identity name is authoritative once the platform has one: a historical
# export carries alias spellings ("AMD" for "Advanced Micro Devices"), so company_name
# is fill-only — set it when missing, otherwise leave the platform's name untouched
# (never a silent overwrite, never a noisy conflict; a differing spelling is an alias,
# learned separately). All other company-owned fields follow the full update rules.
_FILL_ONLY_FIELDS: frozenset[str] = frozenset({"company_name"})

# Model default placeholders that mean "no real value yet" — treated as empty so a
# real historical value fills them (rather than being flagged a conflict against a
# non-answer like company_type='UNKNOWN').
_SENTINELS: frozenset[str] = frozenset({"", "unknown", "pending", "n/a", "na", "none"})


def _decide(field: str, current: str, proposed: str, is_stub: bool) -> FieldChange | None:
    """Apply the update rules to one company-owned field.

    fill missing · refresh a low-quality stub · NEVER overwrite richer real data
    (that becomes a conflict for manual review, not a silent clobber).
    """
    cur, prop = clean_text(current), clean_text(proposed)
    if cur.casefold() in _SENTINELS:
        cur = ""                          # a placeholder default is "missing", not data
    if not prop or prop.casefold() in _SENTINELS:
        return None                       # never blank out / never write a placeholder
    if _norm_equal(field, cur, prop):
        return None                       # already equivalent
    if not cur:
        return FieldChange(field, cur, prop, FILL)
    if field in _FILL_ONLY_FIELDS:
        return None                       # platform's existing name wins; not a conflict
    return FieldChange(field, cur, prop, STALE if is_stub else FIELD_CONFLICT)


def _diff_existing(rec: HistoricalCompany, snap: dict) -> tuple[list[FieldChange], list[FieldChange]]:
    changes: list[FieldChange] = []
    conflicts: list[FieldChange] = []
    is_stub = bool(snap.get("is_stub"))
    for f in COMPANY_OWNED_FIELDS:
        proposed = rec.fields.get(f, "") if f != "company_name" else (rec.fields.get(f) or rec.raw_name)
        if f == "website" and not proposed:
            proposed = rec.website
        change = _decide(f, snap.get(f, ""), proposed, is_stub)
        if change is None:
            continue
        (conflicts if change.action == FIELD_CONFLICT else changes).append(change)
    return changes, conflicts


def _new_company_changes(rec: HistoricalCompany) -> list[FieldChange]:
    changes: list[FieldChange] = []
    for f in COMPANY_OWNED_FIELDS:
        proposed = rec.fields.get(f, "") if f != "company_name" else (rec.fields.get(f) or rec.raw_name)
        if f == "website" and not proposed:
            proposed = rec.website
        proposed = clean_text(proposed)
        if proposed:
            changes.append(FieldChange(f, "", proposed, FILL))
    return changes


def reconcile_companies(
    session: Session,
    records: list[HistoricalCompany],
    *,
    enable_fuzzy: bool = True,
) -> SyncPreview:
    """Reconcile *records* against the platform and return a deterministic preview.

    Pure/read-only: builds one :class:`PlatformCompanyIndex` from SELECTs and never
    mutates the session or the database.
    """
    index = PlatformCompanyIndex.build(session)
    stats = SyncStats(total_input=len(records))
    results: list[CompanySyncResult] = []

    # Deterministic processing order so "first record wins" for duplicates is stable.
    ordered = sorted(
        records,
        key=lambda r: (usable_domain(r.website), cached_name_key(r.raw_name), r.source_ref),
    )
    seen_identity: dict[str, str] = {}   # identity -> source_ref of first occurrence

    for rec in ordered:
        domain, match_type, confidence = index.match(rec.raw_name, rec.website)
        if not enable_fuzzy and match_type == MATCH_FUZZY_NAME:
            domain, match_type, confidence = (
                (usable_domain(rec.website), MATCH_NEW, 0.0)
                if usable_domain(rec.website) else (None, MATCH_INVALID, 0.0)
            )

        # identity for in-batch duplicate detection
        if domain:
            identity = f"dom:{domain}"
        elif match_type == MATCH_INVALID:
            identity = f"invalid:{rec.source_ref}"      # never collapses
        else:
            identity = f"name:{canonical_name_key(rec.raw_name)}"

        if identity in seen_identity:
            stats.duplicates += 1
            results.append(CompanySyncResult(
                raw_name=rec.raw_name, classification="duplicate", match_type=match_type,
                resolved_domain=domain,
                canonical_company_id=cached_canonical_id(domain or "", rec.raw_name),
                confidence=confidence, duplicate_of=seen_identity[identity],
                source_ref=rec.source_ref,
                notes=f"same company as {seen_identity[identity]} within this upload",
            ))
            continue
        seen_identity[identity] = rec.source_ref

        if match_type in (MATCH_EXACT_DOMAIN, MATCH_CANONICAL_NAME, MATCH_ALIAS, MATCH_FUZZY_NAME):
            snap = index.by_domain[domain]
            changes, conflicts = _diff_existing(rec, snap)
            if conflicts:
                classification = "conflict"; stats.conflicts += 1
            elif changes:
                classification = "update"; stats.updated += 1
            else:
                classification = "unchanged"; stats.unchanged += 1
            stats.fields_to_fill += sum(1 for c in changes if c.action == FILL)
            stats.fields_to_update += sum(1 for c in changes if c.action == STALE)
            stats.fields_conflicting += len(conflicts)
            if match_type == MATCH_EXACT_DOMAIN:
                stats.exact_domain_matches += 1
            if match_type == MATCH_FUZZY_NAME:
                stats.fuzzy_matches += 1
            if match_type in (MATCH_ALIAS, MATCH_FUZZY_NAME):
                stats.alias_matches += 1
            results.append(CompanySyncResult(
                raw_name=rec.raw_name, classification=classification, match_type=match_type,
                resolved_domain=domain, canonical_company_id=snap.get("canonical_company_id", ""),
                confidence=confidence, changes=changes, conflicts=conflicts,
                source_ref=rec.source_ref,
            ))
        elif match_type == MATCH_NEW:
            stats.new += 1
            changes = _new_company_changes(rec)
            stats.fields_to_fill += len(changes)
            results.append(CompanySyncResult(
                raw_name=rec.raw_name, classification="new", match_type=match_type,
                resolved_domain=domain, canonical_company_id=cached_canonical_id(domain, rec.raw_name),
                confidence=0.0, changes=changes, source_ref=rec.source_ref,
                notes="would create a new company",
            ))
        else:  # INVALID — no usable domain and no name match; can't create a PK
            stats.conflicts += 1
            results.append(CompanySyncResult(
                raw_name=rec.raw_name, classification="conflict", match_type=MATCH_INVALID,
                resolved_domain=None, canonical_company_id="", confidence=0.0,
                source_ref=rec.source_ref,
                notes="no usable company domain and no name match — needs a domain before import",
            ))

    results.sort(key=lambda r: (r.resolved_domain or "~", cached_name_key(r.raw_name), r.source_ref))
    return SyncPreview(
        results=results, stats=stats,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
