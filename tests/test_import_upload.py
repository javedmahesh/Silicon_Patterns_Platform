"""Phase 6 — base64 Excel upload endpoint that feeds the existing preview/review flow."""
import base64
import io

import openpyxl
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from integration.normalizer import name_key
from master_db.models import Base, Company


def _company(domain, nm):
    return Company(company_domain=domain, canonical_company_id=name_key(nm).upper().replace(" ", ""),
                   company_name=nm, name_key=name_key(nm), validation_status="VALID")


def _xlsx_b64() -> str:
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Sales_Research_Master_v7"
    ws.append(["Company Name", "Company Website", "Contact First Name", "Contact Last Name",
               "Designation", "LinkedIn URL"])
    ws.append(["Groq", "https://groq.com", "Jane", "New", "VP", "https://linkedin.com/in/jane-new"])
    buf = io.BytesIO(); wb.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def test_upload_generates_preview_and_review(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'up.db').as_posix()}", log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(_company("amd.com", "Advanced Micro Devices")); s.commit()
        body = {"filename": "hist.xlsx", "content_base64": _xlsx_b64()}
        # upload is admin-only
        assert c.post("/sync/imports/upload", headers={"X-Dev-Role": "manager"}, json=body).status_code == 403
        resp = c.post("/sync/imports/upload", headers={"X-Dev-Role": "admin"}, json=body)
        assert resp.status_code == 200
        iid = resp.json()["import_id"]
        # the uploaded file was reconciled + seeded with review items (Groq = new)
        review = c.get(f"/sync/imports/{iid}/review", headers={"X-Dev-Role": "manager"}).json()
        assert any(i["category"] == "new_decision_maker" for i in review["items"])
        assert review["stats"]["total"] >= 2


def test_upload_rejects_bad_base64(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'up2.db').as_posix()}", log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        bad = {"filename": "x.xlsx", "content_base64": "not-valid-base64!!!"}
        assert c.post("/sync/imports/upload", headers={"X-Dev-Role": "admin"}, json=bad).status_code == 422
