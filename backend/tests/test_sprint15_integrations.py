"""Sprint 15 — Integrations Hub (connect, encrypt, isolate, automation actions)."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


def _register(client, email=None):
    from dependencies import _rl_store
    _rl_store.clear()
    email = email or f"i_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register", json={
        "firstName": "Int", "lastName": "User", "email": email,
        "password": "Password123!", "company": "Integrations Co",
    })
    assert r.status_code == 200, r.text
    return r.json(), email


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _invite_member(client, owner_token):
    from dependencies import _rl_store
    inv = client.post(
        "/api/team/invitations",
        headers=_auth(owner_token),
        json={"email": f"m_{uuid.uuid4().hex[:8]}@example.com", "role": "member"},
    ).json()
    raw = (inv.get("invitationLink") or "").rsplit("/invite/", 1)[-1]
    assert raw, inv
    _rl_store.clear()
    mem = client.post("/api/auth/register", json={
        "firstName": "M", "lastName": "M", "email": inv["email"],
        "password": "Password123!", "invitationToken": raw,
    }).json()
    return mem


class TestCatalogAndList:
    def test_list_includes_all_providers(self, client):
        owner, _ = _register(client)
        r = client.get("/api/integrations", headers=_auth(owner["accessToken"]))
        assert r.status_code == 200, r.text
        data = r.json()
        ids = {c["id"] for c in data["catalog"]}
        assert ids == {"google", "microsoft", "slack", "discord", "zapier", "webhook"}
        assert len(data["items"]) == 6
        assert all(i["status"] == "disconnected" for i in data["items"])
        assert "encryptedCredentials" not in r.text
        assert "refresh_token" not in r.text


class TestWebhookConnect:
    def test_connect_disconnect_webhook(self, client):
        owner, _ = _register(client)
        h = _auth(owner["accessToken"])
        r = client.post("/api/integrations/connect", headers=h, json={
            "provider": "webhook",
            "webhookUrl": "https://example.com/hooks/assistify",
            "signingSecret": "super-secret",
            "useOauth": False,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["integration"]["status"] in ("connected", "error")
        assert "encryptedCredentials" not in body["integration"]
        assert "super-secret" not in r.text

        from pymongo import MongoClient
        mc = MongoClient(os.environ["MONGO_URL"])
        doc = mc[os.environ["DB_NAME"]].integrations.find_one({
            "organizationId": owner["user"]["organizationId"],
            "provider": "webhook",
        })
        assert doc["encryptedCredentials"]
        assert "super-secret" not in doc["encryptedCredentials"]

        st = client.get("/api/integrations/status", headers=h).json()
        assert st["providers"]["webhook"]["status"] in ("connected", "error")

        d = client.post("/api/integrations/disconnect", headers=h, json={"provider": "webhook"})
        assert d.status_code == 200
        assert d.json()["integration"]["status"] == "disconnected"
        doc2 = mc[os.environ["DB_NAME"]].integrations.find_one({"id": doc["id"]})
        assert not doc2.get("encryptedCredentials")

    def test_rejects_http_webhook(self, client):
        owner, _ = _register(client)
        r = client.post("/api/integrations/connect", headers=_auth(owner["accessToken"]), json={
            "provider": "zapier",
            "webhookUrl": "http://insecure.example/hook",
        })
        assert r.status_code == 400

    def test_member_cannot_connect(self, client):
        owner, _ = _register(client)
        mem = _invite_member(client, owner["accessToken"])
        r = client.post("/api/integrations/connect", headers=_auth(mem["accessToken"]), json={
            "provider": "discord",
            "webhookUrl": "https://discord.com/api/webhooks/1/abc",
        })
        assert r.status_code == 403


class TestOrgIsolation:
    def test_cannot_see_other_org_connection(self, client):
        a, _ = _register(client)
        b, _ = _register(client)
        client.post("/api/integrations/connect", headers=_auth(a["accessToken"]), json={
            "provider": "zapier",
            "webhookUrl": "https://hooks.zapier.com/hooks/catch/123/abc",
        })
        items = client.get("/api/integrations", headers=_auth(b["accessToken"])).json()["items"]
        zap = next(i for i in items if i["provider"] == "zapier")
        assert zap["status"] == "disconnected"


class TestOauthGates:
    def test_google_requires_config(self, client, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
        # Reload provider check reads get_settings which may have cached None — env del is enough for is_configured
        owner, _ = _register(client)
        r = client.post("/api/integrations/connect", headers=_auth(owner["accessToken"]), json={
            "provider": "google", "useOauth": True,
        })
        assert r.status_code == 503


class TestEncryptionUnit:
    def test_roundtrip(self):
        from config import load_settings
        load_settings(strict=True)
        from integrations.crypto import encrypt_credentials, decrypt_credentials
        blob = encrypt_credentials({"refresh_token": "rt_secret_value", "access_token": "at"})
        assert "rt_secret_value" not in blob
        plain = decrypt_credentials(blob)
        assert plain["refresh_token"] == "rt_secret_value"


class TestAutomationActions:
    def test_action_meta_includes_integrations(self):
        from routers.automation import ACTION_META, EXTERNAL
        for key in (
            "create_calendar_event", "create_google_task",
            "send_slack_message", "send_discord_message", "trigger_webhook",
        ):
            assert key in ACTION_META
            assert key in EXTERNAL
            assert ACTION_META[key]["kind"] == "external"

    def test_trigger_webhook_mocked_store(self):
        import asyncio
        from integrations.actions import trigger_webhook

        class FakeResp:
            status_code = 200
            def raise_for_status(self):
                return None

        class FakeClient:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *a):
                return False
            async def post(self, url, json=None, headers=None):
                assert url == "https://hooks.example/x"
                return FakeResp()

        async def run():
            with patch("integrations.actions.store.get_by_provider", new=AsyncMock(return_value={
                "id": "int1", "status": "connected", "organizationId": "org1",
            })), patch("integrations.actions.store.load_credentials", new=AsyncMock(return_value={
                "webhook_url": "https://hooks.example/x",
            })), patch("integrations.actions.store.update_health", new=AsyncMock()), \
                 patch("integrations.actions.httpx.AsyncClient", return_value=FakeClient()):
                return await trigger_webhook("org1", {"message": "hi"}, prefer="webhook")

        out = asyncio.run(run())
        assert out["provider"] == "webhook"

    def test_slack_requires_connection_mocked(self):
        import asyncio
        from integrations.actions import send_slack_message

        async def run():
            with patch("integrations.actions.store.get_by_provider", new=AsyncMock(return_value=None)):
                with pytest.raises(RuntimeError, match="not connected"):
                    await send_slack_message("org1", {"text": "hi"})

        asyncio.run(run())


class TestHealth:
    def test_health_on_discord_webhook(self, client):
        owner, _ = _register(client)
        h = _auth(owner["accessToken"])
        client.post("/api/integrations/connect", headers=h, json={
            "provider": "discord",
            "webhookUrl": "https://example.com/discord-hook",
        })
        r = client.post("/api/integrations/health", headers=h, json={"provider": "discord"})
        assert r.status_code == 200, r.text
        assert "encryptedCredentials" not in r.text
