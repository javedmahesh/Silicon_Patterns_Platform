"""Provider registry — factory + registration, no circular imports."""
from __future__ import annotations

from .base import EmailProvider
from .mock import MockEmailProvider

_REGISTRY: dict[str, EmailProvider] = {
    "mock": MockEmailProvider(),
}


def register_provider(provider: EmailProvider) -> None:
    _REGISTRY[provider.provider_type] = provider


def get_provider(provider_type: str) -> EmailProvider | None:
    return _REGISTRY.get(provider_type)


def get_provider_for_user(provider_type: str, config_json: str) -> EmailProvider:
    """Return a configured provider for a specific user's credentials.

    For mock (and other stateless providers) returns the registry singleton.
    For gmail (and any user-scoped provider) creates a fresh instance bound
    to the user's config_json (OAuth tokens).
    """
    if provider_type == "gmail":
        from .gmail import GmailProvider
        return GmailProvider(config_json=config_json)
    return _REGISTRY.get(provider_type) or MockEmailProvider()


def list_provider_types() -> list[str]:
    return sorted(_REGISTRY.keys())
