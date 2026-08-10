"""Sprint 19B — launch hardening: demo gates, public config, smoke flows, agents."""

from __future__ import annotations

import os
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


def _register(client, company="Launch Co"):
    _clear_rl()
    email = f"s19b_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "firstName": "Sam",
            "lastName": "Owner",
            "email": email,
            "password": "Password123!",
            "company": company,
        },
    )
    assert r.status_code == 200, r.text
    return auth_json(client, r)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---- Demo / public config ----
def test_demo_login_disabled_by_default(client):
    r = client.post("/api/auth/demo")
    assert r.status_code == 404
    assert "disabled" in (r.json().get("detail") or "").lower()


def test_public_config_exposes_flags_without_secrets(client):
    r = client.get("/api/config/public")
    assert r.status_code == 200
    body = r.json()
    assert body["demoLoginEnabled"] is False
    assert body["demoSeedEnabled"] is False
    assert body["billingEnabled"] is False
    assert "jwt" not in str(body).lower()
    assert "password" not in str(body).lower()
    assert "secret" not in str(body).lower()


def test_onboarding_seed_demo_disabled_by_default(client):
    data = _register(client)
    r = client.post("/api/onboarding/seed-demo", headers=_auth(data["accessToken"]))
    assert r.status_code == 404


def test_production_rejects_weak_demo_password():
    from config import ConfigError, load_settings, reset_settings_for_tests

    reset_settings_for_tests()
    env = {
        "ENVIRONMENT": "production",
        "MONGO_URL": "mongodb://127.0.0.1:27017",
        "DB_NAME": "assistify_test",
        "JWT_SECRET": "a" * 40,
        "CORS_ORIGINS": "https://app.example.com",
        "FRONTEND_URL": "https://app.example.com",
        "AI_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test",
        "STORAGE_PROVIDER": "local",
        "INTEGRATION_ENCRYPTION_KEY": "x" * 44,
        "ALLOW_DEMO_IN_PRODUCTION": "true",
        "ENABLE_DEMO_SEED": "true",
        "DEMO_PASSWORD": "change-me-demo-password",
        "EMAIL_PROVIDER": "console",
        "EMAIL_SENDING_ENABLED": "false",
        "WORKER_ENABLED": "false",
        "SCHEDULER_ENABLED": "false",
        "REQUIRE_REDIS": "false",
    }
    old = {k: os.environ.get(k) for k in env}
    try:
        os.environ.update(env)
        with pytest.raises(ConfigError, match="DEMO_PASSWORD"):
            load_settings(strict=True)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        reset_settings_for_tests()
        # Restore shared test settings for any later tests in this process
        import conftest as cf
        cf.ensure_test_settings()


# ---- Health ----
def test_health_live_and_ready(client):
    live = client.get("/api/health/live")
    assert live.status_code == 200
    ready = client.get("/api/health/ready")
    assert ready.status_code in (200, 503)
    body = ready.json()
    assert "status" in body
    assert "checks" in body
    assert "mongodb" in body["checks"]
    assert body["checks"]["mongodb"].get("ok") is True


# ---- Smoke: auth + core CRUD + agents + key pages APIs ----
def test_smoke_core_workspace_flows(client):
    data = _register(client, company="Smoke Studio")
    token = data["accessToken"]
    headers = _auth(token)

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["firstName"] == "Sam"

    exec_r = client.get("/api/dashboard/executive", headers=headers)
    assert exec_r.status_code == 200
    assert exec_r.json().get("workspace_empty") is True

    opps = client.get("/api/opportunities", headers=headers)
    assert opps.status_code == 200
    assert isinstance(opps.json().get("items"), list)

    # Clients CRUD
    c = client.post("/api/clients", headers=headers, json={
        "name": "Smoke Client", "contact": "Pat", "email": "pat@smoke.test",
        "value": 5000, "status": "Active",
    })
    assert c.status_code == 200, c.text
    client_id = c.json()["id"]
    assert client.get("/api/clients", headers=headers).status_code == 200
    assert client.put(f"/api/clients/{client_id}", headers=headers, json={
        "name": "Smoke Client LLC", "contact": "Pat", "email": "pat@smoke.test",
        "value": 6000, "status": "Active",
    }).status_code == 200

    # Projects CRUD
    p = client.post("/api/projects", headers=headers, json={
        "name": "Smoke Project", "client_id": client_id, "status": "In Progress",
        "progress": 0, "due": "2026-12-31", "members": 1, "description": "t", "notes": "",
    })
    assert p.status_code == 200, p.text
    project_id = p.json()["id"]
    assert client.get("/api/projects", headers=headers).status_code == 200
    assert client.get(f"/api/projects/{project_id}", headers=headers).status_code == 200

    # Tasks CRUD
    t = client.post("/api/tasks", headers=headers, json={
        "title": "Smoke task", "project_id": project_id, "priority": "Medium",
        "due": "2026-12-01", "done": False,
    })
    assert t.status_code == 200, t.text
    task_id = t.json()["id"]
    assert client.get("/api/tasks", headers=headers).status_code == 200
    assert client.put(f"/api/tasks/{task_id}", headers=headers, json={
        "title": "Smoke task done", "project_id": project_id, "priority": "Medium",
        "due": "2026-12-01", "done": True,
    }).status_code == 200

    # AI Agents
    agents = client.get("/api/agents", headers=headers)
    assert agents.status_code == 200
    assert isinstance(agents.json(), list)
    assert len(agents.json()) >= 1

    # Copilot / workspace / knowledge / docs / analytics / settings / integrations
    for path in (
        "/api/copilot/suggestions",
        "/api/memory/stats",
        "/api/memory/memories",
        "/api/documents",
        "/api/analytics",
        "/api/settings",
        "/api/settings/billing",
        "/api/integrations",
        "/api/ai/workspace/stats",
        "/api/library/proposals",
        "/api/crm/sales-metrics",
        "/api/automation/summary",
    ):
        r = client.get(path, headers=headers)
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:300]}"

    billing = client.get("/api/settings/billing", headers=headers).json()
    assert isinstance(billing, dict)
    assert billing.get("status") == "pending"
    assert billing.get("billingConfigured") is False
    assert billing.get("plan") is None
    assert "active" != (billing.get("status") or "").lower()

    # Cleanup deletes
    assert client.delete(f"/api/tasks/{task_id}", headers=headers).status_code in (200, 204)
    assert client.delete(f"/api/projects/{project_id}", headers=headers).status_code in (200, 204)
    assert client.delete(f"/api/clients/{client_id}", headers=headers).status_code in (200, 204)

    # Logout + login again
    assert client.post("/api/auth/logout", headers=headers).status_code in (200, 204)
    login = client.post("/api/auth/login", json={
        "email": data["user"]["email"], "password": "Password123!", "remember": True,
    })
    assert login.status_code == 200, login.text
    assert auth_json(client, login).get("accessToken")
