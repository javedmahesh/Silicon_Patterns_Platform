"""Adapter: an uploaded historical Excel export → distinct ``HistoricalCompany`` records.

Companies only (Phase 2 does not touch decision makers). One export row is one
*contact*, so companies are denormalized across many rows; this collapses them into
one record per company, keeping only the company-owned fields the sync engine can act
on. Reading is tolerant of the messy headers found in Phase 1 (trailing spaces,
newlines) and works from a path or an in-memory buffer (for an upload).
"""
from __future__ import annotations

from pathlib import Path
from typing import IO

import openpyxl

from sync.models import HistoricalCompany, HistoricalDecisionMaker
from sync.normalization import cached_name_key, clean_text, usable_domain

# cleaned Excel header -> decision_makers-owned field it feeds (companies-only cols
# from _COLUMN_MAP provide the company context used to resolve the DM's employer).
_DM_COLUMN_MAP: dict[str, str] = {
    "contact first name": "first_name",
    "contact last name": "last_name",
    "first name": "first_name",
    "last name": "last_name",
    "designation": "current_title",
    "function": "functional_area",
    "seniority level": "seniority",
    "contact number": "work_phone",
    "person location": "location",
    "person country": "country",
}

# cleaned Excel header  ->  companies column it feeds. Only company-owned targets;
# contact/QA/score columns are intentionally ignored (companies-only import).
_COLUMN_MAP: dict[str, str] = {
    "company name": "company_name",
    "company website": "website",
    "website": "website",
    "company type": "company_type",
    "product category": "industry_category",
    "region": "country",
    "company city": "city",
    "company country": "country",
    "company linkedin": "company_linkedin",
}


def _pick_sheet(wb) -> str:
    for name in wb.sheetnames:
        ws = wb[name]
        header = next(ws.iter_rows(values_only=True), None) or ()
        cleaned = {clean_text(h).lower() for h in header}
        if "company name" in cleaned:
            return name
    return wb.sheetnames[0]


def load_historical_companies(
    source: str | Path | IO[bytes], *, sheet: str | None = None
) -> list[HistoricalCompany]:
    """Parse *source* into deduplicated per-company records (deterministic order)."""
    wb = openpyxl.load_workbook(source, read_only=True, data_only=True)
    try:
        sheet = sheet or _pick_sheet(wb)
        ws = wb[sheet]
        it = ws.iter_rows(values_only=True)
        header = [clean_text(h).lower() for h in (next(it, None) or ())]
        # cleaned header label -> its column index (first wins)
        col: dict[str, int] = {}
        for i, h in enumerate(header):
            if h in _COLUMN_MAP and h not in col:
                col[h] = i
        raw_rows = list(it)
    finally:
        wb.close()

    # merge rows into one record per company identity, deterministically
    merged: dict[str, HistoricalCompany] = {}
    for rownum, row in enumerate(raw_rows, start=2):
        if not any(c is not None and str(c).strip() for c in row):
            continue
        vals: dict[str, str] = {}
        for label, target in _COLUMN_MAP.items():
            i = col.get(label)
            if i is None or i >= len(row):
                continue
            v = clean_text(row[i])
            if v and not vals.get(target):
                vals[target] = v
        name = vals.get("company_name", "")
        website = vals.get("website", "")
        if not name and not website:
            continue
        dom = usable_domain(website)
        identity = f"dom:{dom}" if dom else f"name:{cached_name_key(name)}"
        if not identity.strip(":").split(":", 1)[1]:
            continue  # neither a usable domain nor a name key

        existing = merged.get(identity)
        if existing is None:
            merged[identity] = HistoricalCompany(
                raw_name=name or website, website=website,
                fields={k: v for k, v in vals.items()},
                source_ref=f"row {rownum}", row_count=1,
            )
        else:
            existing.row_count += 1
            for k, v in vals.items():                 # fill only-empties (first row wins)
                if v and not existing.fields.get(k):
                    existing.fields[k] = v
            if not existing.website and website:
                existing.website = website

    return sorted(merged.values(), key=lambda r: (usable_domain(r.website), cached_name_key(r.raw_name), r.source_ref))


def load_historical_decision_makers(
    source: str | Path | IO[bytes], *, sheet: str | None = None
) -> list[HistoricalDecisionMaker]:
    """Parse *source* into one :class:`HistoricalDecisionMaker` per contact row.

    Keeps every row (duplicate detection is the engine's job); skips only rows with no
    identity at all (no name, LinkedIn, or email). Company name/website travel with each
    record so the engine can resolve the employer to a canonical company.
    """
    wb = openpyxl.load_workbook(source, read_only=True, data_only=True)
    try:
        sheet = sheet or _pick_sheet(wb)
        ws = wb[sheet]
        it = ws.iter_rows(values_only=True)
        header = [clean_text(h).lower() for h in (next(it, None) or ())]
        idx: dict[str, int] = {}
        for i, h in enumerate(header):
            if h not in idx and (h in _DM_COLUMN_MAP or h in ("company name", "company website",
                                                              "website", "linkedin url", "email id")):
                idx[h] = i
        raw_rows = list(it)
    finally:
        wb.close()

    def cell(row, label):
        i = idx.get(label)
        return clean_text(row[i]) if (i is not None and i < len(row)) else ""

    records: list[HistoricalDecisionMaker] = []
    for rownum, row in enumerate(raw_rows, start=2):
        if not any(c is not None and str(c).strip() for c in row):
            continue
        fields = {tgt: cell(row, lbl) for lbl, tgt in _DM_COLUMN_MAP.items() if cell(row, lbl)}
        first, last = fields.get("first_name", ""), fields.get("last_name", "")
        full = clean_text(f"{first} {last}")
        linkedin = cell(row, "linkedin url")
        email = cell(row, "email id")
        if not full and not linkedin and not email:
            continue                                  # no identity at all
        if full:
            fields["full_name"] = full
        records.append(HistoricalDecisionMaker(
            full_name=full or (linkedin or email),
            company_name=cell(row, "company name"),
            company_website=cell(row, "company website") or cell(row, "website"),
            linkedin_url=linkedin, work_email=email,
            fields=fields, source_ref=f"row {rownum}",
        ))
    return records
