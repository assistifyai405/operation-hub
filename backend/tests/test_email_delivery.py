"""Tests for email delivery + dev-mode fallback — TestClient.

Unit tests exercise email_service via the provider interface (console/resend).
HTTP tests verify auth endpoints in console/dev mode.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import email_service
from conftest import auth_json, clear_rate_limits, ensure_test_settings, register_user


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


@pytest.fixture
def restore_settings():
    """Snapshot/restore env + settings around email unit tests that mutate provider config."""
    keys = ("EMAIL_PROVIDER", "RESEND_API_KEY", "FROM_EMAIL", "FROM_NAME")
    old = {k: os.environ.get(k) for k in keys}
    yield
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    ensure_test_settings()


# ---------------- UNIT: email_service ----------------
class TestEmailService:
    def test_disabled_when_no_key(self, restore_settings, monkeypatch):
        monkeypatch.setenv("EMAIL_PROVIDER", "console")
        monkeypatch.delenv("RESEND_API_KEY", raising=False)
        from config import reset_settings_for_tests, load_settings
        reset_settings_for_tests()
        load_settings(strict=True)
        assert email_service.is_enabled() is False

    def test_enabled_when_key_present(self, restore_settings, monkeypatch):
        monkeypatch.setenv("EMAIL_PROVIDER", "resend")
        monkeypatch.setenv("RESEND_API_KEY", "re_test_123")
        monkeypatch.setenv("FROM_EMAIL", "onboarding@resend.dev")
        from config import reset_settings_for_tests, load_settings
        reset_settings_for_tests()
        load_settings(strict=True)
        assert email_service.is_enabled() is True

    def test_fallback_send_does_not_call_resend(self, restore_settings, monkeypatch):
        monkeypatch.setenv("EMAIL_PROVIDER", "console")
        monkeypatch.delenv("RESEND_API_KEY", raising=False)
        from config import reset_settings_for_tests, load_settings
        reset_settings_for_tests()
        load_settings(strict=True)
        res = asyncio.run(email_service.send_verification_email(
            "user@example.com", "https://app/verify?token=x", {"company_name": "Acme"}))
        assert res.get("sent") is True or res.get("mode") in ("console", "dev", "unconfigured")

    def test_verification_email_sent(self, restore_settings, monkeypatch):
        monkeypatch.setenv("EMAIL_PROVIDER", "resend")
        monkeypatch.setenv("RESEND_API_KEY", "re_test_123")
        monkeypatch.setenv("FROM_EMAIL", "onboarding@resend.dev")
        from config import reset_settings_for_tests, load_settings
        reset_settings_for_tests()
        load_settings(strict=True)

        captured = {}

        async def _fake_send(message):
            from email_providers import SendResult
            captured["to"] = message.to
            captured["subject"] = message.subject
            captured["html"] = message.html
            return SendResult(ok=True, provider="resend", provider_message_id="email_abc123")

        import email_providers
        provider = email_providers.ResendEmailProvider(
            api_key="re_test_123", default_from="onboarding@resend.dev",
        )
        monkeypatch.setattr(provider, "send", _fake_send)
        monkeypatch.setattr(email_providers, "get_email_provider", lambda settings=None: provider)
        monkeypatch.setattr(email_service, "get_email_provider", lambda: provider)

        res = asyncio.run(email_service.send_verification_email(
            "user@example.com", "https://app/verify?token=tok",
            {"company_name": "Acme", "primary": "#123456"},
        ))
        assert res["sent"] is True
        assert res["mode"] == "resend"
        assert res["id"] == "email_abc123"
        assert captured["to"] == ["user@example.com"]
        assert "Acme" in captured["subject"]
        assert "verify?token=tok" in captured["html"]

    def test_reset_email_sent(self, restore_settings, monkeypatch):
        monkeypatch.setenv("EMAIL_PROVIDER", "resend")
        monkeypatch.setenv("RESEND_API_KEY", "re_test_123")
        monkeypatch.setenv("FROM_EMAIL", "onboarding@resend.dev")
        from config import reset_settings_for_tests, load_settings
        reset_settings_for_tests()
        load_settings(strict=True)

        captured = {}

        async def _fake_send(message):
            from email_providers import SendResult
            captured["html"] = message.html
            captured["subject"] = message.subject
            return SendResult(ok=True, provider="resend", provider_message_id="email_reset99")

        import email_providers
        provider = email_providers.ResendEmailProvider(
            api_key="re_test_123", default_from="onboarding@resend.dev",
        )
        monkeypatch.setattr(provider, "send", _fake_send)
        monkeypatch.setattr(email_providers, "get_email_provider", lambda settings=None: provider)
        monkeypatch.setattr(email_service, "get_email_provider", lambda: provider)

        res = asyncio.run(email_service.send_password_reset_email(
            "user@example.com", "https://app/reset-password?token=rtok", {"company_name": "Acme"}))
        assert res["sent"] is True and res["id"] == "email_reset99"
        assert "reset-password?token=rtok" in captured["html"]
        assert "Reset" in captured["subject"] or "reset" in captured["subject"].lower()

    def test_send_failure_is_safe(self, restore_settings, monkeypatch):
        monkeypatch.setenv("EMAIL_PROVIDER", "resend")
        monkeypatch.setenv("RESEND_API_KEY", "re_test_123")
        monkeypatch.setenv("FROM_EMAIL", "onboarding@resend.dev")
        from config import reset_settings_for_tests, load_settings
        reset_settings_for_tests()
        load_settings(strict=True)

        async def _raise(message):
            from email_providers import SendResult
            return SendResult(ok=False, provider="resend", error="provider down")

        import email_providers
        provider = email_providers.ResendEmailProvider(
            api_key="re_test_123", default_from="onboarding@resend.dev",
        )
        monkeypatch.setattr(provider, "send", _raise)
        monkeypatch.setattr(email_providers, "get_email_provider", lambda settings=None: provider)
        monkeypatch.setattr(email_service, "get_email_provider", lambda: provider)

        res = asyncio.run(email_service.send_verification_email(
            "user@example.com", "https://app/verify?token=x", None))
        assert res["sent"] is False
        assert res["mode"] == "error"
        assert "provider down" in res["error"]

    def test_internal_logo_not_embedded(self, restore_settings, monkeypatch):
        monkeypatch.setenv("EMAIL_PROVIDER", "resend")
        monkeypatch.setenv("RESEND_API_KEY", "re_test_123")
        monkeypatch.setenv("FROM_EMAIL", "onboarding@resend.dev")
        from config import reset_settings_for_tests, load_settings
        reset_settings_for_tests()
        load_settings(strict=True)

        captured = {}

        async def _fake_send(message):
            from email_providers import SendResult
            captured["html"] = message.html
            return SendResult(ok=True, provider="resend", provider_message_id="x")

        import email_providers
        provider = email_providers.ResendEmailProvider(
            api_key="re_test_123", default_from="onboarding@resend.dev",
        )
        monkeypatch.setattr(provider, "send", _fake_send)
        monkeypatch.setattr(email_providers, "get_email_provider", lambda settings=None: provider)
        monkeypatch.setattr(email_service, "get_email_provider", lambda: provider)

        brand = {"company_name": "Acme", "logo_url": "https://app/api/settings/image/abc?auth=t"}
        asyncio.run(email_service.send_verification_email("u@e.com", "https://app/v?token=1", brand))
        assert "/api/settings/image/" not in captured["html"]
        assert "<img" not in captured["html"]


# ---------------- HTTP: console/dev-mode fallback + regression ----------------
class TestAuthDevModeFallback:
    def test_register_returns_verification_link_in_dev(self, client):
        clear_rate_limits()
        email = f"mail_{uuid.uuid4().hex[:8]}@example.com"
        r = client.post("/api/auth/register", json={
            "firstName": "Mail", "lastName": "Test", "email": email,
            "password": "Pass1234!", "company": "MailOrg",
        })
        assert r.status_code in (200, 201), r.text
        body = auth_json(client, r)
        assert "accessToken" in body and body.get("user", {}).get("email") == email
        raw = r.json()
        assert "verificationLink" in raw and "/verify-email?token=" in raw["verificationLink"]

    def test_forgot_returns_reset_link_in_dev(self, client):
        a = register_user(client, company="ForgotCo", password="Pass1234!")
        r = client.post("/api/auth/forgot-password", json={"email": a["email"]})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert "resetLink" in body and "/reset-password?token=" in body["resetLink"]

    def test_forgot_unknown_email_is_generic(self, client):
        r = client.post("/api/auth/forgot-password",
                        json={"email": f"nobody_{uuid.uuid4().hex[:6]}@example.com"})
        assert r.status_code == 200
        assert "resetLink" not in r.json()

    def test_verify_email_flow_still_works(self, client):
        clear_rate_limits()
        email = f"mail_{uuid.uuid4().hex[:8]}@example.com"
        reg = client.post("/api/auth/register", json={
            "firstName": "Mail", "lastName": "Test", "email": email,
            "password": "Pass1234!", "company": "VerifyCo",
        })
        assert reg.status_code == 200
        link = reg.json()["verificationLink"]
        token = link.split("token=")[1]
        r = client.post("/api/auth/verify-email", json={"token": token})
        assert r.status_code == 200 and r.json().get("ok") is True

    def test_reset_password_flow_still_works(self, client):
        a = register_user(client, company="ResetCo", password="Pass1234!")
        fr = client.post("/api/auth/forgot-password", json={"email": a["email"]}).json()
        token = fr["resetLink"].split("token=")[1]
        r = client.post("/api/auth/reset-password",
                        json={"token": token, "password": "NewPass9876!"})
        assert r.status_code == 200, r.text
        client.cookies.clear()
        clear_rate_limits()
        lr = client.post("/api/auth/login",
                         json={"email": a["email"], "password": "NewPass9876!"})
        assert lr.status_code == 200
        assert "accessToken" in auth_json(client, lr)

    def test_login_and_me_no_regression(self, client):
        a = register_user(client, company="MeCo", password="Pass1234!")
        me = client.get("/api/auth/me", headers=a["headers"])
        assert me.status_code == 200
        assert me.json().get("email") == a["email"]
