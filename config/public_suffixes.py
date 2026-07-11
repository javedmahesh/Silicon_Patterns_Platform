"""Offline public-suffix table for domain normalization.

The four engines each ship their own domain extractor and none is public-suffix
aware, so ``careers.acme.co.uk`` reduces inconsistently (``co.uk`` vs ``acme.co.uk``).
This curated set of multi-label suffixes lets :mod:`integration.normalizer` pick
the correct *registrable* domain with **no network call and no third-party
dependency** — important for P0, which must run fully offline.

This is a pragmatic subset covering the suffixes that actually appear in
semiconductor-industry company domains. For production scale we can swap in the
full Public Suffix List (``publicsuffix2`` / ``tldextract`` with an offline PSL
snapshot) behind the same :func:`integration.normalizer.registrable_domain` API.
"""
from __future__ import annotations

# Second-level suffixes where the registrable domain is the *last three* labels
# (e.g. "acme.co.uk" not "co.uk"). Lower-cased, no leading dot.
MULTI_LABEL_SUFFIXES: frozenset[str] = frozenset(
    {
        # United Kingdom
        "co.uk", "org.uk", "ltd.uk", "plc.uk", "me.uk", "ac.uk", "gov.uk",
        # Ireland / Europe
        "co.at", "or.at", "co.hu", "com.es", "com.pl", "com.ua", "com.tr",
        # India
        "co.in", "net.in", "org.in", "firm.in", "gen.in", "ind.in",
        # China / Hong Kong / Taiwan / Macau
        "com.cn", "net.cn", "org.cn", "com.hk", "com.tw", "com.mo",
        # Japan / Korea
        "co.jp", "or.jp", "ne.jp", "ac.jp", "co.kr", "ne.kr", "or.kr",
        # SE Asia / Oceania
        "com.sg", "com.my", "com.ph", "com.vn", "co.id", "co.th", "com.au",
        "net.au", "org.au", "co.nz", "net.nz",
        # Middle East / Israel
        "co.il", "org.il", "com.sa", "com.qa", "com.kw", "com.bh",
        # Americas (non-US)
        "com.br", "com.mx", "com.ar", "com.co", "com.pe", "com.uy",
        # Africa
        "co.za", "org.za", "com.ng", "co.ke",
    }
)
