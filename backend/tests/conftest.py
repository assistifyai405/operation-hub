"""
Shared pytest fixtures.

A single session-scoped TestClient avoids Motor/asyncio event-loop conflicts
when multiple HTTP test modules would otherwise each create their own client.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from starlette.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "backend" / ".env", override=False)

_TEST_ENV = {
    "ENVIRONMENT": "development",
    "MONGO_URL": "mongodb://127.0.0.1:27017",
    "DB_NAME": "assistify_test",
    "JWT_SECRET": "unit-test-secret-key-with-32plus-chars!!",
    "AI_PROVIDER": "openai",
    "OPENAI_API_KEY": "sk-test-key",
    "STORAGE_PROVIDER": "local",
    "UPLOAD_DIR": "/tmp/assistify-test-uploads",
    "FRONTEND_URL": "http://localhost:3000",
    "CORS_ORIGINS": "http://localhost:3000",
    "ENABLE_DEMO_SEED": "false",
    "ENABLE_DEMO_LOGIN": "false",
    "INVITATION_EXPIRY_DAYS": "7",
    "EMAIL_PROVIDER": "console",
    "EMAIL_SENDING_ENABLED": "false",
    "EMAIL_DAILY_LIMIT": "100",
    "FROM_EMAIL": "onboarding@resend.dev",
    "FROM_NAME": "Assistify OS",
}

for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)


def ensure_test_settings():
    """Restore process-wide settings after unit tests that clear the cache."""
    from config import load_settings, reset_settings_for_tests

    for k, v in _TEST_ENV.items():
        os.environ[k] = v
    # Drop async flags that sprint tests may enable
    for k in ("WORKER_ENABLED", "SCHEDULER_ENABLED", "REQUIRE_REDIS"):
        os.environ.pop(k, None)
    reset_settings_for_tests()
    return load_settings(strict=True)


def clear_rate_limits():
    """Clear in-memory and Redis-backed rate-limit keys used by tests."""
    from dependencies import _rl_store
    _rl_store.clear()
    try:
        from redis_client import get_redis
        r = get_redis()
        if r:
            for k in list(r.scan_iter("assistify:rl:*")):
                r.delete(k)
    except Exception:
        pass


@pytest.fixture(scope="session")
def api_client():
    # Settings must be loaded before importing server (CORS reads them at import).
    ensure_test_settings()
    upload_dir = os.environ["UPLOAD_DIR"]
    Path(upload_dir).mkdir(parents=True, exist_ok=True)

    from server import app
    import dependencies as deps

    with TestClient(app) as client:
        clear_rate_limits()
        yield client, upload_dir
    deps._rl_store.clear()
    clear_rate_limits()


def auth_json(client, response):
    """Cookie-only auth: synthesize accessToken from httpOnly cookie for Bearer test headers.

    Works with Starlette TestClient and requests.Session. `client` may be None
    when the access_token is only on the response cookies.
    """
    data = response.json()
    if not isinstance(data, dict):
        return data
    tok = None
    if client is not None:
        try:
            tok = client.cookies.get("access_token")
        except Exception:
            tok = None
    if not tok:
        try:
            tok = response.cookies.get("access_token")
        except Exception:
            tok = None
    if tok:
        data = {**data, "accessToken": tok}
    return data


def bearer_from_client(client) -> dict:
    tok = client.cookies.get("access_token") if client is not None else None
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def register_user(client, company="Test Co", password="Password123!", first="Test", last="User"):
    """Register a unique user and return headers, token, email, and auth payload.

    Clears rate limits first so parallel/module fixtures don't trip RL.
    """
    import uuid

    clear_rate_limits()
    email = f"u_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "firstName": first,
            "lastName": last,
            "email": email,
            "password": password,
            "company": company,
        },
    )
    assert r.status_code == 200, r.text
    data = auth_json(client, r)
    tok = data["accessToken"]
    return {
        "headers": {"Authorization": f"Bearer {tok}"},
        "token": tok,
        "email": email,
        "password": password,
        "user": data.get("user") or {},
        "data": data,
    }

