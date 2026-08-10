"""Sprint 20 — production foundation: env fail-fast, health ready, demo hard-off."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _base_prod(**extra):
    env = {
        "ENVIRONMENT": "production",
        "MONGO_URL": "mongodb://127.0.0.1:27017",
        "DB_NAME": "assistify_test",
        "JWT_SECRET": "prod-grade-secret-key-with-40-plus-chars!!",
        "CORS_ORIGINS": "https://app.example.com",
        "FRONTEND_URL": "https://app.example.com",
        "AI_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-live-test-key",
        "STORAGE_PROVIDER": "local",
        "INTEGRATION_ENCRYPTION_KEY": "prod-integration-encryption-key-32b",
        "EMAIL_PROVIDER": "console",
        "EMAIL_SENDING_ENABLED": "false",
        "ENABLE_DEMO_SEED": "false",
        "ENABLE_DEMO_LOGIN": "false",
        "REDIS_URL": "redis://127.0.0.1:6379/0",
        "REQUIRE_REDIS": "false",
        "WORKER_ENABLED": "false",
        "SCHEDULER_ENABLED": "false",
    }
    env.update(extra)
    return env


def _with_env(env):
    from config import load_settings, reset_settings_for_tests
    reset_settings_for_tests()
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        return load_settings(strict=True)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        reset_settings_for_tests()
        import conftest as cf
        cf.ensure_test_settings()


def test_production_rejects_weak_jwt():
    from config import ConfigError
    with pytest.raises(ConfigError, match="JWT_SECRET"):
        _with_env(_base_prod(JWT_SECRET="local-dev-secret-change-me-32chars!!"))


def test_production_rejects_localhost_frontend():
    from config import ConfigError
    with pytest.raises(ConfigError, match="FRONTEND_URL"):
        _with_env(_base_prod(FRONTEND_URL="http://localhost:3000"))


def test_production_requires_ai_key():
    from config import ConfigError
    env = _base_prod(OPENAI_API_KEY="")
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        _with_env(env)


def test_production_requires_encryption_key():
    from config import ConfigError
    env = _base_prod(INTEGRATION_ENCRYPTION_KEY="")
    with pytest.raises(ConfigError, match="INTEGRATION_ENCRYPTION_KEY"):
        _with_env(env)


def test_production_forces_demo_off_without_allow():
    s = _with_env(_base_prod(ENABLE_DEMO_LOGIN="true", ENABLE_DEMO_SEED="true", ALLOW_DEMO_IN_PRODUCTION="false"))
    assert s.enable_demo_login is False
    assert s.enable_demo_seed is False


def test_production_redis_required_when_worker():
    from config import ConfigError
    env = _base_prod(WORKER_ENABLED="true")
    env.pop("REDIS_URL", None)
    with pytest.raises(ConfigError, match="REDIS_URL"):
        _with_env(env)


def test_production_settings_load_ok():
    s = _with_env(_base_prod())
    assert s.is_production
    assert s.enable_demo_login is False
    assert s.integration_encryption_key


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


def test_health_live_never_depends_on_redis(client):
    r = client.get("/api/health/live")
    assert r.status_code == 200
    assert r.json()["check"] == "live"


def test_health_ready_shape(client):
    r = client.get("/api/health/ready")
    assert r.status_code in (200, 503)
    body = r.json()
    assert body["check"] == "ready"
    assert "mongodb" in body["checks"]
    assert "redis" in body["checks"]
    assert "jobs" in body["checks"]


def test_public_config_no_secrets(client):
    r = client.get("/api/config/public")
    assert r.status_code == 200
    raw = r.text.lower()
    assert "jwt" not in raw
    assert "password" not in raw
    assert "secret" not in raw
    assert r.json()["billingEnabled"] is False


def test_smoke_register_login_agents(client):
    from dependencies import _rl_store
    _rl_store.clear()
    email = f"s20_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post("/api/auth/register", json={
        "firstName": "Prod", "lastName": "Ready", "email": email,
        "password": "Password123!", "company": "Prod Co",
    })
    assert reg.status_code == 200, reg.text
    token = reg.json()["accessToken"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/auth/me", headers=h).status_code == 200
    agents = client.get("/api/agents", headers=h)
    assert agents.status_code == 200
    assert isinstance(agents.json(), list)
    assert client.post("/api/auth/demo").status_code == 404
