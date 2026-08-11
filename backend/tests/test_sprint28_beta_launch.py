"""Sprint 28 — closed beta launch: beta mode, feedback, AI daily limit, security."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from conftest import auth_json, ensure_test_settings, clear_rate_limits

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(api_client):
    c, _ = api_client
    ensure_test_settings()
    clear_rate_limits()
    # Enable beta mode for this module
    os.environ["BETA_MODE"] = "true"
    os.environ["AI_DAILY_REQUEST_LIMIT"] = "5"
    ensure_test_settings()
    yield c
    os.environ.pop("BETA_MODE", None)
    os.environ["AI_DAILY_REQUEST_LIMIT"] = "200"
    ensure_test_settings()
    clear_rate_limits()
    try:
        from ai_usage import clear_ai_usage_memory
        clear_ai_usage_memory()
    except Exception:
        pass


def _register(client, suffix="s28"):
    import uuid
    email = f"s28_{suffix}_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password123!",
        "firstName": "Beta",
        "lastName": "User",
        "company": "Beta Co",
    })
    assert r.status_code in (200, 201), r.text
    data = auth_json(client, r)
    tok = data.get("accessToken") or client.cookies.get("access_token")
    assert tok, "missing access token after register"
    return {"Authorization": f"Bearer {tok}"}, email


# ---- Public config / beta flag ----
def test_public_config_exposes_beta_mode_without_secrets(client):
    r = client.get("/api/config/public")
    assert r.status_code == 200
    data = r.json()
    assert "betaMode" in data
    assert data["betaMode"] is True
    assert data.get("billingEnabled") is False
    blob = r.text.lower()
    assert "sk-" not in blob
    assert "jwt_secret" not in blob
    assert "openai" not in blob or "openai_api_key" not in blob
    legal = data.get("legal") or {}
    assert legal.get("placeholders") is True or legal.get("companyName") in (None, "")


def test_demo_login_still_disabled(client):
    r = client.get("/api/config/public")
    assert r.json().get("demoLoginEnabled") is False
    demo = client.post("/api/auth/demo")
    assert demo.status_code in (403, 404, 401, 400, 429)


# ---- Feedback ----
def test_submit_and_list_beta_feedback(client):
    headers, email = _register(client, "fb")
    r = client.post("/api/feedback", headers=headers, json={
        "category": "Idea",
        "message": "Please add a dark mode toggle for print exports.",
        "page": "/dashboard",
        "context": "Dashboard",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["category"] == "Idea"
    assert body["organizationId"]
    assert "sk-" not in r.text

    listed = client.get("/api/feedback", headers=headers)
    assert listed.status_code == 200
    items = listed.json()["feedback"]
    assert any(i["id"] == body["id"] for i in items)
    assert listed.json()["total"] >= 1


def test_feedback_requires_auth(client):
    r = client.post("/api/feedback", json={"category": "Bug", "message": "broken button somewhere"})
    # Unauthenticated write may be 401 (auth) or 403 (CSRF before auth) — both deny access.
    assert r.status_code in (401, 403)


def test_feedback_isolation_across_orgs(client):
    h1, _ = _register(client, "iso1")
    h2, _ = _register(client, "iso2")
    r = client.post("/api/feedback", headers=h1, json={
        "category": "Bug", "message": "Org1 only secret feedback note", "page": "/tasks",
    })
    assert r.status_code == 200
    fid = r.json()["id"]
    other = client.get("/api/feedback", headers=h2)
    assert other.status_code == 200
    ids = [i["id"] for i in other.json()["feedback"]]
    assert fid not in ids


# ---- AI daily limit ----
def test_ai_daily_limit_returns_429(client):
    headers, _ = _register(client, "ailimit")
    from ai_usage import clear_ai_usage_memory, enforce_ai_daily_limit, get_ai_usage, bind_ai_org
    from fastapi import HTTPException
    import anyio

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    org = me.json()["organizationId"]

    os.environ["AI_DAILY_REQUEST_LIMIT"] = "2"
    ensure_test_settings()
    clear_ai_usage_memory()
    bind_ai_org(org)

    async def run():
        await enforce_ai_daily_limit(org)
        await enforce_ai_daily_limit(org)
        try:
            await enforce_ai_daily_limit(org)
            return None
        except HTTPException as e:
            return e

    exc = anyio.from_thread.run(run) if False else None
    # Prefer asyncio.run in a fresh loop (TestClient uses its own)
    import asyncio

    try:
        loop = asyncio.new_event_loop()
        exc = loop.run_until_complete(run())
    finally:
        loop.close()

    assert exc is not None
    assert exc.status_code == 429
    detail = exc.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "ai_daily_limit"
    assert "Daily AI" in detail.get("message", "")

    try:
        loop = asyncio.new_event_loop()
        usage = loop.run_until_complete(get_ai_usage(org))
    finally:
        loop.close()
    assert usage["used"] == 2
    assert usage["limit"] == 2

def test_ops_status_includes_beta_ai_feedback(client):
    headers, _ = _register(client, "ops")
    client.post("/api/feedback", headers=headers, json={
        "category": "Other", "message": "Ops visibility check message",
    })
    r = client.get("/api/ops/status", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "aiUsage" in data
    assert "betaFeedbackCount" in data
    assert data["betaFeedbackCount"] >= 1
    assert "aiDailyLimit" in data
    assert "workspaceUserCount" in data
    assert data.get("betaMode") is True
    blob = r.text.lower()
    assert "sk-" not in blob


def test_billing_message_beta(client):
    headers, _ = _register(client, "bill")
    r = client.get("/api/settings/billing", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data.get("billingConfigured") is False
    assert data.get("plan") is None
    assert "not available during beta" in (data.get("message") or "").lower()


def test_invite_reports_manual_email_delivery(client):
    headers, _ = _register(client, "inv")
    r = client.post("/api/team/invitations", headers=headers, json={
        "email": f"colleague_{os.urandom(3).hex()}@example.com",
        "role": "member",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("emailDelivery") == "manual"
    assert "emailDeliveryNote" in data
    assert data.get("invitationLink")  # console/dev


def test_health_score_empty_categories_not_fake_100(client):
    headers, _ = _register(client, "health")
    # Create only a client — invoices/contracts categories should not score as 100
    cr = client.post("/api/clients", headers=headers, json={"name": "Only Client", "email": "only@example.com"})
    assert cr.status_code in (200, 201), cr.text
    h = client.get("/api/opportunities/health", headers=headers)
    assert h.status_code == 200
    data = h.json()
    names = [c["name"] for c in data.get("categories") or []]
    assert "Invoices" not in names
    assert "Contracts" not in names


def test_docs_exist():
    for rel in (
        "docs/CLOSED_BETA_RUNBOOK.md",
        "docs/CLOSED_BETA_CHECKLIST.md",
        "docs/KVK_READINESS_CHECKLIST.md",
        "docs/KVK_LAUNCH_INFO.md",
    ):
        p = ROOT / rel
        assert p.is_file(), rel
        text = p.read_text(encoding="utf-8")
        assert len(text) > 100
