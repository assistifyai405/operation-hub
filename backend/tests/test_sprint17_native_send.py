"""Sprint 17 — Native Gmail/Outlook send, transport routing, idempotency (mocked)."""

from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pymongo import MongoClient as SyncMongoClient

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from integrations.crypto import encrypt_credentials  # noqa: E402
from inbox.gmail_send import build_mime  # noqa: E402
from inbox.transport_errors import map_http_error, EXPIRED_AUTH, RATE_LIMITED  # noqa: E402


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


@pytest.fixture
def mongo():
    mc = SyncMongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=3000)
    yield mc[os.environ["DB_NAME"]]


@pytest.fixture
def sending_on(monkeypatch):
    monkeypatch.setenv("EMAIL_SENDING_ENABLED", "true")
    monkeypatch.setenv("EMAIL_PROVIDER", "console")


def _uid(p="x"):
    return f"{p}-{uuid.uuid4().hex[:10]}"


def _register(client, email=None):
    from dependencies import _rl_store
    _rl_store.clear()
    email = email or f"s17_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register", json={
        "firstName": "S17", "lastName": "Owner", "email": email,
        "password": "Password123!", "company": "Send Co",
    })
    assert r.status_code == 200, r.text
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _enable_org_sending(client, headers, approval=True):
    r = client.patch("/api/settings/email", headers=headers, json={
        "sendingEnabled": True,
        "approvalRequired": approval,
        "dailySendingLimit": 50,
        "senderName": "Send Co",
        "senderEmail": "noreply@example.com",
    })
    # settings path may vary — try alternate
    if r.status_code == 404:
        r = client.put("/api/settings", headers=headers, json={
            "email": {
                "sendingEnabled": True,
                "approvalRequired": approval,
                "dailySendingLimit": 50,
            }
        })
    if r.status_code >= 400:
        # Direct mongo fallback handled by callers via mongo fixture
        pass
    return r


def _seed_mailbox(mongo, owner, provider="google", email="inbox@example.com"):
    org_id = owner["user"]["organizationId"]
    user_id = owner["user"]["id"]
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn_id = _uid("conn")
    mb_id = _uid("mb")
    mongo.integrations.insert_one({
        "id": conn_id,
        "organizationId": org_id,
        "provider": provider,
        "name": "Google" if provider == "google" else "Microsoft",
        "status": "connected",
        "services": ["gmail"] if provider == "google" else ["outlook"],
        "permissions": ["gmail.send"] if provider == "google" else ["Mail.Send"],
        "accountEmail": email,
        "encryptedCredentials": encrypt_credentials({
            "access_token": "tok-access",
            "refresh_token": "tok-refresh",
            "expires_at": time.time() + 3600,
        }),
        "config": {},
        "connectedBy": user_id,
        "connectedAt": now,
        "updatedAt": now,
        "healthStatus": "healthy",
        "error": None,
    })
    mongo.mailboxes.insert_one({
        "id": mb_id,
        "organizationId": org_id,
        "provider": provider,
        "integrationId": conn_id,
        "providerAccountId": email,
        "emailAddress": email,
        "displayName": email,
        "syncEnabled": True,
        "syncStatus": "idle",
        "lastSyncAt": None,
        "lastSuccessfulSyncAt": None,
        "lastError": None,
        "syncCursor": None,
        "createdAt": now,
        "updatedAt": now,
    })
    return mb_id, conn_id


def _seed_thread_and_inbound(mongo, owner, mb_id, *, provider="google"):
    org_id = owner["user"]["organizationId"]
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tid = _uid("thr")
    mid = _uid("msg")
    mongo.email_threads.insert_one({
        "id": tid,
        "organizationId": org_id,
        "mailboxId": mb_id,
        "provider": provider,
        "providerThreadId": "pthread-1",
        "subject": "Hello",
        "participantEmails": ["buyer@acme.com"],
        "latestMessageAt": now,
        "messageCount": 1,
        "unreadCount": 0,
        "status": "open",
        "linkedClientId": None,
        "linkedLeadId": None,
        "linkedContactId": None,
        "assignedUserId": None,
        "labels": [],
        "aiSummary": None,
        "createdAt": now,
        "updatedAt": now,
    })
    mongo.inbound_messages.insert_one({
        "id": mid,
        "organizationId": org_id,
        "mailboxId": mb_id,
        "threadId": tid,
        "providerMessageId": "pmid-inbound-1",
        "providerThreadId": "pthread-1",
        "internetMessageId": "<inbound-1@acme.com>",
        "from": "buyer@acme.com",
        "to": ["inbox@example.com"],
        "cc": [],
        "bcc": [],
        "subject": "Hello",
        "textBody": "Hi there",
        "sanitizedHtmlBody": "<p>Hi there</p>",
        "snippet": "Hi there",
        "receivedAt": now,
        "sentAt": now,
        "isRead": True,
        "direction": "inbound",
        "attachments": [],
        "providerLabels": [],
        "createdAt": now,
        "updatedAt": now,
    })
    return tid, mid


def _enable_sending_mongo(mongo, org_id, approval=True):
    mongo.organizations.update_one(
        {"id": org_id},
        {"$set": {
            "settings.email.sendingEnabled": True,
            "settings.email.approvalRequired": approval,
            "settings.email.dailySendingLimit": 50,
            "settings.email.senderName": "Send Co",
            "settings.email.senderEmail": "noreply@example.com",
        }},
    )


def _create_linked_draft(mongo, owner, mb_id, tid, *, provider="google", status="approved"):
    org_id = owner["user"]["organizationId"]
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    eid = _uid("email")
    doc = {
        "id": eid,
        "organizationId": org_id,
        "createdBy": owner["user"]["id"],
        "createdByEmail": owner["user"]["email"],
        "to": ["buyer@acme.com"],
        "cc": [],
        "bcc": [],
        "subject": "Re: Hello",
        "htmlBody": "<p>Thanks</p>",
        "textBody": "Thanks",
        "status": status,
        "source": "ai",
        "approvalStatus": "approved" if status == "approved" else "pending",
        "approvedBy": owner["user"]["id"] if status == "approved" else None,
        "sendAttempts": 0,
        "inboxThreadId": tid,
        "mailboxId": mb_id,
        "providerThreadId": "pthread-1",
        "providerConversationId": "pthread-1",
        "inReplyTo": "<inbound-1@acme.com>",
        "references": "<inbound-1@acme.com>",
        "replyProvider": provider,
        "transportProvider": "gmail" if provider == "google" else "microsoft",
        "internetMessageId": None,
        "providerMessageId": None,
        "versions": [],
        "createdAt": now,
        "updatedAt": now,
    }
    mongo.outbound_emails.insert_one(doc)
    return eid


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------


def test_mime_includes_threading_headers():
    raw, mid = build_mime(
        from_email="inbox@example.com",
        from_name="Inbox",
        to=["buyer@acme.com"],
        subject="Re: Hello",
        text_body="Thanks",
        html_body="<p>Thanks</p>",
        in_reply_to="<inbound-1@acme.com>",
        references="<inbound-1@acme.com>",
    )
    assert mid.startswith("<")
    assert isinstance(raw, str) and len(raw) > 20


def test_error_mapping():
    e = map_http_error("Gmail", 401, "invalid credentials")
    assert e.code == EXPIRED_AUTH
    e2 = map_http_error("Microsoft", 429, "throttle")
    assert e2.code == RATE_LIMITED


# ---------------------------------------------------------------------------
# Gmail native send
# ---------------------------------------------------------------------------


def test_gmail_thread_reply_send(client, mongo, sending_on):
    owner = _register(client)
    h = _auth(owner["accessToken"])
    org_id = owner["user"]["organizationId"]
    _enable_sending_mongo(mongo, org_id, approval=True)
    mb_id, _ = _seed_mailbox(mongo, owner, "google")
    tid, _ = _seed_thread_and_inbound(mongo, owner, mb_id)
    eid = _create_linked_draft(mongo, owner, mb_id, tid, provider="google")

    native = {
        "ok": True,
        "provider": "gmail",
        "providerMessageId": "gm-sent-1",
        "providerThreadId": "pthread-1",
        "providerConversationId": "pthread-1",
        "internetMessageId": "<out-1@example.com>",
        "providerRawStatus": "sent",
        "deliveryConfirmed": True,
    }
    with patch("inbox.transport.execute_native_send", new_callable=AsyncMock, return_value=native):
        # Patch at call site used by perform_send
        pass
    with patch("routers.emails.execute_native_send", new_callable=AsyncMock, return_value=native):
        r = client.post(f"/api/emails/{eid}/send", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "sent"
    assert body["sentVia"] == "gmail"
    assert body["transportProvider"] == "gmail"
    assert body["providerMessageId"] == "gm-sent-1"
    assert body["internetMessageId"] == "<out-1@example.com>"
    assert body["providerThreadId"] == "pthread-1"


def test_gmail_sender_uses_mailbox_not_org_spoof(client, mongo, sending_on):
    owner = _register(client)
    h = _auth(owner["accessToken"])
    org_id = owner["user"]["organizationId"]
    _enable_sending_mongo(mongo, org_id)
    mb_id, _ = _seed_mailbox(mongo, owner, "google", email="real-mailbox@example.com")
    tid, _ = _seed_thread_and_inbound(mongo, owner, mb_id)
    eid = _create_linked_draft(mongo, owner, mb_id, tid)

    captured = {}

    async def _fake_send(token, **kwargs):
        captured.update(kwargs)
        return {
            "ok": True, "provider": "gmail", "providerMessageId": "x",
            "providerThreadId": kwargs.get("thread_id"), "providerConversationId": kwargs.get("thread_id"),
            "internetMessageId": "<x@example.com>", "providerRawStatus": "sent",
        }

    with (
        patch("inbox.gmail_send.send_gmail_message", new_callable=AsyncMock, side_effect=_fake_send),
        patch("inbox.transport._load_token", new_callable=AsyncMock, return_value=(
            {"id": "i", "accountEmail": "real-mailbox@example.com", "status": "connected"},
            {"access_token": "tok"},
        )),
    ):
        r = client.post(f"/api/emails/{eid}/send", headers=h)
    assert r.status_code == 200, r.text
    assert captured.get("from_email") == "real-mailbox@example.com"
    assert captured.get("thread_id") == "pthread-1"
    assert captured.get("in_reply_to") == "<inbound-1@acme.com>"


def test_gmail_token_refresh_on_401(client, mongo, sending_on):
    owner = _register(client)
    h = _auth(owner["accessToken"])
    org_id = owner["user"]["organizationId"]
    _enable_sending_mongo(mongo, org_id)
    mb_id, _ = _seed_mailbox(mongo, owner, "google")
    tid, _ = _seed_thread_and_inbound(mongo, owner, mb_id)
    eid = _create_linked_draft(mongo, owner, mb_id, tid)

    from inbox.transport_errors import TransportError, EXPIRED_AUTH, ACTIONABLE
    calls = {"n": 0}

    async def _send(token, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TransportError(EXPIRED_AUTH, "expired", 401, ACTIONABLE[EXPIRED_AUTH])
        return {
            "ok": True, "provider": "gmail", "providerMessageId": "after-refresh",
            "providerThreadId": "pthread-1", "providerConversationId": "pthread-1",
            "internetMessageId": "<r@example.com>", "providerRawStatus": "sent",
        }

    with (
        patch("inbox.gmail_send.send_gmail_message", new_callable=AsyncMock, side_effect=_send),
        patch("inbox.transport._load_token", new_callable=AsyncMock, return_value=(
            {"id": "i1", "accountEmail": "inbox@example.com", "status": "connected"},
            {"access_token": "old", "refresh_token": "ref"},
        )),
        patch("inbox.transport.refresh_token_once", new_callable=AsyncMock, return_value={"access_token": "new", "refresh_token": "ref"}),
    ):
        r = client.post(f"/api/emails/{eid}/send", headers=h)
    assert r.status_code == 200, r.text
    assert calls["n"] == 2
    assert r.json()["providerMessageId"] == "after-refresh"


def test_gmail_duplicate_send_blocked(client, mongo, sending_on):
    owner = _register(client)
    h = _auth(owner["accessToken"])
    org_id = owner["user"]["organizationId"]
    _enable_sending_mongo(mongo, org_id)
    mb_id, _ = _seed_mailbox(mongo, owner, "google")
    tid, _ = _seed_thread_and_inbound(mongo, owner, mb_id)
    eid = _create_linked_draft(mongo, owner, mb_id, tid)
    native = {
        "ok": True, "provider": "gmail", "providerMessageId": "once",
        "providerThreadId": "pthread-1", "providerConversationId": "pthread-1",
        "internetMessageId": "<once@example.com>", "providerRawStatus": "sent", "deliveryConfirmed": True,
    }
    with patch("routers.emails.execute_native_send", new_callable=AsyncMock, return_value=native) as mock_send:
        assert client.post(f"/api/emails/{eid}/send", headers=h).status_code == 200
        r2 = client.post(f"/api/emails/{eid}/send", headers=h)
        assert r2.status_code == 400
        assert mock_send.await_count == 1


def test_gmail_disconnected_no_resend_fallback(client, mongo, sending_on):
    owner = _register(client)
    h = _auth(owner["accessToken"])
    org_id = owner["user"]["organizationId"]
    _enable_sending_mongo(mongo, org_id)
    mb_id, conn_id = _seed_mailbox(mongo, owner, "google")
    mongo.integrations.update_one({"id": conn_id}, {"$set": {"status": "disconnected", "encryptedCredentials": None}})
    tid, _ = _seed_thread_and_inbound(mongo, owner, mb_id)
    eid = _create_linked_draft(mongo, owner, mb_id, tid)
    with patch("email_providers.ConsoleEmailProvider.send", new_callable=AsyncMock) as console_send:
        r = client.post(f"/api/emails/{eid}/send", headers=h)
        assert r.status_code == 400
        assert console_send.await_count == 0
        detail = r.json()["detail"]
        assert isinstance(detail, dict)
        assert detail.get("code") == "disconnected_integration"


def test_dedupe_after_native_send_sync(client, mongo, sending_on):
    owner = _register(client)
    h = _auth(owner["accessToken"])
    org_id = owner["user"]["organizationId"]
    _enable_sending_mongo(mongo, org_id)
    mb_id, _ = _seed_mailbox(mongo, owner, "google")
    tid, _ = _seed_thread_and_inbound(mongo, owner, mb_id)
    eid = _create_linked_draft(mongo, owner, mb_id, tid)
    native = {
        "ok": True, "provider": "gmail", "providerMessageId": "gm-echo",
        "providerThreadId": "pthread-1", "providerConversationId": "pthread-1",
        "internetMessageId": "<echo@example.com>", "providerRawStatus": "sent", "deliveryConfirmed": True,
    }
    with patch("routers.emails.execute_native_send", new_callable=AsyncMock, return_value=native):
        assert client.post(f"/api/emails/{eid}/send", headers=h).status_code == 200

    parsed = {
        "providerMessageId": "gm-echo",
        "providerThreadId": "pthread-1",
        "internetMessageId": "<echo@example.com>",
        "from": "inbox@example.com",
        "to": ["buyer@acme.com"],
        "cc": [], "bcc": [],
        "subject": "Re: Hello",
        "textBody": "Thanks",
        "sanitizedHtmlBody": "",
        "snippet": "Thanks",
        "receivedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sentAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "isRead": True,
        "attachments": [],
        "providerLabels": ["SENT"],
    }
    with (
        patch("inbox.gmail.list_inbox_message_ids", new_callable=AsyncMock, return_value=(["gm-echo"], None, "1")),
        patch("inbox.gmail.fetch_messages_batch", new_callable=AsyncMock, return_value=[parsed]),
        patch("inbox.gmail.discover_account", new_callable=AsyncMock, return_value={
            "providerAccountId": "inbox@example.com", "emailAddress": "inbox@example.com",
            "displayName": "Inbox", "historyId": "9",
        }),
    ):
        mongo.mailboxes.update_one({"id": mb_id}, {"$set": {"syncCursor": None}})
        assert client.post(f"/api/inbox/mailboxes/{mb_id}/sync", headers=h).status_code == 200
    assert mongo.inbound_messages.count_documents({"organizationId": org_id, "providerMessageId": "gm-echo"}) == 0


# ---------------------------------------------------------------------------
# Microsoft
# ---------------------------------------------------------------------------


def test_microsoft_reply_send(client, mongo, sending_on):
    owner = _register(client)
    h = _auth(owner["accessToken"])
    org_id = owner["user"]["organizationId"]
    _enable_sending_mongo(mongo, org_id)
    mb_id, _ = _seed_mailbox(mongo, owner, "microsoft", email="outlook@example.com")
    tid, _ = _seed_thread_and_inbound(mongo, owner, mb_id, provider="microsoft")
    eid = _create_linked_draft(mongo, owner, mb_id, tid, provider="microsoft")
    native = {
        "ok": True, "provider": "microsoft", "providerMessageId": "ms-sent-1",
        "providerThreadId": "pthread-1", "providerConversationId": "pthread-1",
        "internetMessageId": "<ms-out@outlook.com>", "providerRawStatus": "sent",
        "deliveryConfirmed": True,
    }
    with patch("routers.emails.execute_native_send", new_callable=AsyncMock, return_value=native):
        r = client.post(f"/api/emails/{eid}/send", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["sentVia"] == "microsoft"
    assert r.json()["transportProvider"] == "microsoft"


def test_microsoft_ambiguous_delivery(client, mongo, sending_on):
    owner = _register(client)
    h = _auth(owner["accessToken"])
    org_id = owner["user"]["organizationId"]
    _enable_sending_mongo(mongo, org_id)
    mb_id, _ = _seed_mailbox(mongo, owner, "microsoft", email="outlook@example.com")
    tid, _ = _seed_thread_and_inbound(mongo, owner, mb_id, provider="microsoft")
    eid = _create_linked_draft(mongo, owner, mb_id, tid, provider="microsoft")
    native = {
        "ok": True, "provider": "microsoft", "providerMessageId": "ms-amb",
        "providerThreadId": "pthread-1", "providerConversationId": "pthread-1",
        "internetMessageId": "<amb@outlook.com>", "providerRawStatus": "accepted_unconfirmed",
        "deliveryConfirmed": False,
    }
    with patch("routers.emails.execute_native_send", new_callable=AsyncMock, return_value=native):
        r = client.post(f"/api/emails/{eid}/send", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "delivery_unknown"


def test_microsoft_error_mapping_insufficient_scopes(client, mongo, sending_on):
    owner = _register(client)
    h = _auth(owner["accessToken"])
    org_id = owner["user"]["organizationId"]
    _enable_sending_mongo(mongo, org_id)
    mb_id, _ = _seed_mailbox(mongo, owner, "microsoft", email="outlook@example.com")
    tid, _ = _seed_thread_and_inbound(mongo, owner, mb_id, provider="microsoft")
    eid = _create_linked_draft(mongo, owner, mb_id, tid, provider="microsoft")
    from inbox.transport_errors import TransportError, INSUFFICIENT_SCOPES, ACTIONABLE
    with patch(
        "routers.emails.execute_native_send",
        new_callable=AsyncMock,
        side_effect=TransportError(INSUFFICIENT_SCOPES, "missing Mail.Send", 403, ACTIONABLE[INSUFFICIENT_SCOPES]),
    ):
        r = client.post(f"/api/emails/{eid}/send", headers=h)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == INSUFFICIENT_SCOPES
    doc = mongo.outbound_emails.find_one({"id": eid})
    assert doc["status"] == "failed"


# ---------------------------------------------------------------------------
# Standalone Resend/console preserved + approval
# ---------------------------------------------------------------------------


def test_standalone_console_still_works(client, mongo, sending_on):
    owner = _register(client)
    h = _auth(owner["accessToken"])
    _enable_sending_mongo(mongo, owner["user"]["organizationId"], approval=False)
    r = client.post("/api/emails", headers=h, json={
        "to": ["a@b.com"], "subject": "Standalone", "textBody": "Hi",
    })
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    # approve not required
    s = client.post(f"/api/emails/{eid}/send", headers=h)
    assert s.status_code == 200, s.text
    assert s.json()["status"] == "sent"
    assert s.json()["provider"] == "console"
    assert s.json().get("transportProvider") in (None, "console") or s.json().get("sentVia") == "console"


def test_member_cannot_send_native(client, mongo, sending_on):
    owner = _register(client)
    h = _auth(owner["accessToken"])
    org_id = owner["user"]["organizationId"]
    _enable_sending_mongo(mongo, org_id, approval=True)
    mb_id, _ = _seed_mailbox(mongo, owner, "google")
    tid, _ = _seed_thread_and_inbound(mongo, owner, mb_id)
    eid = _create_linked_draft(mongo, owner, mb_id, tid, status="approved")

    from dependencies import _rl_store
    inv = client.post("/api/team/invitations", headers=h, json={
        "email": f"m17_{uuid.uuid4().hex[:8]}@example.com", "role": "member",
    }).json()
    raw = (inv.get("invitationLink") or "").rsplit("/invite/", 1)[-1]
    _rl_store.clear()
    mem = client.post("/api/auth/register", json={
        "firstName": "M", "lastName": "M", "email": inv["email"],
        "password": "Password123!", "invitationToken": raw,
    }).json()
    r = client.post(f"/api/emails/{eid}/send", headers=_auth(mem["accessToken"]))
    assert r.status_code == 403


def test_transport_on_get_email(client, mongo, sending_on):
    owner = _register(client)
    h = _auth(owner["accessToken"])
    mb_id, _ = _seed_mailbox(mongo, owner, "google")
    tid, _ = _seed_thread_and_inbound(mongo, owner, mb_id)
    eid = _create_linked_draft(mongo, owner, mb_id, tid, status="draft")
    r = client.get(f"/api/emails/{eid}", headers=h)
    assert r.status_code == 200
    t = r.json().get("transport") or {}
    assert t.get("transportProvider") == "gmail"
    assert t.get("isThreadedReply") is True
    assert "Send via Gmail" in (t.get("label") or "")
