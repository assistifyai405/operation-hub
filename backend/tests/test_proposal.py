"""AI Proposal Writer — TestClient."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import register_user

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


@pytest.fixture
def auth(client):
    return register_user(client, company="Proposal Co")


@pytest.fixture
def project(client, auth):
    r = client.post("/api/projects", headers=auth["headers"], json={
        "name": "TEST_PROPOSAL_MODULE",
        "description": "Testing AI proposal writer end-to-end",
        "status": "In Progress",
    })
    assert r.status_code in (200, 201), r.text
    pid = r.json()["id"]
    client.post("/api/tasks", headers=auth["headers"], json={"project_id": pid, "title": "TEST_task1", "priority": "Medium"})
    client.post("/api/notes", headers=auth["headers"], json={"project_id": pid, "content": "Client wants to increase conversions by 40%."})
    yield {"id": pid, "headers": auth["headers"]}
    client.delete(f"/api/projects/{pid}", headers=auth["headers"])


def test_proposal_sections_schema(client, auth):
    r = client.get("/api/proposal/sections", headers=auth["headers"])
    assert r.status_code == 200
    data = r.json()
    keys = [x["key"] for x in data["sections"]]
    expected = [
        "executive_summary", "client_goals", "business_challenges", "recommended_solution",
        "project_scope", "deliverables", "timeline", "milestones", "technical_approach",
        "success_metrics", "pricing_placeholder", "payment_schedule", "assumptions",
        "terms_conditions", "acceptance_section",
    ]
    assert keys == expected
    assert data["statuses"] == ["Draft", "Generated", "Sent", "Accepted", "Rejected", "Archived"]


def test_generate_bad_project(client, auth):
    r = client.post("/api/projects/nonexistent-id/proposal/generate", headers=auth["headers"])
    assert r.status_code == 404


def test_generate_shape(client, project):
    r = client.post(f"/api/projects/{project['id']}/proposal/generate", headers=project["headers"])
    assert r.status_code in (200, 502, 503), r.text
    assert "sk-" not in r.text.lower()
    if r.status_code != 200:
        return
    generated = r.json()
    assert "title" in generated and "content" in generated
    keys = [
        "executive_summary", "client_goals", "business_challenges", "recommended_solution",
        "project_scope", "deliverables", "timeline", "milestones", "technical_approach",
        "success_metrics", "pricing_placeholder", "payment_schedule", "assumptions",
        "terms_conditions", "acceptance_section",
    ]
    for k in keys:
        assert k in generated["content"], f"missing {k}"
    populated = sum(1 for k in keys if generated["content"].get(k))
    assert populated >= 1


def test_save_and_get(client, project):
    h, pid = project["headers"], project["id"]
    content = {"executive_summary": "We will deliver.", "client_goals": "Grow"}
    r = client.post(f"/api/projects/{pid}/proposal", headers=h, json={
        "title": "TEST Proposal", "status": "Draft", "content": content,
    })
    assert r.status_code == 200, r.text
    got = client.get(f"/api/projects/{pid}/proposal", headers=h)
    assert got.status_code == 200
    assert got.json().get("title") == "TEST Proposal"
