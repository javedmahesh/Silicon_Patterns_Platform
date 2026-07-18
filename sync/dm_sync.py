"""Decision-maker reconciliation engine — deterministic, read-only, batch (Phase 3).

Every historical decision maker first resolves to a canonical company via the Phase-2
:class:`PlatformCompanyIndex` (reusing aliases + company resolution; never creating a
duplicate company), then matches an existing platform decision maker by priority:

  1. canonical LinkedIn URL   2. work email   3. company + full name   4. + designation

and is classified new / update / unchanged / duplicate / conflict / invalid under the
update rules. **Nothing is written to the database.** A record with no usable LinkedIn
URL is ``invalid`` (the platform's ``decision_makers.linkedin_url`` is UNIQUE NOT NULL,
so it cannot be created as-is). Two rows that share a LinkedIn URL / email but name
*different people* are a ``conflict``, never a silent merge.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from master_db.models import DecisionMaker
from sync.company_sync import PlatformCompanyIndex
from sync.linkedin import canonical_linkedin_url
from sync.models import (
    DmSyncPreview,
    DmSyncResult,
    DmSyncStats,
    FieldChange,
    HistoricalDecisionMaker,
    FIELD_CONFLICT,
    FILL,
    DM_MATCH_COMPANY_NAME,
    DM_MATCH_COMPANY_NAME_TITLE,
    DM_MATCH_EMAIL,
    DM_MATCH_INVALID,
    DM_MATCH_LINKEDIN,
    DM_MATCH_NEW,
)
from sync.normalization import (
    DM_OWNED_FIELDS,
    VALUE_SENTINELS,
    canonical_email,
    clean_text,
    norm_person_name,
    norm_title,
)

# DM identity fields matched on — never overwritten by an import.
_DM_FILL_ONLY: frozenset[str] = frozenset({"linkedin_url"})
_NAME_FIELDS = frozenset({"first_name", "last_name", "full_name"})


class PlatformDecisionMakerIndex:
    """In-memory snapshot of ``decision_makers`` for O(1) batch matching. Read-only."""

    __slots__ = ("by_linkedin", "by_email", "by_company_name", "by_company_name_title", "snap")

    def __init__(self) -> None:
        self.by_linkedin: dict[str, int] = {}
        self.by_email: dict[str, int] = {}
        self.by_company_name: dict[tuple[str, str], int] = {}
        self.by_company_name_title: dict[tuple[str, str, str], int] = {}
        self.snap: dict[int, dict] = {}

    @classmethod
    def build(cls, session: Session) -> "PlatformDecisionMakerIndex":
        idx = cls()
        for dm in session.execute(select(DecisionMaker).order_by(DecisionMaker.id)).scalars():
            full = (dm.full_name or f"{dm.first_name or ''} {dm.last_name or ''}").strip()
            pkey = norm_person_name(full)
            snap = {f: (getattr(dm, f, None) or "") for f in DM_OWNED_FIELDS}
            snap["linkedin_canonical"] = canonical_linkedin_url(dm.linkedin_url)
            snap["person_key"] = pkey
            snap["company_domain"] = dm.company_domain or ""
            idx.snap[dm.id] = snap
            li = snap["linkedin_canonical"]
            if li:
                idx.by_linkedin.setdefault(li, dm.id)
            em = canonical_email(dm.work_email)
            if em:
                idx.by_email.setdefault(em, dm.id)
            dom = dm.company_domain or ""
            if dom and pkey:
                idx.by_company_name.setdefault((dom, pkey), dm.id)
                t = norm_title(dm.current_title)
                if t:
                    idx.by_company_name_title.setdefault((dom, pkey, t), dm.id)
        return idx

    def match(self, *, linkedin: str, email: str, domain: str, person_key: str,
              title: str) -> tuple[int | None, str, float]:
        if linkedin and linkedin in self.by_linkedin:
            return self.by_linkedin[linkedin], DM_MATCH_LINKEDIN, 1.0
        if email and email in self.by_email:
            return self.by_email[email], DM_MATCH_EMAIL, 0.9
        if domain and person_key:
            k = (domain, person_key)
            if k in self.by_company_name:
                return self.by_company_name[k], DM_MATCH_COMPANY_NAME, 0.8
            if title and (domain, person_key, title) in self.by_company_name_title:
                return self.by_company_name_title[(domain, person_key, title)], DM_MATCH_COMPANY_NAME_TITLE, 0.75
        return None, DM_MATCH_NEW, 0.0


def _dm_norm_equal(field: str, a: str, b: str) -> bool:
    if field == "work_email":
        return canonical_email(a) == canonical_email(b)
    if field == "organization_linkedin":
        return canonical_linkedin_url(a) == canonical_linkedin_url(b) or a.casefold() == b.casefold()
    if field in _NAME_FIELDS:
        return norm_person_name(a) == norm_person_name(b)
    if field == "current_title":
        return norm_title(a) == norm_title(b)
    return a.casefold() == b.casefold()


def _decide(field: str, current: str, proposed: str) -> FieldChange | None:
    """fill-missing · never overwrite existing platform data (differ -> conflict)."""
    cur, prop = clean_text(current), clean_text(proposed)
    if cur.casefold() in VALUE_SENTINELS:
        cur = ""
    if not prop or prop.casefold() in VALUE_SENTINELS:
        return None
    if _dm_norm_equal(field, cur, prop):
        return None
    if not cur:
        return FieldChange(field, cur, prop, FILL)
    if field in _DM_FILL_ONLY:
        return None
    return FieldChange(field, cur, prop, FIELD_CONFLICT)


def _diff(rec: HistoricalDecisionMaker, snap: dict) -> tuple[list[FieldChange], list[FieldChange]]:
    changes: list[FieldChange] = []
    conflicts: list[FieldChange] = []
    for f in DM_OWNED_FIELDS:
        proposed = rec.fields.get(f, "")
        if f == "work_email" and not proposed:
            proposed = rec.work_email
        if f == "full_name" and not proposed:
            proposed = rec.full_name
        ch = _decide(f, snap.get(f, ""), proposed)
        if ch is None:
            continue
        (conflicts if ch.action == FIELD_CONFLICT else changes).append(ch)
    return changes, conflicts


def reconcile_decision_makers(
    session: Session,
    records: list[HistoricalDecisionMaker],
    *,
    company_index: PlatformCompanyIndex | None = None,
) -> DmSyncPreview:
    """Reconcile *records* against platform decision makers. Pure / read-only."""
    company_index = company_index or PlatformCompanyIndex.build(session)
    dm_index = PlatformDecisionMakerIndex.build(session)
    stats = DmSyncStats(total_input=len(records))
    results: list[DmSyncResult] = []

    def sort_key(r: HistoricalDecisionMaker):
        return (canonical_linkedin_url(r.linkedin_url), canonical_email(r.work_email),
                norm_person_name(r.full_name), r.source_ref)

    seen: dict[str, tuple[str, str]] = {}   # identity -> (source_ref, person_key) of first

    for rec in sorted(records, key=sort_key):
        li = canonical_linkedin_url(rec.linkedin_url)
        em = canonical_email(rec.work_email)
        pkey = norm_person_name(rec.full_name)
        title = norm_title(rec.fields.get("current_title", ""))
        domain, _ctype, _ = company_index.match(rec.company_name, rec.company_website)
        if domain:
            stats.companies_resolved += 1
        else:
            stats.companies_unresolved += 1

        # in-batch identity
        if li:
            identity = f"li:{li}"
        elif em:
            identity = f"em:{em}"
        elif domain and pkey:
            identity = f"cn:{domain}|{pkey}"
        else:
            identity = f"invalid:{rec.source_ref}"

        base = DmSyncResult(
            full_name=rec.full_name, classification="", match_type="",
            resolved_company_domain=domain, matched_dm_id=None, confidence=0.0,
            source_ref=rec.source_ref, linkedin_canonical=li,
        )

        if identity in seen and not identity.startswith("invalid:"):
            first_ref, first_pkey = seen[identity]
            # shared LinkedIn/email but a different person -> conflict, never merge
            if identity[:3] in ("li:", "em:") and pkey and first_pkey and pkey != first_pkey:
                base.classification = "conflict"; base.match_type = DM_MATCH_INVALID
                base.notes = f"identity {identity[3:]} shared with a different person ({first_ref})"
                stats.conflicts += 1
            else:
                base.classification = "duplicate"; base.duplicate_of = first_ref
                base.notes = f"same person as {first_ref} within this upload"
                stats.duplicates += 1
            results.append(base)
            continue
        if not identity.startswith("invalid:"):
            seen[identity] = (rec.source_ref, pkey)

        dm_id, match_type, conf = dm_index.match(
            linkedin=li, email=em, domain=domain or "", person_key=pkey, title=title)
        base.match_type = match_type
        base.confidence = conf

        if dm_id is not None:
            snap = dm_index.snap[dm_id]
            base.matched_dm_id = dm_id
            # matched by URL/email but the platform person is someone else -> conflict
            if match_type in (DM_MATCH_LINKEDIN, DM_MATCH_EMAIL) and pkey and snap["person_key"] and pkey != snap["person_key"]:
                base.classification = "conflict"
                base.conflicts = [FieldChange("full_name", snap.get("full_name", "") or snap["person_key"], rec.full_name, FIELD_CONFLICT)]
                base.notes = f"{match_type} matches a different platform person (dm {dm_id})"
                stats.conflicts += 1; stats.fields_conflicting += 1
            else:
                changes, conflicts = _diff(rec, snap)
                base.changes, base.conflicts = changes, conflicts
                if conflicts:
                    base.classification = "conflict"; stats.conflicts += 1
                elif changes:
                    base.classification = "update"; stats.updated += 1
                else:
                    base.classification = "unchanged"; stats.unchanged += 1
                stats.fields_to_fill += len(changes)
                stats.fields_conflicting += len(conflicts)
                if match_type == DM_MATCH_LINKEDIN:
                    stats.linkedin_matches += 1
                elif match_type == DM_MATCH_EMAIL:
                    stats.email_matches += 1
                else:
                    stats.name_matches += 1
        elif li:
            base.classification = "new"; base.match_type = DM_MATCH_NEW
            base.changes = [FieldChange(f, "", clean_text(rec.fields.get(f, "") or (rec.work_email if f == "work_email" else rec.full_name if f == "full_name" else "")), FILL)
                            for f in DM_OWNED_FIELDS
                            if clean_text(rec.fields.get(f, "") or (rec.work_email if f == "work_email" else rec.full_name if f == "full_name" else ""))]
            stats.new += 1; stats.fields_to_fill += len(base.changes)
        else:
            base.classification = "invalid"; base.match_type = DM_MATCH_INVALID
            base.notes = "no usable LinkedIn URL — cannot create (linkedin_url is UNIQUE NOT NULL)"
            stats.invalid += 1

        results.append(base)

    results.sort(key=lambda r: (r.resolved_company_domain or "~", norm_person_name(r.full_name), r.source_ref))
    return DmSyncPreview(results=results, stats=stats,
                         generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
