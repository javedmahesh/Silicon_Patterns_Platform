"""Apply manual company classification/enrichment from a JSON file.

Updates existing ``companies`` rows in place (matched on ``company_domain``):
sets the Lead-Scoring-relevant fields (company_tier, prospect_type,
compliance_flag) plus light enrichment, and flips a stub to a classified company
(``is_stub=False``, ``validation_status='VALID'``). Idempotent — only changed
fields are touched. This is a manual stand-in for Industry Discovery output; it
does not modify any engine.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from integration.normalizer import normalize_domain
from master_db.models import Company

_DEFAULT = Path(__file__).resolve().parent.parent / "config" / "company_enrichment.json"

# Fields that may be set from the enrichment file.
_ENRICH_FIELDS = (
    "company_tier", "prospect_type", "compliance_flag", "country", "city",
    "headquarters", "industry_category", "sub_category", "industry_type",
    "technology_focus", "founded_year", "company_status",
)


def apply_enrichment(session: Session, path: str | Path = _DEFAULT) -> list[tuple[str, dict]]:
    """Apply enrichment; returns ``[(domain, {field: (old, new), ...}), ...]``."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    results: list[tuple[str, dict]] = []

    for entry in data.get("companies", []):
        domain = normalize_domain(entry.get("domain", ""))
        company = session.get(Company, domain)
        if company is None:
            results.append((domain, {"_error": "company not found"}))
            continue

        changed: dict = {}
        for field_name in _ENRICH_FIELDS:
            new = entry.get(field_name)
            if new in (None, ""):
                continue
            old = getattr(company, field_name)
            if old != new:
                changed[field_name] = (old, new)
                setattr(company, field_name, new)

        if company.is_stub:
            changed["is_stub"] = (True, False)
            company.is_stub = False
        if company.validation_status != "VALID":
            changed["validation_status"] = (company.validation_status, "VALID")
            company.validation_status = "VALID"
        if changed and "manual_enrichment" not in (company.source or ""):
            company.source = ",".join(x for x in (company.source, "manual_enrichment") if x)

        results.append((domain, changed))

    session.commit()
    return results
