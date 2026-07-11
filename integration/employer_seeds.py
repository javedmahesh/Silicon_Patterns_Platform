"""Seed major employer companies + aliases from ``config/employer_seeds.json``.

Created as part of P2 Option B: the live LinkedIn import surfaced 101 distinct
employers (Intel, NVIDIA, Cadence, …) that weren't in the company universe yet,
so every decision-maker landed in the review queue. Seeding these companies and
their name variants lets the alias layer resolve the bulk of them.

Companies are created as real rows (``validation_status='VALID'``,
``source='employer_seed'``, ``is_stub=False``) — they are known real companies,
not resolver stubs. Idempotent: re-running updates aliases without duplicating.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from config.enums import is_excluded_prospect
from integration.normalizer import canonical_company_id, name_key, normalize_domain
from integration.resolver import CompanyResolver
from master_db.models import Company

_DEFAULT_SEED = Path(__file__).resolve().parent.parent / "config" / "employer_seeds.json"


def seed_employers(session: Session, path: str | Path = _DEFAULT_SEED) -> tuple[int, list[tuple[str, str]]]:
    """Create seeded companies + register every alias spelling.

    Returns ``(companies_created, mappings)`` where *mappings* is the list of
    ``(alias_spelling, company_domain)`` pairs processed (for reporting).
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    resolver = CompanyResolver(session)
    companies_created = 0
    mappings: list[tuple[str, str]] = []

    for entry in data.get("companies", []):
        domain = normalize_domain(entry.get("domain", ""))
        name = entry.get("name", "").strip()
        if not domain or not name:
            continue
        if is_excluded_prospect(entry.get("prospect_type")):
            continue  # competitor (service provider) — never seed it or its aliases

        if session.get(Company, domain) is None:
            session.add(
                Company(
                    company_domain=domain,
                    canonical_company_id=canonical_company_id(domain, name),
                    company_name=name,
                    name_key=name_key(name),
                    prospect_type=entry.get("prospect_type", "PRODUCT_COMPANY"),
                    company_tier=entry.get("tier", "UNKNOWN"),
                    compliance_flag="APPROVED",
                    validation_status="VALID",
                    source="employer_seed",
                    source_type="manual",
                    is_stub=False,
                )
            )
            session.flush()
            companies_created += 1

        for spelling in [name, *entry.get("aliases", [])]:
            resolver.register_alias(spelling, domain, source="employer_seed")
            mappings.append((spelling, domain))

    session.commit()
    return companies_created, mappings
