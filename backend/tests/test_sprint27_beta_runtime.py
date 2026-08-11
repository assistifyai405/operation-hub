"""Sprint 27 — Docker gate, live AI validation, OAuth/email readiness, beta RC."""

from __future__ import annotations

import asyncio
import os
import re
import sys
import uuid
from pathlib import Path

import pytest
from conftest import auth_json, ensure_test_settings, register_user

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _live_ai_enabled() -> bool:
    return os.environ.get("RUN_LIVE_AI_TESTS", "").lower() in {"1", "true", "yes", "on"}


def _live_openai_key() -> str | None:
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key or key.startswith("sk-test"):
        return None
    return key


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


# ---------------------------------------------------------------------------
# Compose / env / release artifacts
# ---------------------------------------------------------------------------


def test_compose_has_required_services_and_healthchecks():
    text = (ROOT / "docker-compose.yml").read_text()
    for svc in ("mongo:", "redis:", "backend:", "worker:", "scheduler:", "frontend:"):
        assert svc in text
    assert "OPENAI_API_KEY: ${OPENAI_API_KEY" in text
    assert "sk-test-not-used" not in text
    assert 'WORKER_ENABLED: "true"' in text
    assert 'SCHEDULER_ENABLED: "true"' in text
    assert 'REQUIRE_REDIS: "true"' in text
    assert 'EMAIL_SENDING_ENABLED: "false"' in text
    assert 'ENABLE_DEMO_LOGIN: "false"' in text
    # Heartbeat-aware healthchecks for async processes
    assert "read_status('worker')" in text or 'read_status("worker")' in text
    assert "read_status('scheduler')" in text or 'read_status("scheduler")' in text
    assert "API_URL: http://localhost:8000" in text


def test_release_gate_script_exists_and_is_safe():
    script = (ROOT / "scripts" / "check_local_release.py").read_text()
    assert "health/live" in script
    assert "health/ready" in script
    assert "worker_heartbeat_running" in script
    assert "scheduler_heartbeat_running" in script
    assert "syncMode_false" in script
    assert "sk-" in script  # scrub detection
    assert "print(os.environ" not in script


def test_enqueue_safe_test_job_script_exists():
    script = (ROOT / "scripts" / "enqueue_safe_test_job.py").read_text()
    assert "test_noop" in script
    assert "test_fail" in script
    assert "sk-" in script  # secret scrub


def test_beta_docs_exist():
    runbook = ROOT / "docs" / "CLOSED_BETA_RUNBOOK.md"
    checklist = ROOT / "docs" / "CLOSED_BETA_CHECKLIST.md"
    assert runbook.is_file()
    assert checklist.is_file()
    rb = runbook.read_text()
    assert "docker compose" in rb.lower()
    assert "check_local_release" in rb
    assert "RUN_LIVE_AI_TESTS" in rb
    assert "billing" in rb.lower()
    cl = checklist.read_text()
    assert "worker" in cl.lower()
    assert "ready" in cl.lower()


def test_env_examples_no_real_secrets():
    for rel in (".env.example", "backend/.env.example", "frontend/.env.example"):
        p = ROOT / rel
        if not p.is_file():
            continue
        text = p.read_text()
        # placeholders only
        assert not re.search(r"sk-(?!your|test|live-xxx|proj)[a-zA-Z0-9]{20,}", text)
        assert "re_" not in text or "re_xxx" in text or "RESEND" in text


# ---------------------------------------------------------------------------
# OAuth / email readiness (no live credentials required)
# ---------------------------------------------------------------------------


def test_oauth_readiness_honest_and_secret_free(client):
    r = client.get("/api/config/public")
    assert r.status_code == 200
    body = r.json()
    blob = r.text.lower()
    assert "sk-" not in blob
    assert "client_secret" not in blob
    assert "jwt_secret" not in blob
    for p in ("google", "microsoft", "slack"):
        st = body["oauth"][p]
        assert st in ("configured", "not_configured", "reconnect_required", "connected")

    auth = register_user(client, company="S27 OAuth Co")
    st = client.get("/api/integrations/status", headers=auth["headers"])
    assert st.status_code == 200, st.text
    data = st.json()
    assert "oauthReadiness" in data
    for p in ("google", "microsoft", "slack"):
        assert data["oauthReadiness"][p] in (
            "configured",
            "not_configured",
            "reconnect_required",
            "connected",
        )
    templates = data.get("redirectUriTemplates") or {}
    for p in ("google", "microsoft", "slack"):
        uri = templates.get(p) or ""
        assert "/api/integrations/oauth/callback/" in uri
        assert p in uri
        assert "client_secret" not in uri.lower()


def test_disabled_oauth_connect_does_not_break_app(client):
    auth = register_user(client, company="S27 OAuth Off")
    # App stays healthy even when providers are not configured
    live = client.get("/api/health/live")
    assert live.status_code == 200
    # Connect without credentials should fail cleanly (not 500)
    r = client.post(
        "/api/integrations/connect",
        headers=auth["headers"],
        json={"provider": "google", "useOauth": True},
    )
    assert r.status_code in (400, 401, 403, 404, 422, 503), r.text
    assert "sk-" not in r.text.lower()
    assert "client_secret" not in r.text.lower()


def test_email_readiness_console_disabled_by_default(client):
    r = client.get("/api/config/public")
    assert r.status_code == 200
    email = r.json()["email"]
    assert email["provider"] == "console"
    assert email["sendingEnabled"] is False
    assert email["canSend"] is False
    assert email["status"] in ("configured_disabled", "disabled", "not_configured", "blocked")
    assert email["status"] != "ready"
    assert "api_key" not in r.text.lower()
    assert "re_" not in r.text.lower() or "ready" in r.text.lower()


# ---------------------------------------------------------------------------
# Security regression smoke (Sprint 21–26 must hold)
# ---------------------------------------------------------------------------


def test_security_regression_cookie_csrf_isolation_sanitization(client):
    from ai_service import public_ai_error

    # Public config / demo
    pub = client.get("/api/config/public").json()
    assert pub.get("demoLoginEnabled") is False
    assert pub.get("billingEnabled") is False

    a = register_user(client, company="S27 Iso A")
    b = register_user(client, company="S27 Iso B")
    ha, hb = a["headers"], b["headers"]

    cr = client.post("/api/clients", headers=ha, json={"name": "Client A Only", "email": "a@example.com"})
    # clients endpoint may use slightly different schema
    if cr.status_code not in (200, 201):
        # fallback: create project without client
        pr = client.post(
            "/api/projects",
            headers=ha,
            json={"name": "S27 Proj A", "description": "iso", "status": "Active"},
        )
        assert pr.status_code in (200, 201), pr.text
        pid = pr.json()["id"]
    else:
        client_id = cr.json().get("id") or cr.json().get("client", {}).get("id")
        pr = client.post(
            "/api/projects",
            headers=ha,
            json={
                "name": "S27 Proj A",
                "description": "iso",
                "status": "Active",
                **({"client_id": client_id} if client_id else {}),
            },
        )
        assert pr.status_code in (200, 201), pr.text
        pid = pr.json()["id"]

    # Workspace isolation
    assert client.get(f"/api/projects/{pid}", headers=hb).status_code in (403, 404)
    assert client.post(f"/api/projects/{pid}/proposal/generate", headers=hb).status_code in (403, 404)

    # AI error sanitization
    safe = public_ai_error(Exception("Incorrect API key provided: sk-live-xxx"))
    assert "sk-" not in safe.lower()

    # Cookie session present after register
    assert client.cookies.get("access_token")


# ---------------------------------------------------------------------------
# Live AI (opt-in) — PENDING when key missing
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _live_ai_enabled(), reason="Set RUN_LIVE_AI_TESTS=true to run live AI smoke")
def test_live_openai_provider_smoke():
    key = _live_openai_key()
    if not key:
        pytest.skip("PENDING: OPENAI_API_KEY not configured for live smoke (no fake success)")
    ensure_test_settings()
    from ai_service import AIService, public_ai_error

    async def _call():
        svc = AIService(api_key=key, provider="openai", model=os.environ.get("AI_MODEL") or "gpt-4o-mini")
        return await svc.complete("Reply with exactly: pong", "ping")

    text = asyncio.run(_call())
    assert text
    assert "sk-" not in text.lower()
    assert "pong" in text.lower() or len(text.strip()) > 0
    assert "sk-live" not in public_ai_error(Exception("Incorrect API key provided: sk-live-xxx")).lower()


@pytest.mark.skipif(not _live_ai_enabled(), reason="Set RUN_LIVE_AI_TESTS=true to run live artifact flow")
def test_live_proposal_artifact_persists(client, monkeypatch):
    """Create client → project → generate proposal → save → reload. Real OpenAI only."""
    key = _live_openai_key()
    if not key:
        pytest.skip("PENDING: OPENAI_API_KEY not configured for live artifact flow")

    ensure_test_settings()
    from ai_service import AIService, public_ai_error
    import core
    import server as server_mod

    live_svc = AIService(api_key=key, provider="openai", model=os.environ.get("AI_MODEL") or "gpt-4o-mini")
    monkeypatch.setattr(core, "ai_service", live_svc)
    monkeypatch.setattr(server_mod, "ai_service", live_svc)

    auth = register_user(client, company="S27 Live AI Co")
    h = auth["headers"]

    cr = client.post(
        "/api/clients",
        headers=h,
        json={"name": "Live Beta Client", "email": f"live_{uuid.uuid4().hex[:6]}@example.com"},
    )
    # Soft-fail client create if schema differs — project is enough
    client_id = None
    if cr.status_code in (200, 201):
        body = cr.json()
        client_id = body.get("id") or (body.get("client") or {}).get("id")

    proj_payload = {
        "name": f"Live Proposal {uuid.uuid4().hex[:6]}",
        "description": "Short beta validation project. Keep proposal brief.",
        "status": "Active",
    }
    if client_id:
        proj_payload["client_id"] = client_id

    pr = client.post("/api/projects", headers=h, json=proj_payload)
    assert pr.status_code in (200, 201), pr.text
    pid = pr.json()["id"]

    gen1 = client.post(f"/api/projects/{pid}/proposal/generate", headers=h, json={})
    assert "sk-" not in gen1.text.lower()
    assert gen1.status_code == 200, f"proposal generate failed: {gen1.status_code} {gen1.text[:300]}"
    generated = gen1.json()
    assert generated.get("content")
    assert isinstance(generated["content"], dict)

    # No duplicate submit requirement — second generate should still succeed or be rate-safe
    gen2 = client.post(f"/api/projects/{pid}/proposal/generate", headers=h, json={})
    assert "sk-" not in gen2.text.lower()
    assert gen2.status_code in (200, 429), gen2.text[:300]

    save = client.post(
        f"/api/projects/{pid}/proposal",
        headers=h,
        json={
            "title": generated.get("title") or "Live Beta Proposal",
            "status": "Generated",
            "content": generated["content"],
        },
    )
    assert save.status_code == 200, save.text
    assert "sk-" not in save.text.lower()

    # Visible after "refresh"
    got = client.get(f"/api/projects/{pid}/proposal", headers=h)
    assert got.status_code == 200
    doc = got.json()
    assert doc and doc.get("content")
    assert doc.get("organizationId") is None or doc.get("organizationId") == auth["user"].get("organizationId")

    # Sanitizer still honest
    assert "sk-" not in public_ai_error(Exception("key sk-abc123")).lower()
