"""Reusable company alias system.

The platform already persists aliases in :class:`master_db.models.CompanyAlias`
and resolves them in :class:`integration.resolver.CompanyResolver` (used by Industry
Discovery, the News Collection Engine, Career Intelligence and Decision Maker
Intelligence). This module adds the missing piece: a **curated, deterministic seed**
of well-known equivalences so that "AMD" and "Advanced Micro Devices" collapse to one
company *before* anyone has manually taught the alias — and it does so in a way every
engine (and historical sync) can reuse.

Two uses, one source of truth (:data:`WELL_KNOWN_ALIASES`):

* **In-memory (read-only)** — :func:`alias_name_key_map` returns ``{name_key(alias):
  name_key(canonical)}``. The sync preview uses it to canonicalize a name *without
  writing anything*, so aliases work even against a company not yet in the platform.
* **Persisted (opt-in)** — :func:`seed_persisted_aliases` writes the curated aliases
  as ``CompanyAlias`` rows for whichever canonical companies exist, via the existing
  ``CompanyResolver.register_alias`` (idempotent). Not called during a Phase-2 preview
  (that stays write-free); exposed for a one-off ``sync seed-aliases`` and for the
  four engines to share.
"""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy.orm import Session

from integration.normalizer import name_key
from integration.resolver import CompanyResolver

# canonical display name -> the other spellings that mean the same company.
# Keep this semiconductor/EDA-focused and conservative: only truly unambiguous
# equivalences (a rename, a legal long-form, or a universally-known abbreviation).
WELL_KNOWN_ALIASES: dict[str, tuple[str, ...]] = {
    "Advanced Micro Devices": ("AMD",),
    "NVIDIA Corporation": ("NVIDIA", "Nvidia"),
    "Intel Corporation": ("Intel",),
    "Cadence Design Systems": ("Cadence",),
    "Synopsys": ("Synopsys Inc",),
    "Qualcomm": ("Qualcomm Technologies", "Qualcomm Incorporated"),
    "Taiwan Semiconductor Manufacturing Company": ("TSMC",),
    "Texas Instruments": ("TI",),
    "Micron Technology": ("Micron",),
    "Broadcom": ("Broadcom Inc",),
    "Marvell Technology": ("Marvell",),
    "Analog Devices": ("ADI",),
    "STMicroelectronics": ("ST Micro", "STMicro"),
    "NXP Semiconductors": ("NXP",),
    "Infineon Technologies": ("Infineon",),
    "GlobalFoundries": ("Global Foundries", "GF"),
    "Arm Holdings": ("ARM", "Arm"),
    "Renesas Electronics": ("Renesas",),
    "Microchip Technology": ("Microchip",),
    "Western Digital": ("WD", "WDC"),
}


@lru_cache(maxsize=1)
def alias_name_key_map() -> dict[str, str]:
    """``{name_key(alias): name_key(canonical)}`` for every curated equivalence.

    Cached (the seed is static). The canonical maps to itself too, so a lookup is a
    single ``.get(nk, nk)`` idempotent canonicalization.
    """
    out: dict[str, str] = {}
    for canonical, aliases in WELL_KNOWN_ALIASES.items():
        c_key = name_key(canonical)
        if not c_key:
            continue
        out[c_key] = c_key
        for a in aliases:
            a_key = name_key(a)
            if a_key:
                out[a_key] = c_key
    return out


def canonical_name_key(raw_name: str | None) -> str:
    """The canonical ``name_key`` for *raw_name*, applying the well-known alias map.

    ``canonical_name_key("AMD") == name_key("Advanced Micro Devices")``. Falls back to
    the plain key when the name is not a known alias.
    """
    nk = name_key(raw_name)
    return alias_name_key_map().get(nk, nk)


def seed_persisted_aliases(session: Session, *, source: str = "well_known_seed") -> int:
    """Persist the curated aliases as ``CompanyAlias`` rows for canonical companies
    that exist in the platform. Idempotent. Returns the number of aliases registered.

    Opt-in only (writes to the DB) — reused by the four engines / a maintenance
    command, never by the read-only sync preview. Resolution goes through the
    existing ``CompanyResolver.register_alias`` so behavior matches the engines.
    """
    from master_db.models import Company
    from sqlalchemy import select

    resolver = CompanyResolver(session)
    # index existing companies by canonical name_key so we can find a domain to attach to
    by_key: dict[str, str] = {}
    for domain, nk in session.execute(
        select(Company.company_domain, Company.name_key).where(Company.name_key != "")
    ).all():
        by_key.setdefault(nk, domain)

    registered = 0
    for canonical, aliases in WELL_KNOWN_ALIASES.items():
        domain = by_key.get(name_key(canonical))
        if not domain:
            continue  # canonical company not in the platform yet — nothing to attach to
        for a in aliases:
            if resolver.register_alias(a, domain, source=source, confidence=0.99):
                registered += 1
    return registered
