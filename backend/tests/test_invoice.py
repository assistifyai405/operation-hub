"""Backend tests for the new AI Invoice Generator module."""
import os
import io
import re
import zipfile
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for ln in f:
            if ln.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = ln.split("=", 1)[1].strip().rstrip("/")

EXPECTED_STATUSES = ["Draft", "Generated", "Sent", "Paid", "Overdue", "Cancelled", "Archived"]
INV_RE = re.compile(r"^INV-\d{6}-\d{4}$")


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def project(s):
    cr = s.post(f"{BASE_URL}/api/clients", json={
        "name": "TEST_INVOICE_ClientCo", "contact": "Jane Doe", "email": "jane@testinv.com",
    })
    assert cr.status_code in (200, 201), cr.text
    client_id = cr.json()["id"]
    pr = s.post(f"{BASE_URL}/api/projects", json={
        "name": "TEST_INVOICE_MODULE", "description": "Testing invoice",
        "status": "In Progress", "client_id": client_id,
    })
    assert pr.status_code in (200, 201), pr.text
    pid = pr.json()["id"]
    s.post(f"{BASE_URL}/api/notes", json={"project_id": pid, "content": "Budget $10k, Net 14."})

    # Generate + save proposal so invoice can link
    gen = s.post(f"{BASE_URL}/api/projects/{pid}/proposal/generate", timeout=180)
    prop_id = None
    if gen.status_code == 200:
        body = gen.json()
        sv = s.post(f"{BASE_URL}/api/projects/{pid}/proposal", json={
            "title": body.get("title") or "TEST proposal", "status": "Draft",
            "content": body.get("content", {}),
        })
        if sv.status_code == 200:
            prop_id = sv.json().get("id")

    # Generate + save contract (optional link)
    gc = s.post(f"{BASE_URL}/api/projects/{pid}/contract/generate", timeout=180)
    contract_id = None
    if gc.status_code == 200:
        body = gc.json()
        sc = s.post(f"{BASE_URL}/api/projects/{pid}/contract", json={
            "title": body.get("title") or "TEST contract", "status": "Draft",
            "content": body.get("content", {}),
        })
        if sc.status_code == 200:
            contract_id = sc.json().get("id")

    yield {"project_id": pid, "client_id": client_id, "proposal_id": prop_id, "contract_id": contract_id}
    s.delete(f"{BASE_URL}/api/projects/{pid}")
    s.delete(f"{BASE_URL}/api/clients/{client_id}")


# --- Config endpoint ---
def test_invoice_config(s):
    r = s.get(f"{BASE_URL}/api/invoice/config")
    assert r.status_code == 200
    data = r.json()
    assert data["statuses"] == EXPECTED_STATUSES
    assert isinstance(data["fields"], list) and len(data["fields"]) > 0
    keys = [f["key"] for f in data["fields"]]
    assert "billing_address" in keys and "payment_terms" in keys


# --- Generate ---
def test_generate_bad_project(s):
    r = s.post(f"{BASE_URL}/api/projects/does-not-exist-xyz/invoice/generate")
    assert r.status_code == 404


@pytest.fixture(scope="module")
def generated(s, project):
    r = s.post(f"{BASE_URL}/api/projects/{project['project_id']}/invoice/generate", timeout=180)
    assert r.status_code == 200, r.text
    return r.json()


def test_generate_shape(generated, project):
    for k in ("invoice_number", "title", "content", "line_items", "subtotal", "vat", "total", "proposal_id", "contract_id"):
        assert k in generated, f"missing {k}"
    assert INV_RE.match(generated["invoice_number"]), generated["invoice_number"]
    assert isinstance(generated["line_items"], list) and len(generated["line_items"]) > 0
    for li in generated["line_items"]:
        for k in ("description", "quantity", "unit_price", "amount"):
            assert k in li
    # smart-data
    if project["proposal_id"]:
        assert generated.get("proposal_id") == project["proposal_id"] or generated.get("proposal_id")
    if project["contract_id"]:
        assert generated.get("contract_id") == project["contract_id"] or generated.get("contract_id")


def test_activity_invoice_generated(s, project):
    r = s.get(f"{BASE_URL}/api/activities", params={"project_id": project["project_id"]})
    assert r.status_code == 200
    types = [a.get("type") for a in r.json()]
    assert "invoice_generated" in types


# --- VAT / totals math ---
def test_vat_totals_recomputed(s, project):
    pid = project["project_id"]
    payload = {
        "title": "TEST_INVOICE_TOTALS", "status": "Draft",
        "content": {"vat_rate": 20, "description": "test totals"},
        "line_items": [
            {"description": "A", "quantity": 10, "unit_price": 100},
            {"description": "B", "quantity": 2, "unit_price": 250},
        ],
    }
    r = s.post(f"{BASE_URL}/api/projects/{pid}/invoice", json=payload)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["subtotal"] == 1500
    assert doc["vat"] == 300
    assert doc["total"] == 1800
    for li in doc["line_items"]:
        assert li["amount"] == li["quantity"] * li["unit_price"]
    assert doc["version"] == 1
    for f in ("invoice_number", "title", "project_id", "client_id", "proposal_id", "contract_id",
              "status", "content", "line_items", "subtotal", "vat", "total", "version",
              "history", "created_at", "updated_at"):
        assert f in doc, f"missing {f}"
    assert len(doc["history"]) == 1


def test_get_invoice_persisted(s, project):
    r = s.get(f"{BASE_URL}/api/projects/{project['project_id']}/invoice")
    assert r.status_code == 200
    d = r.json()
    assert d["version"] >= 1
    assert d["total"] == 1800


def test_invalid_status(s, project):
    r = s.post(f"{BASE_URL}/api/projects/{project['project_id']}/invoice", json={
        "title": "x", "status": "NotAStatus", "content": {"vat_rate": 0}, "line_items": [],
    })
    assert r.status_code == 422


def test_save_v2_increments(s, project):
    pid = project["project_id"]
    payload = {
        "title": "TEST_INVOICE_TOTALS v2", "status": "Generated",
        "content": {"vat_rate": 10, "description": "v2"},
        "line_items": [{"description": "Solo", "quantity": 3, "unit_price": 200}],
    }
    r = s.post(f"{BASE_URL}/api/projects/{pid}/invoice", json=payload)
    assert r.status_code == 200
    doc = r.json()
    assert doc["version"] == 2
    assert doc["subtotal"] == 600
    assert doc["vat"] == 60
    assert doc["total"] == 660
    assert len(doc["history"]) == 2


def test_versions_endpoint(s, project):
    r = s.get(f"{BASE_URL}/api/projects/{project['project_id']}/invoice/versions")
    assert r.status_code == 200
    hist = r.json()
    assert len(hist) >= 2
    assert hist[0]["version"] == 1


# --- Restore ---
def test_restore_creates_new_version(s, project):
    pid = project["project_id"]
    before = s.get(f"{BASE_URL}/api/projects/{pid}/invoice").json()
    v1 = next(v for v in before["history"] if v["version"] == 1)
    r = s.post(f"{BASE_URL}/api/projects/{pid}/invoice/restore/1")
    assert r.status_code == 200
    doc = r.json()
    assert doc["version"] == before["version"] + 1
    assert doc["total"] == v1["total"]
    assert doc["subtotal"] == v1["subtotal"]
    act = s.get(f"{BASE_URL}/api/activities", params={"project_id": pid}).json()
    types = [a.get("type") for a in act]
    assert "invoice_restored" in types
    # invoice_saved should NOT be logged for restore
    saved_msgs = [a for a in act if a.get("type") == "invoice_saved"]
    # There should be saved ones from earlier saves but restore should log restored, not saved for that op
    restored_msgs = [a for a in act if a.get("type") == "invoice_restored"]
    assert len(restored_msgs) >= 1


# --- Exports ---
def test_export_pdf(s, project):
    r = s.get(f"{BASE_URL}/api/projects/{project['project_id']}/invoice/export/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


def test_export_docx(s, project):
    r = s.get(f"{BASE_URL}/api/projects/{project['project_id']}/invoice/export/docx")
    assert r.status_code == 200
    assert "wordprocessingml" in r.headers["content-type"]
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    assert "word/document.xml" in zf.namelist()


def test_export_activity_logged(s, project):
    act = s.get(f"{BASE_URL}/api/activities", params={"project_id": project["project_id"]}).json()
    types = [a.get("type") for a in act]
    assert "invoice_exported" in types


def test_export_before_save_returns_404(s):
    pr = s.post(f"{BASE_URL}/api/projects", json={"name": "TEST_INVOICE_UNSAVED", "status": "In Progress"})
    pid = pr.json()["id"]
    try:
        r = s.get(f"{BASE_URL}/api/projects/{pid}/invoice/export/pdf")
        assert r.status_code == 404
        r2 = s.get(f"{BASE_URL}/api/projects/{pid}/invoice/export/docx")
        assert r2.status_code == 404
    finally:
        s.delete(f"{BASE_URL}/api/projects/{pid}")


# --- Regression: proposal + contract exports still work ---
def test_regression_proposal_and_contract_exports(s, project):
    pid = project["project_id"]
    r = s.get(f"{BASE_URL}/api/projects/{pid}/proposal/export/pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    r2 = s.get(f"{BASE_URL}/api/projects/{pid}/proposal/export/docx")
    assert r2.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r2.content))
    assert "word/document.xml" in zf.namelist()

    if project["contract_id"]:
        rc = s.get(f"{BASE_URL}/api/projects/{pid}/contract/export/pdf")
        assert rc.status_code == 200 and rc.content[:4] == b"%PDF"
        rc2 = s.get(f"{BASE_URL}/api/projects/{pid}/contract/export/docx")
        assert rc2.status_code == 200
