"""Seed the ``company_aliases`` table from ``config/company_aliases.seed.json``.

Each seed entry is routed through :class:`~integration.resolver.CompanyResolver`,
so seeding reuses exactly the same code path as live ingestion: a low-confidence
company stub is created for the domain (if absent) and the alias is recorded.
This keeps the alias table and the companies table consistent and avoids a
separate, drift-prone seeding path.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from integration.resolver import CompanyResolver

_DEFAULT_SEED = Path(__file__).resolve().parent.parent / "config" / "company_aliases.seed.json"


def load_alias_seeds(session: Session, path: str | Path = _DEFAULT_SEED) -> int:
    """Load alias seeds into *session*'s database. Returns the number of aliases
    processed. Idempotent: re-running does not duplicate companies or aliases."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    resolver = CompanyResolver(session)
    count = 0
    for entry in data.get("aliases", []):
        alias = entry.get("alias", "").strip()
        domain = entry.get("company_domain", "").strip()
        if not alias or not domain:
            continue
        # resolve() creates the stub company for the domain if needed, then we
        # attach the alias spelling to it.
        resolver.resolve(domain=domain, name=alias, source_engine="seed")
        resolver.register_alias(alias, domain, source="seed")
        count += 1
    session.commit()
    return count
