"""Sprint 23 — product experience, onboarding checklist, empty-workspace dashboard."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from conftest import auth_json

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _clear_rl():
    from dependencies import _rl_store
    _rl_store.clear()


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


def _register(client, company="Sprint23 Co"):
    _clear_rl()
    email = f"s23_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "firstName": "S23",
            "lastName": "User",
            "email": email,
            "password": "Password123!",
            "company": company,
        },
    )
    assert r.status_code == 200, r.text
    return auth_json(client, r)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_new_user_workspace_empty_no_fake_metrics(client):
    data = _register(client)
    assert data["user"].get("onboardingCompleted") is False
    r = client.get("/api/dashboard/executive", headers=_auth(data["accessToken"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("workspace_empty") is True
    hero = body.get("hero") or {}
    assert (hero.get("revenue_at_risk") or 0) == 0


def test_checklist_shape_and_real_progress(client):
    data = _register(client)
    tok = data["accessToken"]
    j = client.get("/api/onboarding/checklist", headers=_auth(tok)).json()
    assert j["total"] == 5 and j["done"] == 1 and j["percent"] == 20
    keys = {i["key"] for i in j["items"]}
    assert keys == {"account", "client", "project", "task", "copilot"}
    assert j.get("dismissed") is False
    assert j.get("title") == "Getting started"

    assert client.post("/api/clients", headers=_auth(tok), json={
        "name": "S23 Client", "contact": "A", "email": "a@a.com",
    }).status_code == 200
    assert client.post("/api/projects", headers=_auth(tok), json={
        "name": "S23 Project", "status": "Active",
    }).status_code == 200

    projects = client.get("/api/projects", headers=_auth(tok)).json()
    items = projects if isinstance(projects, list) else projects.get("items") or projects.get("projects") or []
    if items:
        client.post("/api/tasks", headers=_auth(tok), json={
            "title": "S23 Task", "project_id": items[0]["id"], "priority": "Medium",
        })
    client.post("/api/onboarding/flag", headers=_auth(tok), json={"key": "copilot"})

    j2 = client.get("/api/onboarding/checklist", headers=_auth(tok)).json()
    st = {i["key"]: i["done"] for i in j2["items"]}
    assert st["account"] is True
    assert st["client"] is True
    assert st["project"] is True
    assert st["copilot"] is True
    assert j2["done"] >= 4


def test_checklist_dismiss_persists(client):
    data = _register(client)
    tok = data["accessToken"]
    r = client.post("/api/onboarding/checklist/dismiss", headers=_auth(tok))
    assert r.status_code == 200
    j = client.get("/api/onboarding/checklist", headers=_auth(tok)).json()
    assert j.get("dismissed") is True


def test_skip_onboarding_marks_complete_for_returning_user(client):
    data = _register(client)
    tok = data["accessToken"]
    client.post("/api/onboarding/state", headers=_auth(tok), json={
        "step": 0, "data": {"primaryGoal": "save_time_ai"}, "completed": True,
    })
    client.post("/api/onboarding/complete", headers=_auth(tok))
    st = client.get("/api/onboarding/state", headers=_auth(tok)).json()
    assert st["completed"] is True
    assert (st.get("data") or {}).get("primaryGoal") == "save_time_ai"
    me = client.get("/api/auth/me", headers=_auth(tok)).json()
    assert me.get("onboardingCompleted") is True


def test_checklist_requires_auth(client):
    # TestClient keeps cookies across tests in the session-scoped client
    client.cookies.clear()
    assert client.get("/api/onboarding/checklist").status_code == 401
