"""Tests for Resend email delivery + dev-mode fallback (Assistify OS).

Unit tests exercise email_service directly (mocking Resend). HTTP tests verify
the auth endpoints behave correctly in dev-mode (no RESEND_API_KEY) and that
existing auth flows have no regressions.
"""
import os
import uuid
import asyncio

import pytest
import requests

import email_service
from conftest import auth_json

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


# ---------------- UNIT: email_service ----------------
class TestEmailService:
    def test_disabled_when_no_key(self, monkeypatch):
        monkeypatch.delenv("RESEND_API_KEY", raising=False)
        assert email_service.is_enabled() is False

    def test_enabled_when_key_present(self, monkeypatch):
        monkeypatch.setenv("RESEND_API_KEY", "re_test_123")
        assert email_service.is_enabled() is True

    def test_fallback_send_does_not_call_resend(self, monkeypatch):
        monkeypatch.delenv("RESEND_API_KEY", raising=False)
        called = {"n": 0}

        def _boom(params):
            called["n"] += 1
            raise AssertionError("resend must NOT be called in dev mode")

        monkeypatch.setattr(email_service.resend.Emails, "send", _boom)
        res = asyncio.run(email_service.send_verification_email(
            "user@example.com", "https://app/verify?token=x", {"company_name": "Acme"}))
        assert res == {"sent": False, "mode": "dev"}
        assert called["n"] == 0

    def test_verification_email_sent(self, monkeypatch):
        monkeypatch.setenv("RESEND_API_KEY", "re_test_123")
        captured = {}

        def _fake_send(params):
            captured.update(params)
            return {"id": "email_abc123"}

        monkeypatch.setattr(email_service.resend.Emails, "send", _fake_send)
        res = asyncio.run(email_service.send_verification_email(
            "user@example.com", "https://app/verify?token=tok", {"company_name": "Acme", "primary": "#123456"}))
        assert res["sent"] is True
        assert res["mode"] == "resend"
        assert res["id"] == "email_abc123"
        # Correct recipient, branded subject, link embedded, from configured
        assert captured["to"] == ["user@example.com"]
        assert "Acme" in captured["subject"]
        assert "verify?token=tok" in captured["html"]
        assert captured["from"] == (os.environ.get("FROM_EMAIL") or email_service.DEFAULT_FROM)

    def test_reset_email_sent(self, monkeypatch):
        monkeypatch.setenv("RESEND_API_KEY", "re_test_123")
        captured = {}

        def _fake_send(params):
            captured.update(params)
            return {"id": "email_reset99"}

        monkeypatch.setattr(email_service.resend.Emails, "send", _fake_send)
        res = asyncio.run(email_service.send_password_reset_email(
            "user@example.com", "https://app/reset-password?token=rtok", {"company_name": "Acme"}))
        assert res["sent"] is True and res["id"] == "email_reset99"
        assert "reset-password?token=rtok" in captured["html"]
        assert "Reset" in captured["subject"] or "reset" in captured["subject"].lower()

    def test_send_failure_is_safe(self, monkeypatch):
        monkeypatch.setenv("RESEND_API_KEY", "re_test_123")

        def _raise(params):
            raise RuntimeError("provider down")

        monkeypatch.setattr(email_service.resend.Emails, "send", _raise)
        # Must never raise — returns an error status the caller can log
        res = asyncio.run(email_service.send_verification_email(
            "user@example.com", "https://app/verify?token=x", None))
        assert res["sent"] is False
        assert res["mode"] == "error"
        assert "provider down" in res["error"]

    def test_internal_logo_not_embedded(self, monkeypatch):
        monkeypatch.setenv("RESEND_API_KEY", "re_test_123")
        captured = {}
        monkeypatch.setattr(email_service.resend.Emails, "send",
                            lambda p: captured.update(p) or {"id": "x"})
        # A logo behind the authed image endpoint must NOT be embedded as <img>
        brand = {"company_name": "Acme", "logo_url": "https://app/api/settings/image/abc?auth=t"}
        asyncio.run(email_service.send_verification_email("u@e.com", "https://app/v?token=1", brand))
        assert "/api/settings/image/" not in captured["html"]
        assert "<img" not in captured["html"]


# ---------------- HTTP: dev-mode fallback + regression ----------------
def _register(email):
    return requests.post(f"{BASE_URL}/api/auth/register", json={
        "firstName": "Mail", "lastName": "Test", "email": email,
        "password": "Pass1234!", "company": "MailOrg"}, timeout=20)


class TestAuthDevModeFallback:
    """Server runs with RESEND_API_KEY empty -> dev mode: links surfaced in responses."""

    def test_register_returns_verification_link_in_dev(self):
        email = f"mail_{uuid.uuid4().hex[:8]}@example.com"
        r = _register(email)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert "accessToken" in body and body.get("user", {}).get("email") == email
        # Dev mode exposes the link so the flow is testable
        assert "verificationLink" in body and "/verify-email?token=" in body["verificationLink"]

    def test_forgot_returns_reset_link_in_dev(self):
        email = f"mail_{uuid.uuid4().hex[:8]}@example.com"
        _register(email)
        r = requests.post(f"{BASE_URL}/api/auth/forgot-password", json={"email": email}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert "resetLink" in body and "/reset-password?token=" in body["resetLink"]

    def test_forgot_unknown_email_is_generic(self):
        r = requests.post(f"{BASE_URL}/api/auth/forgot-password",
                          json={"email": f"nobody_{uuid.uuid4().hex[:6]}@example.com"}, timeout=15)
        assert r.status_code == 200
        # No account -> generic response, never a link
        assert "resetLink" not in r.json()

    def test_verify_email_flow_still_works(self):
        email = f"mail_{uuid.uuid4().hex[:8]}@example.com"
        reg = _register(email).json()
        token = reg["verificationLink"].split("token=")[1]
        r = requests.post(f"{BASE_URL}/api/auth/verify-email", json={"token": token}, timeout=15)
        assert r.status_code == 200 and r.json().get("ok") is True

    def test_reset_password_flow_still_works(self):
        email = f"mail_{uuid.uuid4().hex[:8]}@example.com"
        _register(email)
        fr = requests.post(f"{BASE_URL}/api/auth/forgot-password", json={"email": email}, timeout=15).json()
        token = fr["resetLink"].split("token=")[1]
        r = requests.post(f"{BASE_URL}/api/auth/reset-password",
                          json={"token": token, "password": "NewPass9876!"}, timeout=15)
        assert r.status_code == 200, r.text
        # New password works
        lr = requests.post(f"{BASE_URL}/api/auth/login",
                           json={"email": email, "password": "NewPass9876!"}, timeout=15)
        assert lr.status_code == 200 and "accessToken" in lr.json()

    def test_login_and_me_no_regression(self):
        email = f"mail_{uuid.uuid4().hex[:8]}@example.com"
        _register(email)
        lr = requests.post(f"{BASE_URL}/api/auth/login",
                           json={"email": email, "password": "Pass1234!"}, timeout=15)
        assert lr.status_code == 200
        tok = auth_json(client, lr).get("accessToken")
        me = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {tok}"}, timeout=15)
        assert me.status_code == 200 and me.json()["email"] == email
