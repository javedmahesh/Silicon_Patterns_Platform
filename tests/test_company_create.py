"""Manual company creation (POST /companies) — normalization, dedup, RBAC."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company


@pytest.fixture()
def client(tmp_path):
    db = tmp_path / "cc.db"
    app = create_app(Settings(database_url=f"sqlite:///{db.as_posix()}", log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        yield app, c


def test_create_company_normalizes_and_derives_keys(client):
    app, c = client
    # A messy URL is normalized to the registrable domain + join keys are derived.
    r = c.post("/companies", json={"company_name": "Acme Semiconductor, Inc.",
                                    "company_domain": "https://www.Acme.com/careers", "country": "USA"},
               headers={"X-Dev-Role": "manager"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["company_domain"] == "acme.com"
    assert body["company_name"] == "Acme Semiconductor, Inc."
    assert body["country"] == "USA"

    with app.state.db.sessionmaker() as s:
        row = s.get(Company, "acme.com")
        assert row is not None
        assert row.name_key == "acme"            # legal/structural suffixes stripped
        assert row.canonical_company_id == "ACME"
        assert row.source == "manual" and row.is_stub is False and row.validation_status == "VALID"

    # It now appears in the universe listing.
    listed = c.get("/companies", params={"q": "Acme"}).json()
    assert any(x["company_domain"] == "acme.com" for x in listed["items"])


def test_create_company_rejects_duplicate(client):
    _, c = client
    body = {"company_name": "Foo", "company_domain": "foo.com"}
    assert c.post("/companies", json=body, headers={"X-Dev-Role": "manager"}).status_code == 201
    dup = c.post("/companies", json=body, headers={"X-Dev-Role": "manager"})
    assert dup.status_code == 409
    assert dup.json()["detail"]["code"] == "company_exists"


def test_create_company_rejects_invalid_domain(client):
    _, c = client
    r = c.post("/companies", json={"company_name": "NoDomain", "company_domain": "not a domain"},
               headers={"X-Dev-Role": "manager"})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "invalid_domain"


def test_create_company_requires_manager(client):
    _, c = client
    body = {"company_name": "Members Cant", "company_domain": "member.com"}
    assert c.post("/companies", json=body, headers={"X-Dev-Role": "member"}).status_code == 403
    # ...and a manager can.
    assert c.post("/companies", json=body, headers={"X-Dev-Role": "manager"}).status_code == 201
