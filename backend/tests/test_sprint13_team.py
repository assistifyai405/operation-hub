"""Sprint 13 — Team members, invitations, RBAC, org isolation."""
from __future__ import annotations

import hashlib
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from conftest import auth_json

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def client(api_client):
    c, _upload = api_client
    return c


def _register(client, email=None, password="Password123!", **extra):
    from dependencies import _rl_store
    _rl_store.clear()
    email = email or f"u_{uuid.uuid4().hex[:10]}@example.com"
    body = {
        "firstName": "Test", "lastName": "User", "email": email,
        "password": password, "company": "Acme Co",
        **extra,
    }
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 200, r.text
    data = auth_json(client, r)
    return data, email


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _invite_raw_from_dev_response(inv):
    link = inv.get("invitationLink") or ""
    assert "/invite/" in link, inv
    return link.rsplit("/invite/", 1)[-1]


class TestTeamPermissions:
    def test_member_cannot_invite(self, client):
        owner, owner_email = _register(client)
        inv = client.post(
            "/api/team/invitations",
            headers=_auth(owner["accessToken"]),
            json={"email": f"mem_{uuid.uuid4().hex[:8]}@example.com", "role": "member"},
        ).json()
        raw = _invite_raw_from_dev_response(inv)
        mem_email = inv["email"]
        # Register via invite as member
        mem, _ = _register(client, email=mem_email, invitationToken=raw)
        assert mem["user"]["role"] == "member"
        r = client.post(
            "/api/team/invitations",
            headers=_auth(mem["accessToken"]),
            json={"email": f"x_{uuid.uuid4().hex[:6]}@example.com", "role": "member"},
        )
        assert r.status_code == 403

    def test_member_cannot_patch_org_settings(self, client):
        owner, _ = _register(client)
        inv = client.post(
            "/api/team/invitations",
            headers=_auth(owner["accessToken"]),
            json={"email": f"m2_{uuid.uuid4().hex[:8]}@example.com", "role": "member"},
        ).json()
        raw = _invite_raw_from_dev_response(inv)
        mem, _ = _register(client, email=inv["email"], invitationToken=raw)
        r = client.patch(
            "/api/settings/organization",
            headers=_auth(mem["accessToken"]),
            json={"name": "Hacked"},
        )
        assert r.status_code == 403

    def test_admin_cannot_remove_owner_or_transfer(self, client):
        owner, _ = _register(client)
        inv = client.post(
            "/api/team/invitations",
            headers=_auth(owner["accessToken"]),
            json={"email": f"ad_{uuid.uuid4().hex[:8]}@example.com", "role": "admin"},
        ).json()
        raw = _invite_raw_from_dev_response(inv)
        admin, _ = _register(client, email=inv["email"], invitationToken=raw)
        assert admin["user"]["role"] == "admin"
        r = client.delete(
            f"/api/team/members/{owner['user']['id']}",
            headers=_auth(admin["accessToken"]),
        )
        assert r.status_code == 403
        r = client.post(
            "/api/team/transfer-ownership",
            headers=_auth(admin["accessToken"]),
            json={"userId": admin["user"]["id"]},
        )
        assert r.status_code == 403


class TestOrgIsolation:
    def test_cannot_list_other_org_members(self, client):
        a, _ = _register(client)
        b, _ = _register(client)
        ma = client.get("/api/team/members", headers=_auth(a["accessToken"])).json()
        mb = client.get("/api/team/members", headers=_auth(b["accessToken"])).json()
        assert ma["organization"]["id"] != mb["organization"]["id"]
        assert all(m["email"] != b["user"]["email"] for m in ma["members"])
        assert all(m["email"] != a["user"]["email"] for m in mb["members"])

    def test_cannot_cancel_other_org_invitation(self, client):
        a, _ = _register(client)
        b, _ = _register(client)
        inv = client.post(
            "/api/team/invitations",
            headers=_auth(a["accessToken"]),
            json={"email": f"iso_{uuid.uuid4().hex[:8]}@example.com", "role": "member"},
        ).json()
        r = client.delete(f"/api/team/invitations/{inv['id']}", headers=_auth(b["accessToken"]))
        assert r.status_code == 404


class TestInvitationLifecycle:
    def test_create_accept_register_flow(self, client):
        owner, _ = _register(client)
        email = f"join_{uuid.uuid4().hex[:8]}@example.com"
        inv = client.post(
            "/api/team/invitations",
            headers=_auth(owner["accessToken"]),
            json={"email": email, "role": "member"},
        ).json()
        assert inv["status"] == "pending"
        assert "tokenHash" not in inv
        assert "invitationLink" in inv  # dev mode
        raw = _invite_raw_from_dev_response(inv)

        preview = client.get(f"/api/team/invitations/preview/{raw}").json()
        assert preview["status"] == "pending"
        assert preview["email"] == email
        assert preview["organization"]["name"]

        # Duplicate pending blocked
        r2 = client.post(
            "/api/team/invitations",
            headers=_auth(owner["accessToken"]),
            json={"email": email, "role": "admin"},
        )
        assert r2.status_code == 409

        joined, _ = _register(client, email=email, invitationToken=raw)
        assert joined["joinedViaInvitation"] is True
        assert joined["user"]["organizationId"] == owner["user"]["organizationId"]
        assert joined["user"]["role"] == "member"

        # Replay blocked
        r3 = client.post(f"/api/team/invitations/{raw}/accept", headers=_auth(joined["accessToken"]))
        assert r3.status_code in (409, 410)

        # Token hash never equals raw token
        from pymongo import MongoClient
        mc = MongoClient(os.environ["MONGO_URL"])
        docs = list(mc[os.environ["DB_NAME"]].organization_invitations.find({"email": email}))
        assert docs
        for d in docs:
            assert d.get("tokenHash")
            assert d["tokenHash"] != raw
            assert hashlib.sha256(raw.encode()).hexdigest() == d["tokenHash"]

        members = client.get("/api/team/members", headers=_auth(owner["accessToken"])).json()
        assert any(m["email"] == email for m in members["members"])

    def test_accept_existing_user_email_mismatch(self, client):
        owner, _ = _register(client)
        inv = client.post(
            "/api/team/invitations",
            headers=_auth(owner["accessToken"]),
            json={"email": f"match_{uuid.uuid4().hex[:8]}@example.com", "role": "member"},
        ).json()
        raw = _invite_raw_from_dev_response(inv)
        other, _ = _register(client)
        r = client.post(f"/api/team/invitations/{raw}/accept", headers=_auth(other["accessToken"]))
        assert r.status_code == 403

    def test_accept_existing_user_success(self, client):
        owner, _ = _register(client)
        invitee_email = f"exist_{uuid.uuid4().hex[:8]}@example.com"
        invitee, _ = _register(client, email=invitee_email)
        # Owner invites the existing user
        inv = client.post(
            "/api/team/invitations",
            headers=_auth(owner["accessToken"]),
            json={"email": invitee_email, "role": "admin"},
        ).json()
        raw = _invite_raw_from_dev_response(inv)
        # Invitee is sole owner of their org — can leave
        r = client.post(f"/api/team/invitations/{raw}/accept", headers=_auth(invitee["accessToken"]))
        assert r.status_code == 200, r.text
        data = auth_json(client, r)
        assert data["user"]["organizationId"] == owner["user"]["organizationId"]
        assert data["user"]["role"] == "admin"
        assert data.get("auth") == "cookie" or client.cookies.get("access_token")

        # Replay
        tok = auth_json(client, r).get("accessToken") or data.get("accessToken")
        r2 = client.post(f"/api/team/invitations/{raw}/accept", headers=_auth(tok))
        assert r2.status_code in (409, 410)

    def test_expired_invitation(self, client):
        owner, _ = _register(client)
        inv = client.post(
            "/api/team/invitations",
            headers=_auth(owner["accessToken"]),
            json={"email": f"exp_{uuid.uuid4().hex[:8]}@example.com", "role": "member"},
        ).json()
        raw = _invite_raw_from_dev_response(inv)
        # Force expire via sync pymongo (same DB)
        from pymongo import MongoClient
        mc = MongoClient(os.environ["MONGO_URL"])
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        mc[os.environ["DB_NAME"]].organization_invitations.update_one(
            {"id": inv["id"]}, {"$set": {"expiresAt": past}},
        )

        preview = client.get(f"/api/team/invitations/preview/{raw}").json()
        assert preview["status"] == "expired"
        r = client.post("/api/auth/register", json={
            "firstName": "X", "email": inv["email"], "password": "Password123!",
            "invitationToken": raw,
        })
        assert r.status_code == 400


class TestOwnershipTransfer:
    def test_transfer_and_owner_cannot_self_remove(self, client):
        owner, _ = _register(client)
        inv = client.post(
            "/api/team/invitations",
            headers=_auth(owner["accessToken"]),
            json={"email": f"own_{uuid.uuid4().hex[:8]}@example.com", "role": "admin"},
        ).json()
        raw = _invite_raw_from_dev_response(inv)
        admin, _ = _register(client, email=inv["email"], invitationToken=raw)

        # Owner cannot remove self
        r = client.delete(
            f"/api/team/members/{owner['user']['id']}",
            headers=_auth(owner["accessToken"]),
        )
        assert r.status_code == 400

        r = client.post(
            "/api/team/transfer-ownership",
            headers=_auth(owner["accessToken"]),
            json={"userId": admin["user"]["id"]},
        )
        assert r.status_code == 200, r.text
        members = client.get("/api/team/members", headers=_auth(owner["accessToken"])).json()
        # After transfer, old owner is admin; need refresh role from me
        me = client.get("/api/auth/me", headers=_auth(owner["accessToken"])).json()
        assert me["role"] == "admin"
        roles = {m["id"]: m["role"] for m in members["members"]}
        assert roles[admin["user"]["id"]] == "owner"
        assert roles[owner["user"]["id"]] == "admin"

    def test_cannot_invite_as_owner_role(self, client):
        owner, _ = _register(client)
        r = client.post(
            "/api/team/invitations",
            headers=_auth(owner["accessToken"]),
            json={"email": f"bad_{uuid.uuid4().hex[:8]}@example.com", "role": "owner"},
        )
        assert r.status_code == 400


class TestSeatsHelper:
    def test_seat_counts(self, client):
        owner, _ = _register(client)
        seats = client.get("/api/team/seats", headers=_auth(owner["accessToken"])).json()
        assert seats["active_members"] == 1
        assert seats["pending_invitations"] == 0
        assert seats["enforcement_enabled"] is False
        client.post(
            "/api/team/invitations",
            headers=_auth(owner["accessToken"]),
            json={"email": f"seat_{uuid.uuid4().hex[:8]}@example.com", "role": "member"},
        )
        seats2 = client.get("/api/team/seats", headers=_auth(owner["accessToken"])).json()
        assert seats2["pending_invitations"] == 1
        assert seats2["seats_used"] == seats2["active_members"] + seats2["pending_invitations"]
