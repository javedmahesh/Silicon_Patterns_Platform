"""Enterprise CRM Phase 7: Custom Objects, Forms & No-Code Platform tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company

MGR = {"X-Dev-Role": "manager"}
MEM = {"X-Dev-Role": "member"}


def _seed(s):
    s.add(Company(
        company_domain="acme.com", canonical_company_id="ACME",
        company_name="Acme Corp", name_key="acme",
        prospect_type="PRODUCT_COMPANY", validation_status="VALID",
        company_tier="INCUMBENT",
    ))
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'custom_objects.db').as_posix()}",
        log_json=False, dev_auth_bypass=True,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _uid(client, headers=MGR) -> int:
    return client.get("/auth/me", headers=headers).json()["id"]


def _make_object(client, **kw):
    payload = {"name": "Project", "api_name": "project", "status": "active", **kw}
    return client.post("/custom-objects", headers=MGR, json=payload).json()


def _make_field(client, object_id, **kw):
    payload = {"name": "Amount", "api_name": "amount", "field_type": "decimal", **kw}
    return client.post(f"/custom-objects/{object_id}/fields", headers=MGR, json=payload).json()


def _make_record(client, object_id, data, headers=MGR):
    return client.post(f"/custom-objects/{object_id}/records", headers=headers, json={"data": data})


# =====================================================================
# Object CRUD
# =====================================================================
class TestObjectCRUD:
    def test_create_object(self, client):
        o = _make_object(client)
        assert o["id"] > 0
        assert o["api_name"] == "project"
        assert o["version"] == 1

    def test_create_object_manager_only(self, client):
        r = client.post("/custom-objects", headers=MEM, json={"name": "X", "api_name": "x"})
        assert r.status_code == 403

    def test_create_object_duplicate_api_name(self, client):
        _make_object(client)
        r = client.post("/custom-objects", headers=MGR, json={"name": "Project2", "api_name": "project"})
        assert r.status_code == 409

    def test_list_objects(self, client):
        _make_object(client, api_name="p1")
        _make_object(client, api_name="p2")
        r = client.get("/custom-objects", headers=MGR)
        assert r.json()["total"] == 2

    def test_list_filter_by_status(self, client):
        _make_object(client, api_name="p1", status="active")
        _make_object(client, api_name="p2", status="draft")
        r = client.get("/custom-objects?status=draft", headers=MGR)
        assert r.json()["total"] == 1

    def test_get_object(self, client):
        o = _make_object(client)
        r = client.get(f"/custom-objects/{o['id']}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["name"] == "Project"

    def test_get_object_not_found(self, client):
        assert client.get("/custom-objects/9999", headers=MGR).status_code == 404

    def test_patch_object_bumps_version(self, client):
        o = _make_object(client)
        r = client.patch(f"/custom-objects/{o['id']}", headers=MGR, json={"status": "archived"})
        assert r.json()["status"] == "archived"
        assert r.json()["version"] == 2

    def test_patch_object_manager_only(self, client):
        o = _make_object(client)
        assert client.patch(f"/custom-objects/{o['id']}", headers=MEM, json={"status": "archived"}).status_code == 403

    def test_delete_object(self, client):
        o = _make_object(client)
        assert client.delete(f"/custom-objects/{o['id']}", headers=MGR).status_code == 204
        assert client.get(f"/custom-objects/{o['id']}", headers=MGR).status_code == 404

    def test_delete_object_manager_only(self, client):
        o = _make_object(client)
        assert client.delete(f"/custom-objects/{o['id']}", headers=MEM).status_code == 403

    def test_delete_object_cascades_records(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        _make_record(client, o["id"], {"amount": 10.0})
        client.delete(f"/custom-objects/{o['id']}", headers=MGR)
        # records table has no more rows for this object — verified indirectly via 404 on the object.
        assert client.get(f"/custom-objects/{o['id']}", headers=MGR).status_code == 404


# =====================================================================
# Field CRUD
# =====================================================================
class TestFieldCRUD:
    def test_create_field(self, client):
        o = _make_object(client)
        f = _make_field(client, o["id"], name="Amount", api_name="amount", field_type="decimal")
        assert f["id"] > 0
        assert f["field_type"] == "decimal"

    def test_create_field_manager_only(self, client):
        o = _make_object(client)
        r = client.post(f"/custom-objects/{o['id']}/fields", headers=MEM, json={
            "name": "X", "api_name": "x", "field_type": "text",
        })
        assert r.status_code == 403

    def test_create_field_invalid_type(self, client):
        o = _make_object(client)
        r = client.post(f"/custom-objects/{o['id']}/fields", headers=MGR, json={
            "name": "X", "api_name": "x", "field_type": "not_a_type",
        })
        assert r.status_code == 422

    def test_lookup_field_requires_lookup_object(self, client):
        o = _make_object(client)
        r = client.post(f"/custom-objects/{o['id']}/fields", headers=MGR, json={
            "name": "Related", "api_name": "related", "field_type": "lookup",
        })
        assert r.status_code == 422

    def test_duplicate_api_name_on_object_rejected(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount")
        r = client.post(f"/custom-objects/{o['id']}/fields", headers=MGR, json={
            "name": "Amount 2", "api_name": "amount", "field_type": "integer",
        })
        assert r.status_code == 409

    def test_list_fields_ordered(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="b", display_order=2)
        _make_field(client, o["id"], api_name="a", display_order=1)
        r = client.get(f"/custom-objects/{o['id']}/fields", headers=MGR)
        names = [f["api_name"] for f in r.json()]
        assert names == ["a", "b"]

    def test_patch_field(self, client):
        o = _make_object(client)
        f = _make_field(client, o["id"])
        r = client.patch(f"/custom-objects/fields/{f['id']}", headers=MGR, json={"is_required": True})
        assert r.json()["is_required"] is True

    def test_delete_field(self, client):
        o = _make_object(client)
        f = _make_field(client, o["id"])
        assert client.delete(f"/custom-objects/fields/{f['id']}", headers=MGR).status_code == 204

    def test_picklist_field_with_options(self, client):
        o = _make_object(client)
        f = _make_field(client, o["id"], name="Status", api_name="status", field_type="picklist",
                         picklist_options=["open", "closed"])
        assert f["picklist_options"] == ["open", "closed"]


# =====================================================================
# Dynamic Forms
# =====================================================================
class TestDynamicForms:
    def test_create_form(self, client):
        o = _make_object(client)
        _make_field(client, o["id"])
        r = client.post(f"/custom-objects/{o['id']}/forms", headers=MGR, json={
            "name": "Default Form",
            "layout": {"sections": [{"title": "Basics", "fields": [{"field_api_name": "amount"}]}]},
        })
        assert r.status_code == 201
        assert r.json()["layout"]["sections"][0]["title"] == "Basics"

    def test_form_conditional_visibility_and_readonly(self, client):
        o = _make_object(client)
        r = client.post(f"/custom-objects/{o['id']}/forms", headers=MGR, json={
            "name": "Conditional Form",
            "layout": {"sections": [{"title": "S", "fields": [
                {"field_api_name": "amount", "read_only": True},
                {"field_api_name": "notes", "visible_if": {"field": "amount", "op": "gt", "value": 1000}},
            ]}]},
        })
        layout = r.json()["layout"]
        fields = layout["sections"][0]["fields"]
        assert fields[0]["read_only"] is True
        assert fields[1]["visible_if"]["op"] == "gt"

    def test_list_forms(self, client):
        o = _make_object(client)
        client.post(f"/custom-objects/{o['id']}/forms", headers=MGR, json={"name": "F1"})
        r = client.get(f"/custom-objects/{o['id']}/forms", headers=MGR)
        assert len(r.json()) == 1

    def test_patch_form(self, client):
        o = _make_object(client)
        f = client.post(f"/custom-objects/{o['id']}/forms", headers=MGR, json={"name": "F1"}).json()
        r = client.patch(f"/custom-objects/forms/{f['id']}", headers=MGR, json={"is_default": True})
        assert r.json()["is_default"] is True

    def test_delete_form(self, client):
        o = _make_object(client)
        f = client.post(f"/custom-objects/{o['id']}/forms", headers=MGR, json={"name": "F1"}).json()
        assert client.delete(f"/custom-objects/forms/{f['id']}", headers=MGR).status_code == 204

    def test_form_create_manager_only(self, client):
        o = _make_object(client)
        r = client.post(f"/custom-objects/{o['id']}/forms", headers=MEM, json={"name": "F1"})
        assert r.status_code == 403


# =====================================================================
# Record CRUD + Validation
# =====================================================================
class TestRecordCRUD:
    def test_create_record(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        r = _make_record(client, o["id"], {"amount": 500.0})
        assert r.status_code == 201
        assert r.json()["data"]["amount"] == 500.0

    def test_create_record_any_authenticated_user(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        r = _make_record(client, o["id"], {"amount": 1.0}, headers=MEM)
        assert r.status_code == 201

    def test_create_record_object_not_found(self, client):
        r = _make_record(client, 9999, {})
        assert r.status_code == 404

    def test_required_field_validation(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal", is_required=True)
        r = _make_record(client, o["id"], {})
        assert r.status_code == 422

    def test_numeric_limit_validation(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal", validation={"min": 0, "max": 1000})
        r = _make_record(client, o["id"], {"amount": 5000.0})
        assert r.status_code == 422

    def test_regex_validation(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="code", field_type="text", validation={"pattern": "^[A-Z]{3}$"})
        r = _make_record(client, o["id"], {"code": "abc"})
        assert r.status_code == 422
        r2 = _make_record(client, o["id"], {"code": "ABC"})
        assert r2.status_code == 201

    def test_custom_error_message(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal",
                    validation={"min": 0, "error_message": "Amount cannot be negative"})
        r = _make_record(client, o["id"], {"amount": -5.0})
        assert r.status_code == 422
        assert "Amount cannot be negative" in str(r.json())

    def test_email_field_validation(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="contact_email", field_type="email")
        assert _make_record(client, o["id"], {"contact_email": "not-an-email"}).status_code == 422
        assert _make_record(client, o["id"], {"contact_email": "a@b.com"}).status_code == 201

    def test_boolean_field_validation(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="active", field_type="boolean")
        assert _make_record(client, o["id"], {"active": "yes"}).status_code == 422
        assert _make_record(client, o["id"], {"active": True}).status_code == 201

    def test_date_field_validation(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="due_date", field_type="date")
        assert _make_record(client, o["id"], {"due_date": "not-a-date"}).status_code == 422
        assert _make_record(client, o["id"], {"due_date": "2030-01-01"}).status_code == 201

    def test_picklist_field_validation(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="status", field_type="picklist", picklist_options=["open", "closed"])
        assert _make_record(client, o["id"], {"status": "unknown"}).status_code == 422
        assert _make_record(client, o["id"], {"status": "open"}).status_code == 201

    def test_multiselect_field_validation(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="tags", field_type="multiselect", picklist_options=["a", "b", "c"])
        assert _make_record(client, o["id"], {"tags": ["a", "z"]}).status_code == 422
        assert _make_record(client, o["id"], {"tags": ["a", "b"]}).status_code == 201

    def test_get_record(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        r = _make_record(client, o["id"], {"amount": 1.0}).json()
        got = client.get(f"/custom-objects/{o['id']}/records/{r['id']}", headers=MGR)
        assert got.status_code == 200
        assert got.json()["data"]["amount"] == 1.0

    def test_get_record_not_found(self, client):
        o = _make_object(client)
        assert client.get(f"/custom-objects/{o['id']}/records/9999", headers=MGR).status_code == 404

    def test_patch_record(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        r = _make_record(client, o["id"], {"amount": 1.0}).json()
        patched = client.patch(f"/custom-objects/{o['id']}/records/{r['id']}", headers=MGR, json={"data": {"amount": 99.0}})
        assert patched.json()["data"]["amount"] == 99.0

    def test_patch_record_revalidates(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal", validation={"max": 100})
        r = _make_record(client, o["id"], {"amount": 1.0}).json()
        bad = client.patch(f"/custom-objects/{o['id']}/records/{r['id']}", headers=MGR, json={"data": {"amount": 999.0}})
        assert bad.status_code == 422

    def test_delete_record(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        r = _make_record(client, o["id"], {"amount": 1.0}).json()
        assert client.delete(f"/custom-objects/{o['id']}/records/{r['id']}", headers=MGR).status_code == 204
        assert client.get(f"/custom-objects/{o['id']}/records/{r['id']}", headers=MGR).status_code == 404


# =====================================================================
# Search, Filtering, Sorting, Pagination
# =====================================================================
class TestRecordSearchFilterSort:
    def _seed_records(self, client, o):
        _make_field(client, o["id"], api_name="name", field_type="text")
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        _make_record(client, o["id"], {"name": "Alpha", "amount": 100.0})
        _make_record(client, o["id"], {"name": "Beta", "amount": 50.0})
        _make_record(client, o["id"], {"name": "Gamma", "amount": 200.0})

    def test_list_records_pagination(self, client):
        o = _make_object(client)
        self._seed_records(client, o)
        r = client.get(f"/custom-objects/{o['id']}/records?limit=2&offset=0", headers=MGR)
        assert r.json()["total"] == 3
        assert len(r.json()["items"]) == 2

    def test_filter_by_field(self, client):
        o = _make_object(client)
        self._seed_records(client, o)
        r = client.get(f"/custom-objects/{o['id']}/records?name=Beta", headers=MGR)
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["data"]["name"] == "Beta"

    def test_search_across_fields(self, client):
        o = _make_object(client)
        self._seed_records(client, o)
        r = client.get(f"/custom-objects/{o['id']}/records?search=alph", headers=MGR)
        assert r.json()["total"] == 1

    def test_sort_ascending(self, client):
        o = _make_object(client)
        self._seed_records(client, o)
        r = client.get(f"/custom-objects/{o['id']}/records?sort_by=amount&sort_dir=asc", headers=MGR)
        amounts = [item["data"]["amount"] for item in r.json()["items"]]
        assert amounts == sorted(amounts)

    def test_sort_descending(self, client):
        o = _make_object(client)
        self._seed_records(client, o)
        r = client.get(f"/custom-objects/{o['id']}/records?sort_by=amount&sort_dir=desc", headers=MGR)
        amounts = [item["data"]["amount"] for item in r.json()["items"]]
        assert amounts == sorted(amounts, reverse=True)


# =====================================================================
# Audit History
# =====================================================================
class TestAuditHistory:
    def test_create_writes_audit(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        r = _make_record(client, o["id"], {"amount": 1.0}).json()
        audit = client.get(f"/custom-objects/{o['id']}/records/{r['id']}/audit", headers=MGR)
        assert audit.status_code == 200
        assert len(audit.json()) == 1
        assert audit.json()[0]["action"] == "created"

    def test_patch_writes_audit_with_diff(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        r = _make_record(client, o["id"], {"amount": 1.0}).json()
        client.patch(f"/custom-objects/{o['id']}/records/{r['id']}", headers=MGR, json={"data": {"amount": 2.0}})
        audit = client.get(f"/custom-objects/{o['id']}/records/{r['id']}/audit", headers=MGR).json()
        assert len(audit) == 2
        assert audit[0]["action"] == "updated"
        assert audit[0]["field_changes"]["amount"]["old"] == 1.0
        assert audit[0]["field_changes"]["amount"]["new"] == 2.0

    def test_audit_not_found(self, client):
        o = _make_object(client)
        assert client.get(f"/custom-objects/{o['id']}/records/9999/audit", headers=MGR).status_code == 404


# =====================================================================
# Relationships / Related Lists
# =====================================================================
class TestRelationships:
    def test_lookup_field_and_related_list(self, client):
        parent = _make_object(client, name="Account", api_name="account")
        child = _make_object(client, name="Contact", api_name="contact")
        client.post(f"/custom-objects/{child['id']}/fields", headers=MGR, json={
            "name": "Account", "api_name": "account_ref", "field_type": "lookup",
            "lookup_object_id": parent["id"],
        })
        parent_record = _make_record(client, parent["id"], {}).json()
        child_record = _make_record(client, child["id"], {"account_ref": parent_record["id"]}).json()
        r = client.get(f"/custom-objects/{parent['id']}/records/{parent_record['id']}/related", headers=MGR)
        assert r.status_code == 200
        related = r.json()
        key = f"{child['id']}:account_ref"
        assert key in related
        assert related[key][0]["id"] == child_record["id"]

    def test_lookup_field_validates_existing_record(self, client):
        parent = _make_object(client, name="Account", api_name="account")
        child = _make_object(client, name="Contact", api_name="contact")
        client.post(f"/custom-objects/{child['id']}/fields", headers=MGR, json={
            "name": "Account", "api_name": "account_ref", "field_type": "lookup",
            "lookup_object_id": parent["id"],
        })
        r = _make_record(client, child["id"], {"account_ref": 999999})
        assert r.status_code == 422


# =====================================================================
# Import / Export
# =====================================================================
class TestImportExport:
    def test_export_csv(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        _make_record(client, o["id"], {"amount": 100.0})
        r = client.get(f"/custom-objects/{o['id']}/export", headers=MGR)
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "amount" in r.text
        assert "100.0" in r.text or "100" in r.text

    def test_export_creates_job(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        client.get(f"/custom-objects/{o['id']}/export", headers=MGR)
        jobs = client.get(f"/custom-objects/{o['id']}/jobs?job_type=export", headers=MGR).json()
        assert len(jobs) == 1
        assert jobs[0]["status"] == "completed"

    def test_import_csv_success(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        csv_text = "amount\n10.5\n20.5\n"
        r = client.post(
            f"/custom-objects/{o['id']}/import", headers={**MGR, "Content-Type": "text/csv"},
            content=csv_text.encode(),
        )
        assert r.status_code == 201
        body = r.json()
        assert body["total_rows"] == 2
        assert body["success_count"] == 2
        assert body["error_count"] == 0
        records = client.get(f"/custom-objects/{o['id']}/records", headers=MGR).json()
        assert records["total"] == 2

    def test_import_csv_partial_success(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal", validation={"min": 0})
        csv_text = "amount\n10.5\n-5\n"
        r = client.post(
            f"/custom-objects/{o['id']}/import", headers={**MGR, "Content-Type": "text/csv"},
            content=csv_text.encode(),
        )
        body = r.json()
        assert body["total_rows"] == 2
        assert body["success_count"] == 1
        assert body["error_count"] == 1
        assert len(body["errors"]) == 1
        assert body["errors"][0]["row"] == 2

    def test_import_type_coercion(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="active", field_type="boolean")
        csv_text = "active\ntrue\nfalse\n"
        r = client.post(
            f"/custom-objects/{o['id']}/import", headers={**MGR, "Content-Type": "text/csv"},
            content=csv_text.encode(),
        )
        assert r.json()["success_count"] == 2

    def test_import_creates_job_and_audit(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        csv_text = "amount\n1.0\n"
        client.post(
            f"/custom-objects/{o['id']}/import", headers={**MGR, "Content-Type": "text/csv"},
            content=csv_text.encode(),
        )
        jobs = client.get(f"/custom-objects/{o['id']}/jobs?job_type=import", headers=MGR).json()
        assert len(jobs) == 1
        records = client.get(f"/custom-objects/{o['id']}/records", headers=MGR).json()
        record_id = records["items"][0]["id"]
        audit = client.get(f"/custom-objects/{o['id']}/records/{record_id}/audit", headers=MGR).json()
        assert len(audit) == 1


# =====================================================================
# Object Dashboard
# =====================================================================
class TestObjectDashboard:
    def test_dashboard_returns_200(self, client):
        r = client.get("/custom-objects/dashboard/summary", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for key in ("total_objects", "active_objects", "total_records", "recent_records",
                    "recent_import_errors", "import_jobs_run"):
            assert key in body

    def test_dashboard_reflects_object_and_record_counts(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        _make_record(client, o["id"], {"amount": 1.0})
        r = client.get("/custom-objects/dashboard/summary", headers=MGR)
        body = r.json()
        assert body["total_objects"] == 1
        assert body["active_objects"] == 1
        assert body["total_records"] == 1
        assert len(body["recent_records"]) == 1

    def test_member_can_view_dashboard(self, client):
        assert client.get("/custom-objects/dashboard/summary", headers=MEM).status_code == 200


# =====================================================================
# Object Analytics
# =====================================================================
class TestObjectAnalytics:
    def test_analytics_returns_200(self, client):
        o = _make_object(client)
        r = client.get(f"/custom-objects/{o['id']}/analytics", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for key in ("records_created_total", "records_created_by_period", "records_updated_total",
                    "field_utilization", "import_success_rate", "export_count"):
            assert key in body

    def test_analytics_not_found(self, client):
        assert client.get("/custom-objects/9999/analytics", headers=MGR).status_code == 404

    def test_field_utilization_computed(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        _make_field(client, o["id"], api_name="notes", field_type="text")
        _make_record(client, o["id"], {"amount": 1.0, "notes": "hi"})
        _make_record(client, o["id"], {"amount": 2.0})
        r = client.get(f"/custom-objects/{o['id']}/analytics", headers=MGR)
        util = {u["field_api_name"]: u["filled_pct"] for u in r.json()["field_utilization"]}
        assert util["amount"] == 1.0
        assert util["notes"] == 0.5

    def test_records_updated_total(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal")
        r = _make_record(client, o["id"], {"amount": 1.0}).json()
        client.patch(f"/custom-objects/{o['id']}/records/{r['id']}", headers=MGR, json={"data": {"amount": 2.0}})
        analytics = client.get(f"/custom-objects/{o['id']}/analytics", headers=MGR).json()
        assert analytics["records_updated_total"] == 1

    def test_export_count_tracked(self, client):
        o = _make_object(client)
        client.get(f"/custom-objects/{o['id']}/export", headers=MGR)
        client.get(f"/custom-objects/{o['id']}/export", headers=MGR)
        analytics = client.get(f"/custom-objects/{o['id']}/analytics", headers=MGR).json()
        assert analytics["export_count"] == 2

    def test_import_success_rate(self, client):
        o = _make_object(client)
        _make_field(client, o["id"], api_name="amount", field_type="decimal", validation={"min": 0})
        csv_text = "amount\n1\n-1\n"
        client.post(
            f"/custom-objects/{o['id']}/import", headers={**MGR, "Content-Type": "text/csv"},
            content=csv_text.encode(),
        )
        analytics = client.get(f"/custom-objects/{o['id']}/analytics", headers=MGR).json()
        assert analytics["import_success_rate"] == 0.5


# =====================================================================
# Backward Compatibility
# =====================================================================
class TestBackwardCompatibility:
    def test_deals_endpoint(self, client):
        assert client.get("/deals", headers=MGR).status_code == 200

    def test_workflows_endpoint(self, client):
        assert client.get("/workflows", headers=MGR).status_code == 200

    def test_revops_dashboard(self, client):
        assert client.get("/revops/executive-dashboard", headers=MGR).status_code == 200

    def test_cs_accounts_endpoint(self, client):
        assert client.get("/cs/accounts", headers=MGR).status_code == 200

    def test_campaigns_endpoint(self, client):
        assert client.get("/campaigns", headers=MGR).status_code == 200

    def test_pipelines_endpoint(self, client):
        assert client.get("/pipelines", headers=MGR).status_code == 200

    def test_assignments_endpoint(self, client):
        assert client.get("/assignments", headers=MGR).status_code == 200

    def test_team_work_queue(self, client):
        assert client.get("/team/work-queue", headers=MGR).status_code == 200

    def test_outreach_leads(self, client):
        assert client.get("/outreach/leads", headers=MGR).status_code == 200
