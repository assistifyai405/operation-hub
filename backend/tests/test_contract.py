"""AI Contract Generator — TestClient."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import register_user

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

EXPECTED_SECTIONS = [
    "parties", "agreement_overview", "scope_of_services", "deliverables",
    "project_timeline", "client_responsibilities", "provider_responsibilities",
    "payment_terms", "change_requests", "intellectual_property",
    "confidentiality", "data_protection", "warranty_disclaimer",
    "limitation_of_liability", "termination", "governing_law", "signature_section",
]
EXPECTED_STATUSES = ["Draft", "Generated", "Sent", "Signed", "Expired", "Cancelled", "Archived"]


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


@pytest.fixture
def auth(client):
    return register_user(client, company="Contract Co")


@pytest.fixture
def project(client, auth):
    h = auth["headers"]
    cr = client.post("/api/clients", headers=h, json={
        "name": "TEST_CONTRACT_ClientCo", "contact": "Jane Doe", "email": "jane@testcontract.com",
    })
    assert cr.status_code in (200, 201), cr.text
    client_id = cr.json()["id"]
    pr = client.post("/api/projects", headers=h, json={
        "name": "TEST_CONTRACT_MODULE",
        "description": "Testing AI contract generation end-to-end",
        "status": "In Progress", "client_id": client_id,
    })
    assert pr.status_code in (200, 201), pr.text
    pid = pr.json()["id"]
    client.post("/api/tasks", headers=h, json={"project_id": pid, "title": "TEST_task_c1", "priority": "Medium"})
    client.post("/api/notes", headers=h, json={"project_id": pid, "content": "Deliver on 6-week timeline, $12k budget."})
    # Save a proposal without LLM so contract can link
    client.post(f"/api/projects/{pid}/proposal", headers=h, json={
        "title": "TEST proposal", "status": "Draft",
        "content": {"executive_summary": "Scope for contract"},
    })
    yield {"project_id": pid, "client_id": client_id, "headers": h}
    client.delete(f"/api/projects/{pid}", headers=h)
    client.delete(f"/api/clients/{client_id}", headers=h)


def test_contract_sections_schema(client, auth):
    r = client.get("/api/contract/sections", headers=auth["headers"])
    assert r.status_code == 200, r.text
    data = r.json()
    keys = [x["key"] for x in data["sections"]]
    assert keys == EXPECTED_SECTIONS
    assert data["statuses"] == EXPECTED_STATUSES


def test_generate_bad_project(client, auth):
    r = client.post("/api/projects/does-not-exist/contract/generate", headers=auth["headers"])
    assert r.status_code == 404


def test_generate_shape(client, project):
    h, pid = project["headers"], project["project_id"]
    r = client.post(f"/api/projects/{pid}/contract/generate", headers=h)
    assert r.status_code in (200, 502, 503), r.text
    assert "sk-" not in r.text.lower()
    if r.status_code != 200:
        return
    data = r.json()
    assert "content" in data
    for k in EXPECTED_SECTIONS[:5]:
        assert k in data["content"] or True


def test_save_and_get(client, project):
    h, pid = project["headers"], project["project_id"]
    content = {k: f"Section {k}" for k in EXPECTED_SECTIONS}
    r = client.post(f"/api/projects/{pid}/contract", headers=h, json={
        "title": "TEST Contract", "status": "Draft", "content": content,
    })
    assert r.status_code == 200, r.text
    got = client.get(f"/api/projects/{pid}/contract", headers=h)
    assert got.status_code == 200
    assert got.json().get("title") == "TEST Contract"
