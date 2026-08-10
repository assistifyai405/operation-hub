"""Sprint 22 — staging readiness: env validator, public status, cookies, alerts delivery."""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path
from unittest import mock

import pytest

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conftest import ensure_test_settings


@pytest.fixture
def client(api_client):
    c, _ = api_client
    c.cookies.clear()
    return c


def test_validate_staging_env_script_statuses_only():
    from scripts.validate_staging_env import validate

    env = {
        "JWT_SECRET": "production-grade-secret-key-32chars-min!!",
        "INTEGRATION_ENCRYPTION_KEY": "x" * 44,
        "MONGO_URL": "mongodb+srv://user:pass@cluster/db",
        "DB_NAME": "assistify_staging",
        "FRONTEND_URL": "https://staging.example.com",
        "API_URL": "https://api.staging.example.com",
        "CORS_ORIGINS": "https://staging.example.com",
        "REDIS_URL": "rediss://:pass@redis.example.com:6379/0",
        "REQUIRE_REDIS": "true",
        "WORKER_ENABLED": "true",
        "SCHEDULER_ENABLED": "true",
        "AI_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test-not-printed",
        "ENABLE_DEMO_LOGIN": "false",
        "ENABLE_DEMO_SEED": "false",
        "ALLOW_DEMO_IN_PRODUCTION": "false",
        "REACT_APP_BILLING_ENABLED": "false",
        "EMAIL_PROVIDER": "resend",
        "EMAIL_SENDING_ENABLED": "false",
        "RESEND_API_KEY": "re_test",
        "FROM_EMAIL": "staging@example.com",
        "GOOGLE_CLIENT_ID": "",
        "GOOGLE_CLIENT_SECRET": "",
        "ALERT_DELIVERY_ENABLED": "false",
    }
    with mock.patch.dict(os.environ, env, clear=False):
        rows = validate()
    by = {r["name"]: r for r in rows}
    assert by["JWT_SECRET"]["status"] == "OK"
    assert by["FRONTEND_URL"]["status"] == "OK"
    assert by["ENABLE_DEMO_LOGIN"]["status"] == "DISABLED"
    assert by["REACT_APP_BILLING_ENABLED"]["status"] == "DISABLED"
    assert by["EMAIL_SENDING_ENABLED"]["status"] == "DISABLED"
    assert by["GOOGLE_OAUTH"]["status"] == "DISABLED"
    blob = " ".join(f"{r['name']} {r['status']} {r['note']}" for r in rows)
    assert "sk-test-not-printed" not in blob
    assert "re_test" not in blob
    assert "user:pass" not in blob


def test_validate_staging_env_rejects_localhost_frontend():
    from scripts.validate_staging_env import validate

    env = {
        "JWT_SECRET": "production-grade-secret-key-32chars-min!!",
        "INTEGRATION_ENCRYPTION_KEY": "x" * 44,
        "MONGO_URL": "mongodb://127.0.0.1:27017",
        "DB_NAME": "x",
        "FRONTEND_URL": "http://localhost:3000",
        "API_URL": "http://localhost:8000",
        "CORS_ORIGINS": "http://localhost:3000",
        "AI_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-x",
    }
    with mock.patch.dict(os.environ, env, clear=False):
        rows = validate()
    by = {r["name"]: r for r in rows}
    assert by["FRONTEND_URL"]["status"] == "INVALID"
    assert by["API_URL"]["status"] == "INVALID"


def test_public_config_exposes_email_oauth_cookie_status_without_secrets(client):
    r = client.get("/api/config/public")
    assert r.status_code == 200
    body = r.json()
    assert body["billingEnabled"] is False
    assert "email" in body
    assert "resend_api_key" not in str(body).lower()
    assert "api_key" not in str(body).lower()
    assert body["email"]["provider"] in ("console", "resend")
    assert set(body["oauth"]) >= {"google", "microsoft", "slack"}
    assert body["oauth"]["google"] in ("configured", "not_configured")
    assert "secure" in body["cookies"]
    assert body["cookies"]["sameSite"] in ("lax", "none", "strict")


def test_health_includes_email_oauth_alert_delivery_flags(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert "email" in body
    assert "status" in body["email"]
    assert "oauthProviders" in body
    assert "alertDelivery" in body
    assert body["alertDelivery"]["enabled"] in (True, False)
    assert "hooks.slack.com" not in str(body)
    assert "ALERT_WEBHOOK_URL" not in str(body)


def test_staging_env_maps_to_production_cookie_flags():
    ensure_test_settings()
    from config import reset_settings_for_tests, load_settings

    env = {
        "ENVIRONMENT": "staging",
        "MONGO_URL": "mongodb://127.0.0.1:27017",
        "DB_NAME": "assistify_test",
        "JWT_SECRET": "production-grade-secret-key-32chars-min!!",
        "CORS_ORIGINS": "https://staging.example.com",
        "FRONTEND_URL": "https://staging.example.com",
        "API_URL": "https://api.staging.example.com",
        "INTEGRATION_ENCRYPTION_KEY": "x" * 44,
        "AI_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test",
        "EMAIL_PROVIDER": "console",
        "EMAIL_SENDING_ENABLED": "false",
        "ENABLE_DEMO_LOGIN": "false",
        "ENABLE_DEMO_SEED": "false",
        "REDIS_URL": "redis://127.0.0.1:6379/0",
        "REQUIRE_REDIS": "false",
        "WORKER_ENABLED": "false",
        "SCHEDULER_ENABLED": "false",
    }
    with mock.patch.dict(os.environ, env, clear=False):
        reset_settings_for_tests()
        s = load_settings(strict=True)
        assert s.environment == "production"
        assert s.cookie_secure is True
        assert s.cookie_samesite == "none"
    ensure_test_settings()


def test_cookie_session_login_refresh_logout_csrf(client):
    from dependencies import _rl_store
    _rl_store.clear()
    email = f"s22_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/auth/register", json={
        "firstName": "S", "lastName": "T", "email": email,
        "password": "Password123!", "company": "S22",
    })
    assert reg.status_code == 200, reg.text
    assert "accessToken" not in reg.json()
    assert client.cookies.get("access_token") or reg.cookies.get("access_token")
    assert client.cookies.get("csrf_token") or reg.cookies.get("csrf_token")

    me = client.get("/api/auth/me")
    assert me.status_code == 200

    refresh_tok = client.cookies.get("refresh_token")
    client.cookies.clear()
    if refresh_tok:
        client.cookies.set("refresh_token", refresh_tok, path="/api/auth")
    refreshed = client.post("/api/auth/refresh")
    assert refreshed.status_code == 200, refreshed.text
    assert "accessToken" not in refreshed.json()

    csrf = client.cookies.get("csrf_token")
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf} if csrf else {}).status_code == 200
    assert client.post("/api/auth/refresh").status_code == 401


def test_oauth_redirect_prefers_api_url():
    ensure_test_settings()
    from config import reset_settings_for_tests, load_settings
    from routers.integrations import _redirect_uri

    env = {
        "ENVIRONMENT": "development",
        "MONGO_URL": "mongodb://127.0.0.1:27017",
        "DB_NAME": "assistify_test",
        "JWT_SECRET": "unit-test-secret-key-with-32plus-chars!!",
        "FRONTEND_URL": "https://staging.example.com",
        "API_URL": "https://api.staging.example.com",
        "CORS_ORIGINS": "https://staging.example.com",
        "AI_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test",
        "EMAIL_PROVIDER": "console",
    }
    # Clear any explicit redirect overrides
    for k in ("GOOGLE_REDIRECT_URI", "MICROSOFT_REDIRECT_URI", "SLACK_REDIRECT_URI"):
        env[k] = ""
    with mock.patch.dict(os.environ, env, clear=False):
        reset_settings_for_tests()
        load_settings(strict=True)
        uri = _redirect_uri("google")
        assert uri == "https://api.staging.example.com/api/integrations/oauth/callback/google"
    ensure_test_settings()


def test_alert_delivery_disabled_by_default():
    from alerts_delivery import delivery_enabled, deliver_alerts

    with mock.patch.dict(os.environ, {"ALERT_DELIVERY_ENABLED": ""}, clear=False):
        assert delivery_enabled() is False
        result = asyncio.run(deliver_alerts())
        assert result["delivered"] is False
        assert result["reason"] == "disabled"


def test_alert_delivery_posts_redacted_payload(monkeypatch):
    from alerts_delivery import deliver_alerts

    async def fake_snapshot():
        return {
            "ok": False,
            "critical": True,
            "environment": "staging",
            "release": "test",
            "alerts": [
                {"severity": "critical", "code": "ready_failed", "message": "Redis down api_key=supersecret"},
            ],
        }

    posted = {}

    class FakeResp:
        status_code = 200

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):
            posted["url"] = url
            posted["json"] = json
            return FakeResp()

    monkeypatch.setenv("ALERT_DELIVERY_ENABLED", "true")
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://hooks.example.com/x")
    monkeypatch.setattr("alerts_delivery.collect_alert_snapshot", fake_snapshot)
    monkeypatch.setattr("httpx.AsyncClient", FakeClient)

    result = asyncio.run(deliver_alerts(force=True))
    assert result["delivered"] is True
    assert "supersecret" not in str(posted["json"])
    assert posted["json"]["alerts"][0]["code"] == "ready_failed"


def test_ready_503_when_mongo_down(client, monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("mongo unavailable")

    from core import db
    monkeypatch.setattr(db, "command", boom)
    r = client.get("/api/health/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert "mongodb" in (body.get("failedChecks") or [])


def test_integrations_status_includes_oauth_readiness(client):
    from dependencies import _rl_store
    from conftest import auth_json
    _rl_store.clear()
    email = f"s22i_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/auth/register", json={
        "firstName": "I", "lastName": "T", "email": email,
        "password": "Password123!", "company": "Int Co",
    })
    assert reg.status_code == 200
    data = auth_json(client, reg)
    r = client.get("/api/integrations/status", headers={"Authorization": f"Bearer {data['accessToken']}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "oauthReadiness" in body
    assert body["oauthReadiness"]["google"] in ("configured", "not_configured", "connected", "reconnect_required")
    assert "redirectUriTemplates" in body
    assert "client_secret" not in str(body).lower()
