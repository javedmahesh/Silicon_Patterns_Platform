"""Role embeddings — a reusable, cached semantic feature extractor for DM titles.

A lightweight open-source model (all-MiniLM-L6-v2 via sentence-transformers) is used
when installed; otherwise a deterministic zero-dependency hash embedding keeps the
whole pipeline working (and tests fast + deterministic). Either way results are cached
in ``role_embeddings`` keyed by a hash of the normalized title, so an unchanged title
is never re-embedded.

Embeddings AUGMENT the existing structured role data (seniority / functional_area /
current_title) — they never replace it.
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from master_db.models import RoleEmbedding

logger = logging.getLogger("ml.embeddings")

_WORD = re.compile(r"[a-z0-9+]+")


def normalize_title(title: str) -> str:
    """Lowercase + collapse to alnum tokens so equivalent titles share a cache key."""
    return " ".join(_WORD.findall((title or "").lower()))


def title_hash(norm_title: str) -> str:
    return hashlib.sha1(norm_title.encode("utf-8")).hexdigest()[:32]


class EmbeddingProvider:
    """Turns a title into a fixed-dim unit vector. Backend is pluggable + lazy."""

    def __init__(self, backend: str = "hash", model_name: str = "all-MiniLM-L6-v2",
                 dim: int = 384) -> None:
        self.backend = backend
        self.model_name = model_name
        self.dim = dim
        self._model = None  # lazily loaded sentence-transformers model

    @property
    def cache_key(self) -> str:
        """Distinguishes cached vectors from different backends/models."""
        return self.model_name if self.backend == "sentence-transformers" else f"hash-{self.dim}"

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # heavy, optional

            self._model = SentenceTransformer(self.model_name)
            self.dim = self._model.get_sentence_embedding_dimension()
        return self._model

    def embed_one(self, title: str) -> list[float]:
        norm = normalize_title(title)
        if self.backend == "sentence-transformers":
            try:
                vec = self._load_model().encode(norm or " ", normalize_embeddings=True)
                return [float(x) for x in vec]
            except Exception as exc:  # missing package / load error -> deterministic fallback
                logger.warning("embedding model unavailable (%s); using hash fallback", exc)
                self.backend = "hash"
        return _hash_embed(norm, self.dim)


def _hash_embed(norm_title: str, dim: int) -> list[float]:
    """Deterministic bag-of-tokens hash embedding, L2-normalized. Stable across
    processes (hashlib, not Python's salted hash) so features are reproducible."""
    vec = [0.0] * dim
    tokens = norm_title.split()
    if not tokens:
        return vec
    for tok in tokens:
        h = int(hashlib.sha1(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [round(x / norm, 6) for x in vec]
    return vec


@lru_cache(maxsize=1)
def _provider_from(backend: str, model_name: str, dim: int) -> EmbeddingProvider:
    return EmbeddingProvider(backend=backend, model_name=model_name, dim=dim)


def get_provider(settings) -> EmbeddingProvider:
    return _provider_from(settings.ml_embedding_backend, settings.ml_embedding_model,
                          settings.ml_embedding_dim)


def embed_titles(session: Session, titles: list[str], settings) -> dict[str, list[float]]:
    """Embed *titles* (deduped) with a read-through cache. Only titles not already in
    ``role_embeddings`` for this model are computed; the rest are reused. Returns a map
    keyed by the ORIGINAL title string. Batch-friendly."""
    provider = get_provider(settings)
    model = provider.cache_key
    # normalize + dedupe (unchanged titles collapse to one embedding)
    norm_by_title = {t: normalize_title(t) for t in titles}
    hashes = {title_hash(n): n for n in set(norm_by_title.values())}

    cached: dict[str, list[float]] = {}
    if hashes:
        rows = session.scalars(
            select(RoleEmbedding).where(
                RoleEmbedding.model_name == model,
                RoleEmbedding.title_hash.in_(list(hashes)),
            )
        ).all()
        cached = {r.title_hash: r.vector for r in rows}

    # compute + persist the misses
    missing = {h: n for h, n in hashes.items() if h not in cached}
    for h, norm in missing.items():
        vec = provider.embed_one(norm)
        session.add(RoleEmbedding(title_hash=h, title_norm=norm[:512], model_name=model,
                                  dim=len(vec), vector=vec))
        cached[h] = vec
    if missing:
        session.flush()

    return {t: cached[title_hash(n)] for t, n in norm_by_title.items()}


def mean_vector(vectors: list[list[float]], dim: int) -> list[float]:
    """Mean of embedding vectors (a company's aggregate role embedding). Zero if empty."""
    vectors = [v for v in vectors if v]
    if not vectors:
        return [0.0] * dim
    n = len(vectors)
    d = len(vectors[0])
    return [round(sum(v[i] for v in vectors) / n, 6) for i in range(d)]


def demo() -> None:
    """Self-check: deterministic + unit-norm + same title -> same vector. Run: python -m ml.embeddings"""
    a = _hash_embed(normalize_title("VP  Engineering"), 384)
    b = _hash_embed(normalize_title("vp engineering"), 384)
    assert a == b, "normalization should collapse case/whitespace-equivalent titles"
    assert abs(math.sqrt(sum(x * x for x in a)) - 1.0) < 1e-6, "should be unit norm"
    c = _hash_embed(normalize_title("Chief Financial Officer"), 384)
    assert a != c
    print(f"OK — deterministic hash embedding dim={len(a)}, unit-norm, title-normalized")


if __name__ == "__main__":  # pragma: no cover
    demo()
