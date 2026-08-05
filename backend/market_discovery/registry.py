"""Source registry — the only thing the scheduler and the engine talk to.

The scheduler asks the registry for "the sources that should run now" and never
learns which providers exist. Adding Firecrawl, Wellfound, Dealroom or a government
registry means registering one class and naming it in configuration; nothing in the
scheduler, pipeline or engine changes.

Enablement is deliberately explicit rather than "everything registered runs": these
sources cost money and hit rate limits, so a source must be *named* in
``SP_DISCOVERY_SOURCES`` (or the ``enabled`` argument) before it will run. The one
exception is the wildcard ``*``, for development.
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Iterable

from backend.market_discovery.base_source import DiscoverySource
from backend.market_discovery.schemas import SourceCapabilities, SourceHealth, SourceStatus

logger = logging.getLogger("market_discovery.registry")

_SOURCES_PACKAGE = "backend.market_discovery.sources"


class SourceRegistry:
    """Holds the known discovery sources and which of them are switched on."""

    def __init__(self) -> None:
        self._sources: dict[str, DiscoverySource] = {}

    # ------------------------------------------------------------- registration
    def register(self, source: DiscoverySource, *, replace: bool = False) -> None:
        name = (source.name or "").strip().lower()
        if not name:
            raise ValueError(f"{type(source).__name__} must define a non-empty `name`")
        if name in self._sources and not replace:
            raise ValueError(f"discovery source {name!r} is already registered")
        self._sources[name] = source
        logger.debug("[discovery] registered source %s", name)

    def unregister(self, name: str) -> None:
        self._sources.pop((name or "").strip().lower(), None)

    def clear(self) -> None:
        """Drop every registration. Used by tests; not part of the runtime path."""
        self._sources.clear()

    def autodiscover(self, package: str = _SOURCES_PACKAGE) -> list[str]:
        """Import every module under ``sources/`` so it can self-register.

        Import side effects are the registration mechanism (same as the news adapters
        and the notification providers). A module that fails to import is logged and
        skipped — one broken connector must not stop the engine from starting.

        A connector's ``register(MySource())`` call targets the process-wide registry,
        and Python caches the import — so on a second call, or on a registry that is
        not the global one, nothing new would be imported and this instance would come
        up empty. Adopting the global's entries afterwards makes ``autodiscover()``
        idempotent and makes a fresh registry (a test, a second engine instance) behave
        identically to the first.
        """
        loaded: list[str] = []
        try:
            pkg = importlib.import_module(package)
        except ModuleNotFoundError:
            logger.debug("[discovery] no sources package at %s", package)
            return loaded
        for mod in pkgutil.iter_modules(pkg.__path__):
            if mod.name.startswith("_"):
                continue
            full = f"{package}.{mod.name}"
            try:
                importlib.import_module(full)
                loaded.append(full)
            except Exception:      # noqa: BLE001
                logger.error("[discovery] could not import source module %s (skipped)",
                             full, exc_info=True)
        self._adopt_globally_registered()
        return loaded

    def _adopt_globally_registered(self) -> None:
        """Copy anything registered on the process-wide registry into this one."""
        if self is registry:
            return
        for name, source in registry._sources.items():
            self._sources.setdefault(name, source)

    # ------------------------------------------------------------- lookup
    def get(self, name: str) -> DiscoverySource | None:
        return self._sources.get((name or "").strip().lower())

    def names(self) -> list[str]:
        return sorted(self._sources)

    def all(self) -> list[DiscoverySource]:
        return [self._sources[n] for n in self.names()]

    def __len__(self) -> int:
        return len(self._sources)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name.strip().lower() in self._sources

    # ------------------------------------------------------------- selection
    def enabled_sources(self, enabled: Iterable[str] | None) -> list[DiscoverySource]:
        """The sources that should run, in deterministic (name) order.

        A configured name that isn't registered is a warning, not an error — a deploy
        naming a connector that hasn't shipped yet degrades to running the rest.
        """
        if enabled is None:
            return []
        wanted = [n.strip().lower() for n in enabled if n and n.strip()]
        if "*" in wanted:
            return self.all()
        out: list[DiscoverySource] = []
        for name in sorted(dict.fromkeys(wanted)):
            source = self._sources.get(name)
            if source is None:
                logger.warning("[discovery] configured source %r is not registered (skipped)", name)
                continue
            out.append(source)
        return out

    def runnable_sources(self, enabled: Iterable[str] | None) -> tuple[list[DiscoverySource], list[SourceHealth]]:
        """Enabled sources that also pass :meth:`validate`, plus the ones that didn't.

        Validating up front means a missing credential shows as a skipped source with a
        reason, instead of an exception in the middle of a run.
        """
        runnable: list[DiscoverySource] = []
        skipped: list[SourceHealth] = []
        for source in self.enabled_sources(enabled):
            try:
                ok, reason = source.validate()
            except Exception as exc:      # noqa: BLE001
                ok, reason = False, f"validate() raised: {exc}"
                logger.error("[discovery] %s.validate() raised", source.name, exc_info=True)
            if ok:
                runnable.append(source)
            else:
                logger.warning("[discovery] source %s is not runnable: %s", source.name, reason)
                skipped.append(SourceHealth(source.name, SourceStatus.UNAVAILABLE, reason))
        return runnable, skipped

    # ------------------------------------------------------------- introspection
    def capabilities(self) -> dict[str, SourceCapabilities]:
        out: dict[str, SourceCapabilities] = {}
        for source in self.all():
            try:
                out[source.name] = source.capabilities()
            except Exception:      # noqa: BLE001
                logger.error("[discovery] %s.capabilities() raised", source.name, exc_info=True)
        return out

    def health(self, enabled: Iterable[str] | None = None) -> dict[str, SourceHealth]:
        """Health of every registered source; those not enabled report DISABLED."""
        active = {s.name for s in self.enabled_sources(enabled)} if enabled is not None else None
        out: dict[str, SourceHealth] = {}
        for source in self.all():
            if active is not None and source.name not in active:
                out[source.name] = SourceHealth(source.name, SourceStatus.DISABLED,
                                                "not enabled by configuration")
                continue
            try:
                out[source.name] = source.health()
            except Exception as exc:      # noqa: BLE001 - health must never raise
                out[source.name] = SourceHealth(source.name, SourceStatus.UNAVAILABLE,
                                                f"health() raised: {exc}")
                logger.error("[discovery] %s.health() raised", source.name, exc_info=True)
        return out


#: Process-wide registry. Sources self-register into this on import.
registry = SourceRegistry()


def register(source: DiscoverySource, *, replace: bool = False) -> None:
    """Module-level convenience: ``register(MySource())`` at the bottom of a source."""
    registry.register(source, replace=replace)
