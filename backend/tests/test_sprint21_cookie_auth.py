"""Sprint 21 — cookie-only auth, CSRF, workspace isolation, production cookie flags."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from unittest import mock

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from conftest import auth_json, ensure_test_settings


@pytest.fixture
def client(api_client):
    c, _ = api_client
    c.cookies.clear()
    return c


def _clear_rl():
    from dependencies import _rl_store
    _rl_store.clear()


def _register(client, email=None, company="Cookie Co"):
    _clear_rl()
    email = email or f"s21_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "firstName": "Sprint",
            "lastName": "TwentyOne",
            "email": email,
            "password": "Password123!",
            "company": company,
        },
    )
    assert r.status_code == 200, r.text
    return auth_json(client, r), email


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_api_rejected(client):
    client.cookies.clear()
    for path in ("/api/auth/me", "/api/clients", "/api/projects", "/api/agents", "/api/settings"):
        r = client.get(path)
        assert r.status_code == 401, path


def test_register_login_cookie_only_no_jwt_in_body(client):
    data, email = _register(client)
    assert "accessToken" not in data or data.get("auth") == "cookie"
    # Raw register body never includes JWT
    assert client.cookies.get("access_token")

    client.cookies.clear()
    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123!", "remember": True},
    )
    assert login.status_code == 200, login.text
    body = login.json()
    assert "accessToken" not in body
    assert body.get("auth") == "cookie"
    assert login.cookies.get("access_token") or client.cookies.get("access_token")
    assert login.cookies.get("csrf_token") or client.cookies.get("csrf_token")

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_authenticated_access_via_cookie_and_bearer(client):
    data, email = _register(client)
    tok = data["accessToken"]
    assert tok
    # Bearer (test / machine clients)
    assert client.get("/api/auth/me", headers=_auth(tok)).status_code == 200
    # Cookie session on same client
    assert client.get("/api/agents").status_code == 200


def test_refresh_survives_without_localstorage_token(client):
    _register(client)
    refresh = client.cookies.get("refresh_token")
    assert refresh, "register must set refresh_token cookie"
    client.cookies.clear()
    client.cookies.set("refresh_token", refresh, path="/api/auth")
    r = client.post("/api/auth/refresh")
    assert r.status_code == 200, r.text
    assert "accessToken" not in r.json()
    assert r.json().get("auth") == "cookie"
    assert r.cookies.get("access_token") or client.cookies.get("access_token")
    assert client.get("/api/auth/me").status_code == 200


def test_logout_invalidates_session(client):
    data, _ = _register(client)
    tok = data["accessToken"]
    csrf = client.cookies.get("csrf_token")
    r = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf} if csrf else {})
    assert r.status_code == 200
    # Refresh must fail
    assert client.post("/api/auth/refresh").status_code == 401
    # Old bearer must fail once session path uses refresh revocation;
    # access JWT may still validate until expiry — me with cookie should fail.
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401


def test_expired_or_invalid_session_fails_cleanly(client):
    client.cookies.clear()
    client.cookies.set("access_token", "not-a-jwt", path="/api")
    r = client.get("/api/auth/me")
    assert r.status_code == 401
    assert "detail" in r.json()

    client.cookies.clear()
    client.cookies.set("refresh_token", "also-not-a-jwt", path="/api/auth")
    r2 = client.post("/api/auth/refresh")
    assert r2.status_code == 401


def test_csrf_required_for_cookie_mutations(client):
    data, _ = _register(client)
    # Ensure we have session cookies; strip Authorization
    assert client.cookies.get("access_token") or data.get("accessToken")
    # Mutating without CSRF header must fail when using cookies only
    r = client.post(
        "/api/clients",
        json={"name": "CSRF Block", "contact": "A", "email": "a@b.co"},
    )
    assert r.status_code == 403
    assert "CSRF" in (r.json().get("detail") or "")

    csrf = client.cookies.get("csrf_token")
    assert csrf
    r2 = client.post(
        "/api/clients",
        headers={"X-CSRF-Token": csrf},
        json={"name": "CSRF Ok", "contact": "A", "email": "a@b.co"},
    )
    assert r2.status_code == 200, r2.text


def test_bearer_skips_csrf(client):
    data, _ = _register(client)
    tok = data["accessToken"]
    client.cookies.clear()  # no cookie session
    r = client.post(
        "/api/clients",
        headers=_auth(tok),
        json={"name": "Bearer Client", "contact": "B", "email": "b@b.co"},
    )
    assert r.status_code == 200, r.text


def test_workspace_isolation(client):
    a, _ = _register(client, company="Org A")
    ca = client.post(
        "/api/clients",
        headers=_auth(a["accessToken"]),
        json={"name": "Only A", "contact": "A", "email": "a@org.test"},
    )
    assert ca.status_code == 200

    b, _ = _register(client, company="Org B")
    lb = client.get("/api/clients", headers=_auth(b["accessToken"]))
    assert lb.status_code == 200
    names = [c.get("name") for c in lb.json()]
    assert "Only A" not in names

    la = client.get("/api/clients", headers=_auth(a["accessToken"]))
    assert la.status_code == 200
    assert "Only A" in [c.get("name") for c in la.json()]


def test_role_unauthenticated_cannot_invite(client):
    client.cookies.clear()
    r = client.post(
        "/api/team/invitations",
        json={"email": f"x_{uuid.uuid4().hex[:6]}@example.com", "role": "member"},
    )
    assert r.status_code in (401, 403)


def test_production_cookie_flags():
    ensure_test_settings()
    from config import reset_settings_for_tests, load_settings

    env = {
        "ENVIRONMENT": "production",
        "MONGO_URL": "mongodb://127.0.0.1:27017",
        "DB_NAME": "assistify_test",
        "JWT_SECRET": "production-grade-secret-key-32chars-min!!",
        "CORS_ORIGINS": "https://app.example.com",
        "FRONTEND_URL": "https://app.example.com",
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
        assert s.cookie_secure is True
        assert s.cookie_samesite == "none"
    ensure_test_settings()


def test_auth_json_body_never_includes_access_token_on_register(client):
    _clear_rl()
    email = f"plain_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "firstName": "P",
            "lastName": "Q",
            "email": email,
            "password": "Password123!",
            "company": "Plain",
        },
    )
    assert r.status_code == 200
    raw = r.json()
    assert "accessToken" not in raw
    assert raw.get("auth") == "cookie"
