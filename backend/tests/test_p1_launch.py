"""
P1 Launch-Readiness Tests — repaired for cookie-auth TestClient (Sprint 26).

Covers:
- Security: image/document endpoints ignore ?auth query param
- Email verification send-guard on proposal/contract/invoice
- Verified users can still Send
- Copilot endpoints respond safely without leaking secrets
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from conftest import auth_json

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _clear_rl():
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


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


def _register(client, *, verified=False, company="P1 Co"):
    _clear_rl()
    email = f"p1_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "firstName": "P1",
            "lastName": "Tester",
            "email": email,
            "password": "Password123!",
            "company": company,
        },
    )
    assert r.status_code == 200, r.text
    data = auth_json(client, r)
    tok = data["accessToken"]
    user = data["user"]
    if verified:
        import os
        from pymongo import MongoClient
        mc = MongoClient(os.environ["MONGO_URL"])
        mc[os.environ["DB_NAME"]].users.update_one({"email": email}, {"$set": {"emailVerified": True}})
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
        if me.status_code == 200:
            user = me.json()
    return {
        "email": email,
        "token": tok,
        "headers": {"Authorization": f"Bearer {tok}"},
        "user": user,
    }


@pytest.fixture
def unverified_user(client):
    u = _register(client, verified=False)
    assert u["user"].get("emailVerified") in (False, None)
    return u


@pytest.fixture
def verified_user(client):
    return _register(client, verified=True, company="Verified Co")


@pytest.fixture
def unverified_project(client, unverified_user):
    h = unverified_user["headers"]
    c = client.post("/api/clients", headers=h, json={"name": "TEST_P1_Client", "email": "client@test.com"})
    assert c.status_code == 200, c.text
    client_id = c.json()["id"]
    p = client.post(
        "/api/projects",
        headers=h,
        json={"name": "TEST_P1_Project", "client_id": client_id, "status": "Active"},
    )
    assert p.status_code == 200, p.text
    return p.json()["id"]


@pytest.fixture
def verified_project(client, verified_user):
    h = verified_user["headers"]
    c = client.post("/api/clients", headers=h, json={"name": "TEST_P1_VClient", "email": "vc@test.com"})
    assert c.status_code == 200
    p = client.post(
        "/api/projects",
        headers=h,
        json={"name": "TEST_P1_VProject", "client_id": c.json()["id"], "status": "Active"},
    )
    assert p.status_code == 200
    return p.json()["id"]


class TestImageDocumentSecurity:
    def test_image_no_auth_query_ignored(self, client):
        r = client.get("/api/settings/image/anyid?auth=fake")
        # Must not accept ?auth= as a credential; unauthenticated → 401 or 404
        assert r.status_code in (401, 404)
        assert "fake" not in r.text

    def test_document_no_auth_query_ignored(self, client):
        r = client.get("/api/documents/anyid/file?auth=fake")
        assert r.status_code in (401, 404)
        assert "fake" not in r.text

    def test_image_bearer_returns_404_for_unknown(self, client, verified_user):
        r = client.get("/api/settings/image/nonexistent_asset_xyz", headers=verified_user["headers"])
        assert r.status_code == 404, f"expected 404, got {r.status_code}"

    def test_document_bearer_returns_404_for_unknown(self, client, verified_user):
        r = client.get("/api/documents/nonexistent_doc_xyz/file", headers=verified_user["headers"])
        assert r.status_code == 404, f"expected 404, got {r.status_code}"

    def test_image_missing_auth_401(self, client):
        r = client.get("/api/settings/image/anything")
        assert r.status_code in (401, 404)


class TestSendGuardUnverified:
    def test_proposal_draft_ok(self, client, unverified_user, unverified_project):
        r = client.post(
            f"/api/projects/{unverified_project}/proposal",
            headers=unverified_user["headers"],
            json={"status": "Draft", "title": "T", "content": {"body": "test"}},
        )
        assert r.status_code in (200, 201), f"draft should save: {r.status_code} {r.text}"

    def test_proposal_sent_blocked(self, client, unverified_user, unverified_project):
        r = client.post(
            f"/api/projects/{unverified_project}/proposal",
            headers=unverified_user["headers"],
            json={"status": "Sent", "title": "T", "content": {"body": "test"}},
        )
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"
        assert "verify your email" in r.text.lower()

    def test_contract_draft_ok(self, client, unverified_user, unverified_project):
        r = client.post(
            f"/api/projects/{unverified_project}/contract",
            headers=unverified_user["headers"],
            json={"status": "Draft", "title": "C", "content": {"body": "c"}},
        )
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"

    def test_contract_sent_blocked(self, client, unverified_user, unverified_project):
        r = client.post(
            f"/api/projects/{unverified_project}/contract",
            headers=unverified_user["headers"],
            json={"status": "Sent", "title": "C", "content": {"body": "c"}},
        )
        assert r.status_code == 403
        assert "verify your email" in r.text.lower()

    def test_invoice_draft_ok(self, client, unverified_user, unverified_project):
        r = client.post(
            f"/api/projects/{unverified_project}/invoice",
            headers=unverified_user["headers"],
            json={"status": "Draft", "title": "I", "content": {}, "line_items": []},
        )
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"

    def test_invoice_sent_blocked(self, client, unverified_user, unverified_project):
        r = client.post(
            f"/api/projects/{unverified_project}/invoice",
            headers=unverified_user["headers"],
            json={"status": "Sent", "title": "I", "content": {}, "line_items": []},
        )
        assert r.status_code == 403
        assert "verify your email" in r.text.lower()


class TestSendGuardVerified:
    def test_proposal_sent_ok_verified(self, client, verified_user, verified_project):
        r = client.post(
            f"/api/projects/{verified_project}/proposal",
            headers=verified_user["headers"],
            json={"status": "Sent", "title": "T", "content": {"body": "t"}},
        )
        assert r.status_code in (200, 201), f"verified user should send: {r.status_code} {r.text}"

    def test_contract_sent_ok_verified(self, client, verified_user, verified_project):
        r = client.post(
            f"/api/projects/{verified_project}/contract",
            headers=verified_user["headers"],
            json={"status": "Sent", "title": "T", "content": {"body": "t"}},
        )
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"

    def test_invoice_sent_ok_verified(self, client, verified_user, verified_project):
        r = client.post(
            f"/api/projects/{verified_project}/invoice",
            headers=verified_user["headers"],
            json={"status": "Sent", "title": "I", "content": {}, "line_items": []},
        )
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"


class TestCopilot:
    def test_suggestions(self, client, verified_user):
        r = client.get("/api/copilot/suggestions", headers=verified_user["headers"])
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("suggestions", [])
        assert isinstance(items, list)

    def test_message_safe_error_or_reply(self, client, verified_user):
        r = client.post(
            "/api/copilot/message",
            headers=verified_user["headers"],
            json={"session_id": f"s_{uuid.uuid4().hex[:8]}", "message": "How many clients do I have?"},
            timeout=60,
        )
        assert r.status_code in (200, 502, 503), f"{r.status_code} {r.text[:300]}"
        assert "sk-" not in r.text.lower()
        assert "incorrect api key" not in r.text.lower()
        if r.status_code == 200:
            data = r.json()
            assert "reply" in data or "message" in data or "response" in data or "content" in data

    def test_message_action_shape(self, client, verified_user):
        r = client.post(
            "/api/copilot/message",
            headers=verified_user["headers"],
            json={
                "session_id": f"s_{uuid.uuid4().hex[:8]}",
                "message": "Create a new task called TEST_P1_CopilotTask due next Friday",
            },
            timeout=60,
        )
        assert r.status_code in (200, 502, 503)
        assert "sk-" not in r.text.lower()
        assert r.json() is not None
