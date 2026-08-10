"""Sprint 19A — dashboard empty states + opportunities from real workspace data."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


def _clear_rl():
    from dependencies import _rl_store
    _rl_store.clear()


def _register(client, company="Real Co"):
    _clear_rl()
    email = f"s19a_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "firstName": "Alex",
            "lastName": "Owner",
            "email": email,
            "password": "Password123!",
            "company": company,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_empty_workspace_executive_has_no_fake_kpis(client):
    data = _register(client)
    r = client.get("/api/dashboard/executive", headers=_auth(data["accessToken"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("workspace_empty") is True
    assert body["kpi_cards"]["health"]["value"] is None
    assert body["kpi_cards"]["pipeline"]["value"] is None
    assert body["kpi_cards"]["revenue_month"]["value"] is None
    assert body["hero"]["ai_confidence"] is None
    assert body["priorities_total"] == 0
    assert "Demo" not in (body["hero"].get("greeting") or "")


def test_empty_workspace_health_score(client):
    data = _register(client)
    r = client.get("/api/opportunities/health", headers=_auth(data["accessToken"]))
    assert r.status_code == 200
    body = r.json()
    assert body.get("has_workspace_data") is False
    assert body.get("score") is None


def test_opportunities_include_overdue_task_and_stale_deal(client):
    data = _register(client)
    token = data["accessToken"]
    org = data["user"]["organizationId"]
    headers = _auth(token)

    c = client.post("/api/clients", headers=headers, json={
        "name": "Acme Real", "contact": "Pat", "email": "pat@acme.test", "value": 1000, "status": "Active",
    })
    assert c.status_code == 200, c.text
    client_id = c.json()["id"]

    p = client.post("/api/projects", headers=headers, json={
        "name": "Website", "client_id": client_id, "status": "In Progress", "progress": 10,
        "due": "", "members": 1, "description": "", "notes": "",
    })
    assert p.status_code == 200, p.text
    project_id = p.json()["id"]

    yesterday = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
    t = client.post("/api/tasks", headers=headers, json={
        "title": "Send kickoff notes", "project_id": project_id, "priority": "High",
        "due": yesterday, "done": False,
    })
    assert t.status_code == 200, t.text

    lead = client.post("/api/crm/leads", headers=headers, json={
        "title": "Enterprise expansion",
        "client_id": client_id,
        "project_id": project_id,
        "stage": "Proposal Sent",
        "value": 25000,
        "expected_close": "",
        "owner": "Alex",
        "source": "Inbound",
        "tags": [],
        "notes": "",
        "probability": 50,
    })
    assert lead.status_code == 200, lead.text
    lead_id = lead.json()["id"]

    # Backdate stage change so the deal is considered stale (>=14 days)
    old = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    import pymongo
    mongo = pymongo.MongoClient("mongodb://127.0.0.1:27017")
    mongo["assistify_test"].leads.update_one(
        {"id": lead_id, "organizationId": org},
        {"$set": {"stage_changed_at": old, "updated_at": old, "created_at": old}},
    )

    r = client.get("/api/opportunities", headers=headers)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    types = {i["type"] for i in items}
    assert "task_overdue" in types
    assert "deal_stale" in types
    titles = " ".join(i["title"] for i in items)
    assert "Northwind" not in titles
    assert "Send kickoff notes" in titles
    assert "Enterprise expansion" in titles


def test_authenticated_greeting_uses_real_user_name_not_demo(client):
    data = _register(client, company="Alex Studio")
    assert data["user"]["firstName"] == "Alex"
    assert data["user"].get("isDemo") in (None, False)
    me = client.get("/api/auth/me", headers=_auth(data["accessToken"]))
    assert me.status_code == 200
    assert me.json()["firstName"] == "Alex"
    assert me.json()["firstName"] != "Demo"


def test_morning_brief_handles_null_health_score(client):
    data = _register(client)
    r = client.get("/api/dashboard/morning-brief", headers=_auth(data["accessToken"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("workspace_empty") is True
    assert body["numbers"]["business_health"] is None
    assert body["numbers"]["revenue"] is None
    assert body["numbers"]["pipeline"] is None
    assert not any("health is strong" in (w.get("title") or "").lower() for w in body.get("wins", []))
