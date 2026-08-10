"""Sprint 12 — Production Hardening & Local Portability (unit tests).

These tests do not require a live HTTP server or MongoDB. They validate:
  - env / JWT / CORS startup rules
  - cookie policy for local HTTP vs production
  - AI provider key resolution
  - local storage put/get + path traversal rejection
  - JWT auth helpers still sign/verify
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure backend package root is importable when pytest is launched from repo root
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


REQUIRED = {
    "MONGO_URL": "mongodb://localhost:27017",
    "DB_NAME": "assistify_test",
    "JWT_SECRET": "unit-test-secret-key-with-32plus-chars!!",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    # Clear provider/config-related vars so each test starts clean
    for k in list(os.environ.keys()):
        if k in {
            "ENVIRONMENT", "ENV", "MONGO_URL", "DB_NAME", "JWT_SECRET",
            "CORS_ORIGINS", "FRONTEND_URL", "ENABLE_DEMO_SEED", "ENABLE_DEMO_LOGIN",
            "ALLOW_DEMO_IN_PRODUCTION",
            "AI_PROVIDER", "AI_MODEL", "OPENAI_API_KEY", "EMERGENT_LLM_KEY",
            "STORAGE_PROVIDER", "UPLOAD_DIR", "COOKIE_SECURE", "COOKIE_SAMESITE",
            "DEMO_EMAIL", "DEMO_PASSWORD", "INVITATION_EXPIRY_DAYS",
            "EMAIL_PROVIDER", "EMAIL_SENDING_ENABLED", "EMAIL_DAILY_LIMIT",
            "RESEND_API_KEY", "FROM_EMAIL", "FROM_NAME", "REPLY_TO_EMAIL",
            "RESEND_WEBHOOK_SECRET", "INTEGRATION_ENCRYPTION_KEY",
            "REDIS_URL", "REQUIRE_REDIS", "WORKER_ENABLED", "SCHEDULER_ENABLED",
            "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI",
            "MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET", "MICROSOFT_TENANT",
            "MICROSOFT_REDIRECT_URI", "SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET",
            "SLACK_REDIRECT_URI",
        }:
            monkeypatch.delenv(k, raising=False)
    import config
    config.reset_settings_for_tests()
    yield
    # Restore defaults so session HTTP fixtures / other modules keep working
    try:
        from conftest import ensure_test_settings
        ensure_test_settings()
    except Exception:
        config.reset_settings_for_tests()


def _load(**extra):
    import config
    for k, v in {**REQUIRED, **extra}.items():
        os.environ[k] = v
    config.reset_settings_for_tests()
    return config.load_settings(strict=True)


# ---------------- Config / production safety ----------------
class TestConfigValidation:
    def test_requires_mongo_db_jwt(self, monkeypatch):
        import config
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("MONGO_URL", raising=False)
        monkeypatch.delenv("DB_NAME", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)
        config.reset_settings_for_tests()
        with pytest.raises(config.ConfigError) as ei:
            config.load_settings(strict=True)
        msg = str(ei.value)
        assert "MONGO_URL" in msg and "DB_NAME" in msg and "JWT_SECRET" in msg

    def test_rejects_weak_jwt_in_production(self):
        import config
        with pytest.raises(config.ConfigError):
            _load(ENVIRONMENT="production", JWT_SECRET="changeme", CORS_ORIGINS="https://app.example.com")

    def test_rejects_short_jwt_in_production(self):
        import config
        with pytest.raises(config.ConfigError):
            _load(ENVIRONMENT="production", JWT_SECRET="short-but-not-weak", CORS_ORIGINS="https://app.example.com")

    def test_requires_explicit_cors_in_production(self):
        import config
        with pytest.raises(config.ConfigError):
            _load(ENVIRONMENT="production", CORS_ORIGINS="*")

    def test_production_ok_with_strong_secret_and_cors(self):
        s = _load(
            ENVIRONMENT="production",
            JWT_SECRET="a" * 40,
            CORS_ORIGINS="https://app.example.com,https://admin.example.com",
            FRONTEND_URL="https://app.example.com",
            OPENAI_API_KEY="sk-test-prod",
            INTEGRATION_ENCRYPTION_KEY="integration-key-for-unit-tests-32",
        )
        assert s.is_production
        assert s.cors_origins == ["https://app.example.com", "https://admin.example.com"]
        assert s.cookie_secure is True
        assert s.cookie_samesite == "none"
        assert s.enable_demo_seed is False

    def test_demo_seed_off_by_default_even_in_dev(self):
        s = _load(ENVIRONMENT="development")
        assert s.enable_demo_seed is False

    def test_demo_seed_opt_in(self):
        s = _load(ENVIRONMENT="development", ENABLE_DEMO_SEED="true")
        assert s.enable_demo_seed is True

    def test_demo_login_off_by_default(self):
        s = _load(ENVIRONMENT="development")
        assert s.enable_demo_login is False

    def test_demo_login_opt_in(self):
        s = _load(ENVIRONMENT="development", ENABLE_DEMO_LOGIN="true")
        assert s.enable_demo_login is True

    def test_production_weak_demo_password_rejected(self):
        import pytest
        from config import ConfigError
        with pytest.raises(ConfigError, match="DEMO_PASSWORD"):
            _load(
                ENVIRONMENT="production",
                JWT_SECRET="a" * 40,
                CORS_ORIGINS="https://app.example.com",
                FRONTEND_URL="https://app.example.com",
                OPENAI_API_KEY="sk-test-prod",
                INTEGRATION_ENCRYPTION_KEY="integration-key-for-unit-tests-32",
                ENABLE_DEMO_SEED="true",
                ALLOW_DEMO_IN_PRODUCTION="true",
                DEMO_PASSWORD="change-me-demo-password",
            )


class TestCookiePolicy:
    def test_localhost_http_uses_lax_insecure(self):
        s = _load(ENVIRONMENT="development", FRONTEND_URL="http://localhost:3000")
        assert s.cookie_secure is False
        assert s.cookie_samesite == "lax"

    def test_https_frontend_keeps_secure_even_in_dev(self):
        s = _load(ENVIRONMENT="development", FRONTEND_URL="https://preview.example.com")
        assert s.cookie_secure is True
        assert s.cookie_samesite == "none"


# ---------------- AI provider ----------------
class TestAIProvider:
    def test_openai_requires_key(self):
        import config
        from ai_service import AIService, AIConfigError
        _load(ENVIRONMENT="development", AI_PROVIDER="openai")
        with pytest.raises(config.ConfigError):
            config.resolve_ai_api_key()
        with pytest.raises(AIConfigError):
            AIService(provider="openai", api_key=None)

    def test_openai_resolves_key(self):
        import config
        from ai_service import AIService
        s = _load(ENVIRONMENT="development", AI_PROVIDER="openai", OPENAI_API_KEY="sk-test-123")
        assert config.resolve_ai_api_key(s) == "sk-test-123"
        svc = AIService(api_key="sk-test-123", provider="openai", model="gpt-4o-mini")
        assert svc.provider == "openai"

    def test_emergent_requires_key(self):
        import config
        _load(ENVIRONMENT="development", AI_PROVIDER="emergent")
        with pytest.raises(config.ConfigError):
            config.resolve_ai_api_key()

    def test_emergent_resolves_key(self):
        import config
        s = _load(ENVIRONMENT="development", AI_PROVIDER="emergent", EMERGENT_LLM_KEY="emg-test")
        assert config.resolve_ai_api_key(s) == "emg-test"


# ---------------- Local storage ----------------
class TestLocalStorage:
    def test_put_get_roundtrip(self, tmp_path):
        _load(ENVIRONMENT="development", STORAGE_PROVIDER="local", UPLOAD_DIR=str(tmp_path))
        import storage as S
        S.init_storage()
        path = f"assistify-os/uploads/org1/{tmp_path.name}.txt"
        result = S.put_object(path, b"hello-sprint12", "text/plain")
        assert result["path"] == path
        assert result["size"] == len(b"hello-sprint12")
        content, ctype = S.get_object(path)
        assert content == b"hello-sprint12"
        assert "text" in ctype or ctype == "text/plain"

    def test_path_traversal_rejected(self, tmp_path):
        _load(ENVIRONMENT="development", STORAGE_PROVIDER="local", UPLOAD_DIR=str(tmp_path))
        import storage as S
        S.init_storage()
        with pytest.raises(S.StorageError):
            S.get_object("../etc/passwd")
        with pytest.raises(S.StorageError):
            S.put_object("../../evil.txt", b"x", "text/plain")

    def test_org_paths_isolated_by_filename(self, tmp_path):
        """Different org path prefixes store different objects under the same upload root."""
        _load(ENVIRONMENT="development", STORAGE_PROVIDER="local", UPLOAD_DIR=str(tmp_path))
        import storage as S
        S.put_object("assistify-os/uploads/orgA/a.txt", b"A", "text/plain")
        S.put_object("assistify-os/uploads/orgB/b.txt", b"B", "text/plain")
        assert S.get_object("assistify-os/uploads/orgA/a.txt")[0] == b"A"
        assert S.get_object("assistify-os/uploads/orgB/b.txt")[0] == b"B"
        with pytest.raises(S.StorageError):
            S.get_object("assistify-os/uploads/orgA/missing.txt")


# ---------------- Auth helpers ----------------
class TestAuthHelpers:
    def test_jwt_roundtrip(self):
        _load(ENVIRONMENT="development")
        import auth as A
        token = A.create_access_token("u1", "a@b.com", "org1")
        payload = A.decode_token(token)
        assert payload["sub"] == "u1"
        assert payload["org"] == "org1"
        assert payload["type"] == "access"
        hashed = A.hash_password("CorrectHorseBattery!")
        assert A.verify_password("CorrectHorseBattery!", hashed)
        assert not A.verify_password("wrong", hashed)
