"""Backend tests for the new AI Contract Generator module."""
import os
import io
import zipfile
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for ln in f:
            if ln.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = ln.split("=", 1)[1].strip().rstrip("/")

EXPECTED_SECTIONS = [
    "parties", "agreement_overview", "scope_of_services", "deliverables",
    "project_timeline", "client_responsibilities", "provider_responsibilities",
    "payment_terms", "change_requests", "intellectual_property",
    "confidentiality", "data_protection", "warranty_disclaimer",
    "limitation_of_liability", "termination", "governing_law", "signature_section",
]
EXPECTED_STATUSES = ["Draft", "Generated", "Sent", "Signed", "Expired", "Cancelled", "Archived"]


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def project_with_proposal(s):
    # Create client
    cr = s.post(f"{BASE_URL}/api/clients", json={
        "name": "TEST_CONTRACT_ClientCo",
        "contact": "Jane Doe",
        "email": "jane@testcontract.com",
    })
    assert cr.status_code in (200, 201), cr.text
    client_id = cr.json()["id"]

    # Create project
    pr = s.post(f"{BASE_URL}/api/projects", json={
        "name": "TEST_CONTRACT_MODULE",
        "description": "Testing AI contract generation end-to-end",
        "status": "In Progress",
        "client_id": client_id,
    })
    assert pr.status_code in (200, 201), pr.text
    pid = pr.json()["id"]

    # Add task + note for context
    s.post(f"{BASE_URL}/api/tasks", json={"project_id": pid, "title": "TEST_task_c1", "status": "todo"})
    s.post(f"{BASE_URL}/api/notes", json={"project_id": pid, "content": "Deliver on 6-week timeline, $12k budget."})

    # Generate + save a proposal so contract can link it (smart data)
    gen = s.post(f"{BASE_URL}/api/projects/{pid}/proposal/generate", timeout=180)
    if gen.status_code == 200:
        body = gen.json()
        s.post(f"{BASE_URL}/api/projects/{pid}/proposal", json={
            "title": body.get("title") or "TEST proposal",
            "status": "Draft",
            "content": body.get("content", {}),
        })

    yield {"project_id": pid, "client_id": client_id}
    s.delete(f"{BASE_URL}/api/projects/{pid}")
    s.delete(f"{BASE_URL}/api/clients/{client_id}")


# --- Schema endpoint ---
def test_contract_sections_schema(s):
    r = s.get(f"{BASE_URL}/api/contract/sections")
    assert r.status_code == 200, r.text
    data = r.json()
    keys = [x["key"] for x in data["sections"]]
    assert keys == EXPECTED_SECTIONS
    assert data["statuses"] == EXPECTED_STATUSES


# --- Generate ---
def test_generate_bad_project(s):
    r = s.post(f"{BASE_URL}/api/projects/does-not-exist-xyz/contract/generate")
    assert r.status_code == 404


@pytest.fixture(scope="module")
def generated(s, project_with_proposal):
    pid = project_with_proposal["project_id"]
    r = s.post(f"{BASE_URL}/api/projects/{pid}/contract/generate", timeout=180)
    assert r.status_code == 200, r.text
    return r.json()


def test_generate_shape_and_sections(generated):
    assert "title" in generated
    assert "content" in generated
    assert "proposal_id" in generated
    content = generated["content"]
    missing = [k for k in EXPECTED_SECTIONS if k not in content]
    assert not missing, f"Missing keys: {missing}"
    # All sections populated (non-empty)
    for k in EXPECTED_SECTIONS:
        v = content[k]
        if isinstance(v, list):
            assert len(v) > 0, f"Empty list for {k}"
        else:
            assert v and str(v).strip(), f"Empty text for {k}"


def test_generated_links_proposal(generated):
    # smart data: proposal_id linked if proposal exists
    assert generated.get("proposal_id"), "proposal_id should be populated when project has a saved proposal"


def test_activity_contract_generated(s, project_with_proposal):
    pid = project_with_proposal["project_id"]
    r = s.get(f"{BASE_URL}/api/activities", params={"project_id": pid})
    assert r.status_code == 200
    types = [a.get("type") for a in r.json()]
    assert "contract_generated" in types


# --- Save (v1) ---
def test_save_v1(s, project_with_proposal, generated):
    pid = project_with_proposal["project_id"]
    payload = {"title": generated["title"], "status": "Draft", "content": generated["content"]}
    r = s.post(f"{BASE_URL}/api/projects/{pid}/contract", json=payload)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["version"] == 1
    for f in ("title", "project_id", "client_id", "proposal_id", "status", "content", "version", "history", "created_at", "updated_at"):
        assert f in doc, f"missing field {f}"
    assert doc["proposal_id"] is not None
    assert len(doc["history"]) == 1


def test_get_contract_persisted(s, project_with_proposal):
    pid = project_with_proposal["project_id"]
    r = s.get(f"{BASE_URL}/api/projects/{pid}/contract")
    assert r.status_code == 200
    assert r.json()["version"] >= 1


def test_save_invalid_status(s, project_with_proposal, generated):
    pid = project_with_proposal["project_id"]
    r = s.post(f"{BASE_URL}/api/projects/{pid}/contract", json={
        "title": "x", "status": "NotAStatus", "content": generated["content"],
    })
    assert r.status_code == 422


def test_save_v2_increments(s, project_with_proposal, generated):
    pid = project_with_proposal["project_id"]
    payload = {"title": generated["title"] + " v2", "status": "Generated", "content": generated["content"]}
    r = s.post(f"{BASE_URL}/api/projects/{pid}/contract", json=payload)
    assert r.status_code == 200
    doc = r.json()
    assert doc["version"] == 2
    assert len(doc["history"]) == 2


def test_versions_endpoint(s, project_with_proposal):
    pid = project_with_proposal["project_id"]
    r = s.get(f"{BASE_URL}/api/projects/{pid}/contract/versions")
    assert r.status_code == 200
    hist = r.json()
    assert len(hist) >= 2
    assert hist[0]["version"] == 1


# --- Restore ---
def test_restore_creates_new_version(s, project_with_proposal):
    pid = project_with_proposal["project_id"]
    before = s.get(f"{BASE_URL}/api/projects/{pid}/contract").json()
    v1_content = before["history"][0]["content"]
    r = s.post(f"{BASE_URL}/api/projects/{pid}/contract/restore/1")
    assert r.status_code == 200
    doc = r.json()
    assert doc["version"] == before["version"] + 1
    assert doc["content"] == v1_content
    # activity logged as restored, not saved
    act = s.get(f"{BASE_URL}/api/activities", params={"project_id": pid}).json()
    types = [a.get("type") for a in act]
    assert "contract_restored" in types


# --- Exports ---
def test_export_pdf(s, project_with_proposal):
    pid = project_with_proposal["project_id"]
    r = s.get(f"{BASE_URL}/api/projects/{pid}/contract/export/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


def test_export_docx(s, project_with_proposal):
    pid = project_with_proposal["project_id"]
    r = s.get(f"{BASE_URL}/api/projects/{pid}/contract/export/docx")
    assert r.status_code == 200
    assert "wordprocessingml" in r.headers["content-type"]
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    assert "word/document.xml" in zf.namelist()


def test_export_activity_logged(s, project_with_proposal):
    pid = project_with_proposal["project_id"]
    act = s.get(f"{BASE_URL}/api/activities", params={"project_id": pid}).json()
    types = [a.get("type") for a in act]
    assert "contract_exported" in types


def test_export_before_save_returns_404(s):
    # Fresh project
    pr = s.post(f"{BASE_URL}/api/projects", json={"name": "TEST_CONTRACT_UNSAVED", "status": "In Progress"})
    pid = pr.json()["id"]
    try:
        r = s.get(f"{BASE_URL}/api/projects/{pid}/contract/export/pdf")
        assert r.status_code == 404
        r2 = s.get(f"{BASE_URL}/api/projects/{pid}/contract/export/docx")
        assert r2.status_code == 404
    finally:
        s.delete(f"{BASE_URL}/api/projects/{pid}")


# --- Regression: proposal exports still work ---
def test_regression_proposal_exports(s, project_with_proposal):
    pid = project_with_proposal["project_id"]
    r = s.get(f"{BASE_URL}/api/projects/{pid}/proposal/export/pdf")
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF"
    r2 = s.get(f"{BASE_URL}/api/projects/{pid}/proposal/export/docx")
    assert r2.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r2.content))
    assert "word/document.xml" in zf.namelist()
