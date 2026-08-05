"""Settings env-var binding.

Regression guard for the config bug where the security-relevant fields read only
the bare names (``API_KEY`` / ``RATE_LIMIT_PER_MINUTE``) while every doc and deploy
artifact (``render.yaml``, ``docs/*``) tells operators to set the ``SP_``-prefixed
names. An operator following the docs left ``api_key=""`` — which the service-key
branch in ``backend/security.py`` treats as "no service key" — and silently disabled
the rate limit. Both the
``SP_``-prefixed and bare names must bind. ``_env_file=None`` isolates the tests
from any real ``.env``.
"""
import pytest

from backend.config import Settings

# Every env var these tests touch; cleared before each case so ambient values
# (or a developer's shell) can't mask a real binding failure.
_VARS = (
    "SP_API_KEY", "API_KEY", "sp_api_key", "api_key",
    "SP_RATE_LIMIT_PER_MINUTE", "RATE_LIMIT_PER_MINUTE",
)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for name in _VARS:
        monkeypatch.delenv(name, raising=False)
    yield


def test_sp_api_key_binds(monkeypatch):
    """SP_API_KEY (what render.yaml + docs set) binds to api_key."""
    monkeypatch.setenv("SP_API_KEY", "sp-secret")
    assert Settings(_env_file=None).api_key == "sp-secret"


def test_sp_rate_limit_binds(monkeypatch):
    """SP_RATE_LIMIT_PER_MINUTE binds to rate_limit_per_minute (and coerces to int)."""
    monkeypatch.setenv("SP_RATE_LIMIT_PER_MINUTE", "120")
    assert Settings(_env_file=None).rate_limit_per_minute == 120


def test_bare_names_still_bind(monkeypatch):
    """Bare names keep working — don't break anyone already deployed with them."""
    monkeypatch.setenv("API_KEY", "bare-secret")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "42")
    settings = Settings(_env_file=None)
    assert settings.api_key == "bare-secret"
    assert settings.rate_limit_per_minute == 42


def test_sp_prefix_takes_precedence(monkeypatch):
    """When both are set the SP_-prefixed (canonical) name wins."""
    monkeypatch.setenv("SP_API_KEY", "sp-secret")
    monkeypatch.setenv("API_KEY", "bare-secret")
    assert Settings(_env_file=None).api_key == "sp-secret"


def test_binding_is_case_insensitive(monkeypatch):
    """case_sensitive defaults to False, so a lowercased name still binds."""
    monkeypatch.setenv("sp_api_key", "lower-secret")
    assert Settings(_env_file=None).api_key == "lower-secret"


def test_only_sp_api_key_enables_auth(monkeypatch):
    """The reported bug: setting only SP_API_KEY must NOT leave auth disabled."""
    monkeypatch.setenv("SP_API_KEY", "sp-secret")
    assert Settings(_env_file=None).api_key != ""


def test_init_kwargs_still_work():
    """populate_by_name keeps Settings(api_key=...) usable (other tests rely on it)."""
    settings = Settings(_env_file=None, api_key="kwarg-secret", rate_limit_per_minute=7)
    assert settings.api_key == "kwarg-secret"
    assert settings.rate_limit_per_minute == 7
