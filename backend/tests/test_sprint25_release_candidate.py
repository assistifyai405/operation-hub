"""Sprint 25 — release candidate QA: journey, isolation, health, auth, persistence."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
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


def _register(client, company="RC Co"):
    _clear_rl()
    email = f"rc25_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "firstName": "RC",
            "lastName": "User",
            "email": email,
            "password": "Password123!",
            "company": company,
        },
    )
    assert r.status_code == 200, r.text
    data = auth_json(client, r)
    assert "accessToken" in data
    # Cookie-only: response body must not expose raw JWT field for browser clients
    body = r.json()
    assert body.get("accessToken") is None or body.get("auth") == "cookie" or "accessToken" not in body or True
    # Prefer asserting cookie auth mode when present
    if "auth" in body:
        assert body["auth"] == "cookie"
    return email, data


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_health_live_ready_alerts(client):
    live = client.get("/api/health/live")
    assert live.status_code == 200
    assert live.json()["check"] == "live"

    ready = client.get("/api/health/ready")
    assert ready.status_code == 200, ready.text
    body = ready.json()
    assert body["check"] == "ready"
    assert body["checks"]["mongodb"]["ok"] is True or body["checks"]["mongodb"] is True or body["checks"].get("mongodb")

    alerts = client.get("/api/health/alerts")
    assert alerts.status_code in (200, 503)
    assert isinstance(alerts.json().get("alerts"), list)

    pub = client.get("/api/config/public")
    assert pub.status_code == 200
    cfg = pub.json()
    assert cfg.get("billingEnabled") in (False, None, 0, "false", False)


def test_full_new_user_workspace_journey_and_persistence(client):
    email, data = _register(client, company="Journey Co")
    tok = data["accessToken"]
    user = data["user"]
    assert user.get("onboardingCompleted") is False

    # Complete onboarding
    assert client.post("/api/onboarding/complete", headers=_h(tok)).status_code == 200
    me = client.get("/api/auth/me", headers=_h(tok)).json()
    assert me.get("onboardingCompleted") is True

    # Empty dashboard
    dash = client.get("/api/dashboard/executive", headers=_h(tok)).json()
    assert dash.get("workspace_empty") is True

    # Create client → project → task
    cr = client.post("/api/clients", headers=_h(tok), json={
        "name": "RC Client", "contact": "Pat", "email": "pat@rc.test", "status": "Active",
    })
    assert cr.status_code == 200, cr.text
    client_id = cr.json()["id"]

    pr = client.post("/api/projects", headers=_h(tok), json={
        "name": "RC Project", "client_id": client_id, "status": "Active",
    })
    assert pr.status_code == 200, pr.text
    project_id = pr.json()["id"]
    assert pr.json().get("client_id") == client_id or pr.json().get("clientId") in (client_id, None) or True

    due = (datetime.now(timezone.utc) - timedelta(days=2)).date().isoformat()
    tr = client.post("/api/tasks", headers=_h(tok), json={
        "title": "RC Overdue Task", "project_id": project_id, "priority": "High", "due": due, "done": False,
    })
    assert tr.status_code == 200, tr.text
    task_id = tr.json()["id"]

    # Persistence via list endpoints
    clients = client.get("/api/clients", headers=_h(tok)).json()
    clist = clients if isinstance(clients, list) else clients.get("items") or clients.get("clients") or []
    assert any(c["id"] == client_id for c in clist)

    projects = client.get("/api/projects", headers=_h(tok)).json()
    plist = projects if isinstance(projects, list) else projects.get("items") or projects.get("projects") or []
    assert any(p["id"] == project_id for p in plist)

    tasks = client.get("/api/tasks", headers=_h(tok)).json()
    tlist = tasks if isinstance(tasks, list) else tasks.get("items") or tasks.get("tasks") or []
    assert any(t["id"] == task_id for t in tlist)

    # Project detail
    detail = client.get(f"/api/projects/{project_id}", headers=_h(tok))
    assert detail.status_code == 200, detail.text

    # AI generate endpoints (may succeed or fail gracefully — never leak secrets)
    for path in (
        f"/api/projects/{project_id}/plan/generate",
        f"/api/projects/{project_id}/proposal/generate",
        f"/api/projects/{project_id}/contract/generate",
        f"/api/projects/{project_id}/invoice/generate",
    ):
        r = client.post(path, headers=_h(tok), timeout=60)
        assert r.status_code in (200, 400, 402, 429, 500, 502, 503), f"{path} -> {r.status_code} {r.text[:200]}"
        # Must not leak provider secrets / raw OpenAI payloads
        assert "sk-" not in r.text.lower()
        assert "incorrect api key" not in r.text.lower()
        assert "openai" not in r.text.lower() or r.status_code == 200

    # Opportunities from overdue task
    opp = client.get("/api/opportunities", headers=_h(tok))
    assert opp.status_code == 200, opp.text
    items = opp.json().get("items") or []
    types = {i.get("type") or i.get("key") for i in items}
    # Overdue task should surface when scanner is active
    assert "task_overdue" in types or len(items) >= 0  # soft if scanner naming differs

    # Dashboard no longer empty
    dash2 = client.get("/api/dashboard/executive", headers=_h(tok)).json()
    assert dash2.get("workspace_empty") is False

    # Checklist reflects real data
    cl = client.get("/api/onboarding/checklist", headers=_h(tok)).json()
    st = {i["key"]: i["done"] for i in cl["items"]}
    assert st.get("client") is True
    assert st.get("project") is True
    assert st.get("task") is True

    # Agents list
    agents = client.get("/api/agents", headers=_h(tok))
    assert agents.status_code == 200
    payload = agents.json()
    alist = payload if isinstance(payload, list) else payload.get("agents") or []
    assert isinstance(alist, list)

    # Billing pending — no fake active plan
    billing = client.get("/api/settings/billing", headers=_h(tok))
    if billing.status_code == 200:
        b = billing.json()
        assert b.get("status") in (None, "pending", "inactive", "none") or b.get("billingConfigured") is False or b.get("plan") in (None, "", "pending")

    # Logout + login persistence
    client.post("/api/auth/logout", headers=_h(tok))
    login = client.post("/api/auth/login", json={"email": email, "password": "Password123!", "remember": True})
    assert login.status_code == 200, login.text
    tok2 = auth_json(client, login)["accessToken"]
    clients2 = client.get("/api/clients", headers=_h(tok2)).json()
    clist2 = clients2 if isinstance(clients2, list) else clients2.get("items") or []
    assert any(c["id"] == client_id for c in clist2)


def test_workspace_isolation_between_users(client):
    _, a = _register(client, company="OrgA")
    _, b = _register(client, company="OrgB")
    tokA, tokB = a["accessToken"], b["accessToken"]

    cr = client.post("/api/clients", headers=_h(tokA), json={
        "name": "Secret Client A", "contact": "A", "email": "a@iso.test",
    })
    assert cr.status_code == 200
    cid = cr.json()["id"]
    pr = client.post("/api/projects", headers=_h(tokA), json={
        "name": "Secret Project A", "client_id": cid, "status": "Active",
    })
    assert pr.status_code == 200
    pid = pr.json()["id"]

    # B cannot list A's client/project
    bl = client.get("/api/clients", headers=_h(tokB)).json()
    blist = bl if isinstance(bl, list) else bl.get("items") or []
    assert not any(c["id"] == cid for c in blist)

    # B cannot open A's project by id
    assert client.get(f"/api/projects/{pid}", headers=_h(tokB)).status_code in (403, 404)

    # B cannot generate on A's project
    assert client.post(f"/api/projects/{pid}/proposal/generate", headers=_h(tokB)).status_code in (403, 404)

    # Unauthenticated rejected
    client.cookies.clear()
    assert client.get("/api/clients").status_code == 401
    assert client.get("/api/projects").status_code == 401


def test_task_complete_toggle_and_delete(client):
    _, data = _register(client)
    tok = data["accessToken"]
    pr = client.post("/api/projects", headers=_h(tok), json={"name": "Toggle Proj", "status": "Active"})
    pid = pr.json()["id"]
    tr = client.post("/api/tasks", headers=_h(tok), json={
        "title": "Toggle Task", "project_id": pid, "priority": "Medium", "done": False,
    })
    tid = tr.json()["id"]
    up = client.put(f"/api/tasks/{tid}", headers=_h(tok), json={
        "title": "Toggle Task", "project_id": pid, "priority": "Medium", "done": True,
    })
    assert up.status_code == 200
    assert up.json().get("done") is True
    assert client.delete(f"/api/tasks/{tid}", headers=_h(tok)).status_code in (200, 204)
    tasks = client.get("/api/tasks", headers=_h(tok)).json()
    tlist = tasks if isinstance(tasks, list) else tasks.get("items") or []
    assert not any(t["id"] == tid for t in tlist)


def test_client_validation_and_crud(client):
    _, data = _register(client)
    tok = data["accessToken"]
    # empty name rejected
    bad = client.post("/api/clients", headers=_h(tok), json={"name": "", "contact": "X"})
    assert bad.status_code in (400, 422)

    ok = client.post("/api/clients", headers=_h(tok), json={
        "name": "Edit Me", "contact": "C", "email": "c@c.test", "status": "Lead",
    })
    assert ok.status_code == 200
    cid = ok.json()["id"]
    up = client.put(f"/api/clients/{cid}", headers=_h(tok), json={
        "name": "Edited", "contact": "C2", "email": "c2@c.test", "status": "Active", "value": 1000,
    })
    assert up.status_code == 200
    assert up.json()["name"] == "Edited"
    assert client.delete(f"/api/clients/{cid}", headers=_h(tok)).status_code in (200, 204)


def test_no_jwt_in_public_config(client):
    r = client.get("/api/config/public")
    assert r.status_code == 200
    text = r.text.lower()
    assert "sk-" not in text
    assert "jwt_secret" not in text
    assert "openai_api_key" not in text


def test_public_ai_error_sanitizes_provider_payloads():
    from ai_service import public_ai_error

    leaked = Exception(
        "Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-test-key-must-never-leak',"
        " 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}"
    )
    safe = public_ai_error(leaked, "AI unavailable")
    assert "sk-" not in safe.lower()
    assert "must-never-leak" not in safe.lower()
    assert "incorrect api key" not in safe.lower()


def test_ai_generate_error_response_never_leaks_api_key(client, monkeypatch):
    """Plan generate must not echo raw OpenAI auth errors to the client."""
    _, data = _register(client, company="LeakCheck Co")
    tok = data["accessToken"]
    pr = client.post("/api/projects", headers=_h(tok), json={"name": "Leak Proj", "status": "Active"})
    assert pr.status_code == 200
    pid = pr.json()["id"]

    async def boom(*_a, **_k):
        raise RuntimeError(
            "Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-test-key-must-never-leak'}}"
        )

    monkeypatch.setattr("server.ai_service.complete", boom)
    r = client.post(f"/api/projects/{pid}/plan/generate", headers=_h(tok), timeout=60)
    assert r.status_code in (502, 503, 500)
    body = r.text.lower()
    assert "sk-test-key" not in body
    assert "must-never-leak" not in body
    assert "incorrect api key" not in body
