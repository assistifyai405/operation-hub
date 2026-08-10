"""Sprint 12 HTTP integration tests (auth cookies + local upload authorization).

Requires MongoDB (MONGO_URL) and uses FastAPI TestClient — no external LLM calls.
"""
from __future__ import annotations

import io
import os
import sys
import uuid
from pathlib import Path

import pytest
from conftest import auth_json

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def app_client(api_client):
    return api_client


def _register(client, email=None):
    email = email or f"user_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register", json={
        "firstName": "Test", "lastName": "User", "email": email,
        "password": "Password123!", "company": "Test Co",
    })
    assert r.status_code == 200, r.text
    data = auth_json(client, r)
    assert data.get("auth") == "cookie" or client.cookies.get("access_token")
    return data


class TestAuthCookiesLocal:
    def test_login_sets_insecure_lax_cookies_in_development(self, app_client):
        client, _ = app_client
        email = f"cookie_{uuid.uuid4().hex[:8]}@example.com"
        _register(client, email)
        # logout then login to inspect Set-Cookie
        client.post("/api/auth/logout")
        r = client.post("/api/auth/login", json={"email": email, "password": "Password123!", "remember": True})
        assert r.status_code == 200, r.text
        # Starlette TestClient stores cookies; inspect raw headers for flags
        set_cookies = r.headers.get_list("set-cookie") if hasattr(r.headers, "get_list") else []
        if not set_cookies:
            # httpx/starlette may join differently
            raw = r.headers.get("set-cookie") or ""
            set_cookies = [c.strip() for c in raw.split(",") if "refresh_token" in c or "access_token" in c] or ([raw] if raw else [])
        joined = " | ".join(set_cookies).lower()
        assert "refresh_token" in joined or client.cookies.get("refresh_token")
        # Development must NOT force Secure; SameSite should be Lax
        if joined:
            assert "samesite=lax" in joined
            # secure flag absent or Secure without being set — Starlette may omit Secure=
            assert "secure;" not in joined.replace(" ", "")

    def test_me_with_bearer(self, app_client):
        client, _ = app_client
        data = _register(client)
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['accessToken']}"})
        assert r.status_code == 200
        assert r.json()["email"] == data["user"]["email"]


class TestLocalUploadAuth:
    def test_upload_and_download_same_org(self, app_client):
        client, upload_dir = app_client
        data = _register(client)
        token = data["accessToken"]
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": ("notes.txt", io.BytesIO(b"sprint12-local-file"), "text/plain")}
        r = client.post("/api/documents/upload", headers=headers, files=files)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["id"]
        assert doc["storage_path"]
        assert Path(upload_dir).exists()

        r2 = client.get(f"/api/documents/{doc['id']}/file", headers=headers)
        assert r2.status_code == 200, r2.text
        assert r2.content == b"sprint12-local-file"

    def test_download_rejected_without_auth(self, app_client):
        client, _ = app_client
        data = _register(client)
        token = data["accessToken"]
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": ("secret.txt", io.BytesIO(b"top-secret"), "text/plain")}
        doc = client.post("/api/documents/upload", headers=headers, files=files).json()
        # Drop session cookies and omit Authorization
        client.cookies.clear()
        r = client.get(f"/api/documents/{doc['id']}/file")
        assert r.status_code == 401

    def test_cross_org_download_forbidden(self, app_client):
        client, _ = app_client
        a = _register(client, f"a_{uuid.uuid4().hex[:8]}@example.com")
        files = {"file": ("a.txt", io.BytesIO(b"org-a-data"), "text/plain")}
        doc = client.post(
            "/api/documents/upload",
            headers={"Authorization": f"Bearer {a['accessToken']}"},
            files=files,
        ).json()

        b = _register(client, f"b_{uuid.uuid4().hex[:8]}@example.com")
        r = client.get(
            f"/api/documents/{doc['id']}/file",
            headers={"Authorization": f"Bearer {b['accessToken']}"},
        )
        assert r.status_code == 404  # org-scoped: not found for other tenant
