"""Unit tests for the canonical normalizer — the join-key reconciliation logic."""
import pytest

from integration.normalizer import (
    canonical_company_id,
    domain_from_email,
    is_valid_domain,
    name_key,
    normalize_domain,
    registrable_domain,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("https://www.Groq.com/careers?utm=x", "groq.com"),
        ("http://groq.com", "groq.com"),
        ("GROQ.COM", "groq.com"),
        ("www.groq.com", "groq.com"),
        ("groq.com/careers", "groq.com"),
        ("careers.groq.com", "groq.com"),
        ("//etched.ai", "etched.ai"),
        ("tenstorrent.com:443", "tenstorrent.com"),
        ("recruiting@groq.com", "groq.com"),
        ("", ""),
        (None, ""),
        ("not a domain", ""),
        ("localhost", ""),
    ],
)
def test_normalize_domain(raw, expected):
    assert normalize_domain(raw) == expected


@pytest.mark.parametrize(
    "host, expected",
    [
        ("acme.co.uk", "acme.co.uk"),
        ("careers.acme.co.uk", "acme.co.uk"),
        ("foo.bar.com.cn", "bar.com.cn"),
        ("chip.co.in", "chip.co.in"),
        ("simple.com", "simple.com"),
        ("a.b.c.io", "c.io"),
    ],
)
def test_registrable_domain_multilabel(host, expected):
    assert registrable_domain(host) == expected


def test_multilabel_via_normalize():
    assert normalize_domain("https://jobs.acme.co.uk/x") == "acme.co.uk"


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Groq", "groq"),
        ("Groq, Inc.", "groq"),
        ("GROQ", "groq"),
        ("Tenstorrent Inc", "tenstorrent"),
        ("Acme Semiconductors", "acme"),
        ("Foo Technologies Ltd", "foo"),
        ("", ""),
    ],
)
def test_name_key(name, expected):
    assert name_key(name) == expected


@pytest.mark.parametrize(
    "domain, name, expected",
    [
        ("groq.com", "Groq Inc.", "GROQ"),
        ("groq.com", "", "GROQ"),
        ("www.etched.ai", "Etched", "ETCHED"),
        ("", "Groq Inc.", "GROQ"),      # fallback to name when no domain
        ("", "", ""),
    ],
)
def test_canonical_company_id(domain, name, expected):
    assert canonical_company_id(domain, name) == expected


def test_canonical_id_consistent_across_name_spellings():
    # The whole point: every spelling resolves to the same id via the domain.
    ids = {canonical_company_id("groq.com", n) for n in ("Groq", "Groq Inc.", "GROQ")}
    assert ids == {"GROQ"}


def test_domain_from_email():
    assert domain_from_email("jane.doe@etched.ai") == "etched.ai"
    assert domain_from_email("nope") == ""


def test_is_valid_domain():
    assert is_valid_domain("groq.com")
    assert not is_valid_domain("groq")
    assert not is_valid_domain("")
