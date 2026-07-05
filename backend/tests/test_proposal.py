"""Backend tests for the new AI Proposal Writer module."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for ln in f:
            if ln.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = ln.split("=", 1)[1].strip().rstrip("/")


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def project(s):
    r = s.post(f"{BASE_URL}/api/projects", json={
        "name": "TEST_PROPOSAL_MODULE",
        "description": "Testing AI proposal writer end-to-end",
        "status": "In Progress",
    })
    assert r.status_code in (200, 201), r.text
    pid = r.json()["id"]
    # add a task + note for context
    s.post(f"{BASE_URL}/api/tasks", json={"project_id": pid, "title": "TEST_task1", "status": "todo"})
    s.post(f"{BASE_URL}/api/notes", json={"project_id": pid, "content": "Client wants to increase conversions by 40%."})
    yield pid
    s.delete(f"{BASE_URL}/api/projects/{pid}")


# --- Sections/statuses schema ---
def test_proposal_sections_schema(s):
    r = s.get(f"{BASE_URL}/api/proposal/sections")
    assert r.status_code == 200
    data = r.json()
    keys = [x["key"] for x in data["sections"]]
    expected = ["executive_summary", "client_goals", "business_challenges", "recommended_solution",
                "project_scope", "deliverables", "timeline", "milestones", "technical_approach",
                "success_metrics", "pricing_placeholder", "payment_schedule", "assumptions",
                "terms_conditions", "acceptance_section"]
    assert keys == expected
    assert data["statuses"] == ["Draft", "Generated", "Sent", "Accepted", "Rejected", "Archived"]


# --- Generate (real LLM) ---
def test_generate_bad_project(s):
    r = s.post(f"{BASE_URL}/api/projects/nonexistent-id/proposal/generate")
    assert r.status_code == 404


@pytest.fixture(scope="module")
def generated(s, project):
    r = s.post(f"{BASE_URL}/api/projects/{project}/proposal/generate", timeout=120)
    assert r.status_code == 200, r.text
    return r.json()


def test_generate_shape(generated):
    assert "title" in generated
    assert "content" in generated
    keys = ["executive_summary", "client_goals", "business_challenges", "recommended_solution",
            "project_scope", "deliverables", "timeline", "milestones", "technical_approach",
            "success_metrics", "pricing_placeholder", "payment_schedule", "assumptions",
            "terms_conditions", "acceptance_section"]
    for k in keys:
        assert k in generated["content"], f"missing {k}"
    # at least a few sections populated
    populated = sum(1 for k in keys if generated["content"].get(k))
    assert populated >= 10


def test_generate_logs_activity(s, project):
    r = s.get(f"{BASE_URL}/api/activities?project_id={project}")
    assert r.status_code == 200
    types = [a["type"] for a in r.json()]
    assert "proposal_generated" in types


# --- Save & versioning ---
def test_save_v1_and_persist(s, project, generated):
    payload = {"title": generated["title"], "status": "Generated", "content": generated["content"]}
    r = s.post(f"{BASE_URL}/api/projects/{project}/proposal", json=payload)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["version"] == 1
    assert doc["title"] == payload["title"]
    assert doc["status"] == "Generated"
    assert doc["project_id"] == project
    assert "client_id" in doc
    assert "content" in doc
    assert "history" in doc and len(doc["history"]) == 1
    assert "created_at" in doc and "updated_at" in doc

    # GET should return same doc
    g = s.get(f"{BASE_URL}/api/projects/{project}/proposal")
    assert g.status_code == 200
    assert g.json()["version"] == 1


def test_save_v2_increments(s, project, generated):
    payload = {"title": generated["title"] + " v2", "status": "Draft",
               "content": {**generated["content"], "executive_summary": "Edited summary v2"}}
    r = s.post(f"{BASE_URL}/api/projects/{project}/proposal", json=payload)
    assert r.status_code == 200
    doc = r.json()
    assert doc["version"] == 2
    assert doc["content"]["executive_summary"] == "Edited summary v2"
    assert len(doc["history"]) == 2


def test_invalid_status(s, project, generated):
    r = s.post(f"{BASE_URL}/api/projects/{project}/proposal",
               json={"title": "x", "status": "Weird", "content": generated["content"]})
    assert r.status_code == 422


def test_versions_endpoint(s, project):
    r = s.get(f"{BASE_URL}/api/projects/{project}/proposal/versions")
    assert r.status_code == 200
    hist = r.json()
    assert isinstance(hist, list)
    assert len(hist) >= 2
    assert {v["version"] for v in hist} >= {1, 2}


def test_save_activity_logged(s, project):
    r = s.get(f"{BASE_URL}/api/activities?project_id={project}")
    types = [a["type"] for a in r.json()]
    assert types.count("proposal_saved") >= 2


# --- Restore ---
def test_restore_creates_new_version(s, project):
    r = s.post(f"{BASE_URL}/api/projects/{project}/proposal/restore/1")
    assert r.status_code == 200
    doc = r.json()
    assert doc["version"] == 3  # non-destructive: new version
    # content matches v1 exactly
    v1 = next(v for v in doc["history"] if v["version"] == 1)
    assert doc["content"] == v1["content"]


# --- Exports ---
def test_export_pdf(s, project):
    r = s.get(f"{BASE_URL}/api/projects/{project}/proposal/export/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


def test_export_docx(s, project):
    r = s.get(f"{BASE_URL}/api/projects/{project}/proposal/export/docx")
    assert r.status_code == 200
    assert "officedocument.wordprocessingml.document" in r.headers["content-type"]
    assert r.content[:2] == b"PK"  # zip magic


def test_export_activity_logged(s, project):
    r = s.get(f"{BASE_URL}/api/activities?project_id={project}")
    types = [a["type"] for a in r.json()]
    assert types.count("proposal_exported") >= 2


def test_export_before_save_returns_404(s):
    r = s.post(f"{BASE_URL}/api/projects", json={"name": "TEST_NO_SAVE_EXPORT"})
    pid = r.json()["id"]
    try:
        pdf = s.get(f"{BASE_URL}/api/projects/{pid}/proposal/export/pdf")
        docx = s.get(f"{BASE_URL}/api/projects/{pid}/proposal/export/docx")
        assert pdf.status_code == 404
        assert docx.status_code == 404
    finally:
        s.delete(f"{BASE_URL}/api/projects/{pid}")


# --- Regression: existing plural "Proposals" CRUD (proposal_generated activity) ---
def test_plural_proposals_crud_still_works(s, project):
    r = s.post(f"{BASE_URL}/api/proposals", json={"project_id": project, "title": "TEST_plural_prop", "content": "hi"})
    assert r.status_code == 200
    pid = r.json()["id"]
    lst = s.get(f"{BASE_URL}/api/proposals?project_id={project}")
    assert lst.status_code == 200
    assert any(x["id"] == pid for x in lst.json())
    d = s.delete(f"{BASE_URL}/api/proposals/{pid}")
    assert d.status_code == 200


# --- Regression: AI planner endpoints reachable ---
def test_planner_endpoints_reachable(s, project):
    r = s.get(f"{BASE_URL}/api/projects/{project}/plans")
    assert r.status_code == 200
    r2 = s.get(f"{BASE_URL}/api/projects/{project}/plans")
    assert r2.status_code == 200
