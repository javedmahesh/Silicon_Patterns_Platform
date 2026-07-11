"""Email provider abstraction layer — registry + ABC + concrete implementations."""
from .base import (
    AttachmentData,
    DraftResult,
    EmailProvider,
    ProviderCapabilities,
    RawMessage,
    SendResult,
    SyncResult,
)
from .registry import get_provider, get_provider_for_user, list_provider_types, register_provider

__all__ = [
    "AttachmentData",
    "DraftResult",
    "EmailProvider",
    "ProviderCapabilities",
    "RawMessage",
    "SendResult",
    "SyncResult",
    "get_provider",
    "get_provider_for_user",
    "list_provider_types",
    "register_provider",
]
