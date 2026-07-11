"""Unit tests for CompanyResolver — exercises the stub + review-queue policy
against a local in-memory SQLite database (no Supabase)."""
import pytest
from sqlalchemy import func, select

from integration.resolver import CompanyResolver
from integration.seeds import load_alias_seeds
from master_db.local import make_session_factory
from master_db.models import Company, CompanyAlias, ResolutionReviewQueue


@pytest.fixture()
def session():
    Session = make_session_factory(":memory:")
    with Session() as s:
        yield s


def _add_company(session, domain, name, **kw):
    from integration.normalizer import canonical_company_id, name_key

    c = Company(
        company_domain=domain,
        canonical_company_id=canonical_company_id(domain, name),
        company_name=name,
        name_key=name_key(name),
        validation_status="VALID",
        **kw,
    )
    session.add(c)
    session.flush()
    return c


def test_exact_domain_match(session):
    _add_company(session, "groq.com", "Groq")
    r = CompanyResolver(session).resolve(domain="https://www.groq.com/careers", name="Groq Inc.")
    assert r.match_type == "EXACT_DOMAIN"
    assert r.company_domain == "groq.com"
    assert r.confidence == 1.0
    assert not r.created and not r.review_queued


def test_new_domain_creates_stub_and_queues_review(session):
    r = CompanyResolver(session).resolve(
        domain="etched.ai", name="Etched", source_engine="blog", source_ref="OPP-1"
    )
    assert r.match_type == "NEW_STUB"
    assert r.company_domain == "etched.ai"
    assert r.created and r.review_queued

    stub = session.get(Company, "etched.ai")
    assert stub is not None and stub.is_stub and stub.validation_status == "STUB"
    # An alias was recorded for the stub, and a review item was queued.
    assert session.scalar(select(func.count()).select_from(CompanyAlias)) == 1
    q = session.scalar(select(ResolutionReviewQueue))
    assert q.match_type == "NEW_STUB" and q.source_engine == "blog"


def test_create_stub_disabled_queues_unresolved(session):
    r = CompanyResolver(session).resolve(domain="etched.ai", create_stub=False)
    assert r.match_type == "UNRESOLVED"
    assert r.company_domain is None
    assert session.get(Company, "etched.ai") is None
    assert session.scalar(select(func.count()).select_from(ResolutionReviewQueue)) == 1


def test_alias_resolves_name_only(session):
    _add_company(session, "groq.com", "Groq")
    resolver = CompanyResolver(session)
    resolver.register_alias("Groq Incorporated", "groq.com", source="test")
    r = resolver.resolve(name="Groq Incorporated")
    assert r.match_type == "ALIAS"
    assert r.company_domain == "groq.com"


def test_fuzzy_name_match(session):
    _add_company(session, "tenstorrent.com", "Tenstorrent")
    # Slight misspelling, no domain -> fuzzy match above threshold.
    r = CompanyResolver(session, fuzzy_threshold=0.85).resolve(name="Tenstorent")
    assert r.match_type == "FUZZY_NAME"
    assert r.company_domain == "tenstorrent.com"
    # The new spelling is learned as an alias for next time.
    assert session.scalar(select(func.count()).select_from(CompanyAlias)) == 1


def test_name_only_no_match_goes_to_review(session):
    r = CompanyResolver(session).resolve(
        name="Totally Unknown Co", source_engine="linkedin", source_ref="https://lnkd.in/x"
    )
    assert r.match_type == "UNRESOLVED"
    assert r.company_domain is None and r.review_queued
    q = session.scalar(select(ResolutionReviewQueue))
    assert q.source_engine == "linkedin"


def test_empty_input_does_not_clutter_queue(session):
    r = CompanyResolver(session).resolve(name="   ")
    assert r.match_type == "UNRESOLVED" and not r.review_queued
    assert session.scalar(select(func.count()).select_from(ResolutionReviewQueue)) == 0


def test_resolve_is_idempotent_on_repeat(session):
    resolver = CompanyResolver(session)
    first = resolver.resolve(domain="etched.ai", name="Etched", source_engine="blog")
    second = resolver.resolve(domain="etched.ai", name="Etched", source_engine="blog")
    assert first.created and not second.created          # stub only created once
    assert second.match_type == "EXACT_DOMAIN"
    assert session.scalar(select(func.count()).select_from(Company)) == 1


def test_alias_seed_loader(session):
    n = load_alias_seeds(session)
    assert n >= 6
    # groq.com stub exists and its three spellings share one name_key alias row.
    assert session.get(Company, "groq.com") is not None
    groq_aliases = session.scalars(
        select(CompanyAlias).where(CompanyAlias.company_domain == "groq.com")
    ).all()
    assert {a.name_key for a in groq_aliases} == {"groq"}
