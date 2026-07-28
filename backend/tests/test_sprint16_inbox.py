"""Sprint 16 — Gmail/Outlook inbox sync, CRM matching, AI drafts (mocked providers)."""

from __future__ import annotations

import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pymongo import MongoClient as SyncMongoClient

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from inbox.sanitize import sanitize_html  # noqa: E402
from integrations.base import PROVIDER_CATALOG  # noqa: E402
from integrations.crypto import encrypt_credentials  # noqa: E402
from integrations.providers import GOOGLE_SCOPES  # noqa: E402


@pytest.fixture
def client(api_client):
    c, _ = api_client
    return c


@pytest.fixture
def mongo():
    mc = SyncMongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=3000)
    yield mc[os.environ["DB_NAME"]]


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _register(client, email=None):
    from dependencies import _rl_store
    _rl_store.clear()
    email = email or f"i16_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register", json={
        "firstName": "Inbox", "lastName": "Owner", "email": email,
        "password": "Password123!", "company": "Inbox Co",
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
        json={"email": f"m16_{uuid.uuid4().hex[:8]}@example.com", "role": "member"},
    ).json()
    raw = (inv.get("invitationLink") or "").rsplit("/invite/", 1)[-1]
    assert raw, inv
    _rl_store.clear()
    mem = client.post("/api/auth/register", json={
        "firstName": "M", "lastName": "M", "email": inv["email"],
        "password": "Password123!", "invitationToken": raw,
    }).json()
    return mem


def _seed_google(mongo, owner: dict, *, email_address: str = "inbox@example.com"):
    org_id = owner["user"]["organizationId"]
    user_id = owner["user"]["id"]
    conn_id = _uid("conn")
    mb_id = _uid("mb")
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    mongo.integrations.insert_one({
        "id": conn_id,
        "organizationId": org_id,
        "provider": "google",
        "name": "Google Workspace",
        "status": "connected",
        "services": ["gmail"],
        "permissions": ["gmail.readonly", "gmail.send"],
        "accountEmail": email_address,
        "encryptedCredentials": encrypt_credentials({
            "access_token": "ya29.test",
            "refresh_token": "1//refresh",
            "expires_at": time.time() + 3600,
            "token_type": "Bearer",
        }),
        "config": {},
        "connectedBy": user_id,
        "connectedAt": now,
        "updatedAt": now,
        "healthStatus": "healthy",
        "healthMessage": "Connected",
        "error": None,
    })
    mongo.mailboxes.insert_one({
        "id": mb_id,
        "organizationId": org_id,
        "provider": "google",
        "integrationId": conn_id,
        "providerAccountId": email_address,
        "emailAddress": email_address,
        "displayName": "Gmail Inbox",
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


def _seed_microsoft(mongo, owner: dict, *, email_address: str = "outlook@example.com"):
    org_id = owner["user"]["organizationId"]
    user_id = owner["user"]["id"]
    conn_id = _uid("conn")
    mb_id = _uid("mb")
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    mongo.integrations.insert_one({
        "id": conn_id,
        "organizationId": org_id,
        "provider": "microsoft",
        "name": "Microsoft 365",
        "status": "connected",
        "services": ["outlook"],
        "permissions": ["Mail.Read", "Mail.Send"],
        "accountEmail": email_address,
        "encryptedCredentials": encrypt_credentials({
            "access_token": "eyJ.test",
            "refresh_token": "0.refresh",
            "expires_at": time.time() + 3600,
            "token_type": "Bearer",
        }),
        "config": {},
        "connectedBy": user_id,
        "connectedAt": now,
        "updatedAt": now,
        "healthStatus": "healthy",
        "healthMessage": "Connected",
        "error": None,
    })
    mongo.mailboxes.insert_one({
        "id": mb_id,
        "organizationId": org_id,
        "provider": "microsoft",
        "integrationId": conn_id,
        "providerAccountId": "ms-acct-1",
        "emailAddress": email_address,
        "displayName": "Outlook Inbox",
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


def _parsed_gmail(*, mid="gm-1", thread="thr-1", sender="customer@acme.com", subject="Need help", msgid="<mid-1@acme.com>"):
    return {
        "providerMessageId": mid,
        "providerThreadId": thread,
        "internetMessageId": msgid,
        "inReplyTo": None,
        "references": None,
        "from": sender.lower(),
        "fromRaw": sender,
        "to": ["inbox@example.com"],
        "cc": [],
        "bcc": [],
        "subject": subject,
        "textBody": "Hello team",
        "sanitizedHtmlBody": "<p>Hello team</p>",
        "snippet": "Hello team",
        "receivedAt": "2023-11-15T00:00:00+00:00",
        "sentAt": "2023-11-15T00:00:00+00:00",
        "isRead": False,
        "direction": "inbound",
        "attachments": [],
        "providerLabels": ["INBOX", "UNREAD"],
    }


def _parsed_outlook(*, mid="ms-1", thread="conv-1", sender="lead@prospect.com"):
    return {
        "providerMessageId": mid,
        "providerThreadId": thread,
        "internetMessageId": f"<{mid}@outlook.com>",
        "inReplyTo": None,
        "references": None,
        "from": sender.lower(),
        "fromRaw": sender,
        "to": ["outlook@example.com"],
        "cc": [],
        "bcc": [],
        "subject": "Hello Outlook",
        "textBody": "Hello Outlook body",
        "sanitizedHtmlBody": "",
        "snippet": "Preview",
        "receivedAt": "2024-01-01T12:00:00Z",
        "sentAt": "2024-01-01T12:00:00Z",
        "isRead": False,
        "direction": "inbound",
        "attachments": [],
        "providerLabels": ["Inbox"],
    }


# ---------------------------------------------------------------------------
# Scopes + sanitize
# ---------------------------------------------------------------------------


def test_oauth_scopes_include_mail_read():
    assert "https://www.googleapis.com/auth/gmail.readonly" in GOOGLE_SCOPES
    assert "gmail.readonly" in PROVIDER_CATALOG["google"].permissions
    assert "Mail.Read" in PROVIDER_CATALOG["microsoft"].permissions
    assert "Mail.Send" in PROVIDER_CATALOG["microsoft"].permissions


def test_html_sanitization_strips_scripts_and_images():
    dirty = (
        '<p>Hi</p><script>alert(1)</script><img src="https://evil/x.png" onerror="x">'
        '<a href="javascript:alert(1)">x</a><a href="https://ok.com">ok</a>'
    )
    clean = sanitize_html(dirty)
    assert "<script" not in clean.lower()
    assert "<img" not in clean.lower()
    assert "javascript:" not in clean.lower()
    assert "https://ok.com" in clean
    assert "Hi" in clean


# ---------------------------------------------------------------------------
# Gmail sync (mocked)
# ---------------------------------------------------------------------------


def test_gmail_initial_sync_and_dedupe(client, mongo):
    owner, _ = _register(client)
    h = _auth(owner["accessToken"])
    mb_id, _ = _seed_google(mongo, owner)
    parsed = _parsed_gmail()

    with (
        patch("inbox.gmail.list_inbox_message_ids", new_callable=AsyncMock, return_value=(["gm-1"], None, "1")),
        patch("inbox.gmail.fetch_messages_batch", new_callable=AsyncMock, return_value=[parsed]),
        patch("inbox.gmail.discover_account", new_callable=AsyncMock, return_value={
            "providerAccountId": "inbox@example.com",
            "emailAddress": "inbox@example.com",
            "displayName": "Inbox",
            "historyId": "99",
        }),
    ):
        r = client.post(f"/api/inbox/mailboxes/{mb_id}/sync", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["messagesCreated"] == 1
    assert body["messagesScanned"] == 1
    org_id = owner["user"]["organizationId"]
    assert mongo.inbound_messages.count_documents({"organizationId": org_id, "providerMessageId": "gm-1"}) == 1
    assert mongo.mailboxes.find_one({"id": mb_id})["syncCursor"] == "99"

    # Second full sync of same message → no duplicate insert
    mongo.mailboxes.update_one({"id": mb_id}, {"$set": {"syncCursor": None}})
    with (
        patch("inbox.gmail.list_inbox_message_ids", new_callable=AsyncMock, return_value=(["gm-1"], None, "1")),
        patch("inbox.gmail.fetch_messages_batch", new_callable=AsyncMock, return_value=[parsed]),
        patch("inbox.gmail.discover_account", new_callable=AsyncMock, return_value={
            "providerAccountId": "inbox@example.com",
            "emailAddress": "inbox@example.com",
            "displayName": "Inbox",
            "historyId": "100",
        }),
    ):
        r2 = client.post(f"/api/inbox/mailboxes/{mb_id}/sync", headers=h)
    assert r2.status_code == 200
    assert r2.json()["messagesCreated"] == 0
    assert mongo.inbound_messages.count_documents({"organizationId": org_id, "providerMessageId": "gm-1"}) == 1


def test_gmail_incremental_and_cursor_reset(client, mongo):
    owner, _ = _register(client)
    h = _auth(owner["accessToken"])
    mb_id, _ = _seed_google(mongo, owner)
    mongo.mailboxes.update_one({"id": mb_id}, {"$set": {"syncCursor": "50"}})
    parsed = _parsed_gmail(mid="gm-2", thread="thr-2", msgid="<mid-2@b.com>", sender="a@b.com", subject="Inc")

    with (
        patch("inbox.gmail.history_message_ids", new_callable=AsyncMock, return_value=(["gm-2"], "60", False)),
        patch("inbox.gmail.fetch_messages_batch", new_callable=AsyncMock, return_value=[parsed]),
    ):
        r = client.post(f"/api/inbox/mailboxes/{mb_id}/sync", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["messagesCreated"] == 1
    assert mongo.mailboxes.find_one({"id": mb_id})["syncCursor"] == "60"

    # Invalid history → fallback full sync
    mongo.mailboxes.update_one({"id": mb_id}, {"$set": {"syncCursor": "stale"}})
    with (
        patch("inbox.gmail.history_message_ids", new_callable=AsyncMock, return_value=([], None, True)),
        patch("inbox.gmail.list_inbox_message_ids", new_callable=AsyncMock, return_value=([], None, "0")),
        patch("inbox.gmail.fetch_messages_batch", new_callable=AsyncMock, return_value=[]),
        patch("inbox.gmail.discover_account", new_callable=AsyncMock, return_value={
            "providerAccountId": "inbox@example.com",
            "emailAddress": "inbox@example.com",
            "displayName": "Inbox",
            "historyId": "70",
        }),
    ):
        r2 = client.post(f"/api/inbox/mailboxes/{mb_id}/sync", headers=h)
    assert r2.status_code == 200
    assert r2.json()["cursorReset"] is True
    assert mongo.mailboxes.find_one({"id": mb_id})["syncCursor"] == "70"


# ---------------------------------------------------------------------------
# Outlook sync
# ---------------------------------------------------------------------------


def test_outlook_initial_and_delta(client, mongo):
    owner, _ = _register(client)
    h = _auth(owner["accessToken"])
    mb_id, _ = _seed_microsoft(mongo, owner)
    parsed = _parsed_outlook()
    delta1 = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages/delta?$deltatoken=d1"
    delta2 = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages/delta?$deltatoken=d2"
    delta_fresh = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages/delta?$deltatoken=fresh"

    with patch(
        "inbox.outlook.delta_inbox",
        new_callable=AsyncMock,
        return_value=([parsed], delta1, False),
    ):
        r = client.post(f"/api/inbox/mailboxes/{mb_id}/sync", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["messagesCreated"] == 1
    assert "deltatoken=d1" in (mongo.mailboxes.find_one({"id": mb_id})["syncCursor"] or "")

    org_id = owner["user"]["organizationId"]
    with patch(
        "inbox.outlook.delta_inbox",
        new_callable=AsyncMock,
        return_value=([parsed], delta2, False),
    ):
        r2 = client.post(f"/api/inbox/mailboxes/{mb_id}/sync", headers=h)
    assert r2.status_code == 200
    assert mongo.inbound_messages.count_documents({"organizationId": org_id, "providerMessageId": "ms-1"}) == 1

    # Delta gone → reset
    mongo.mailboxes.update_one({"id": mb_id}, {"$set": {"syncCursor": "https://stale"}})
    calls = {"n": 0}

    async def _delta_side(*args, **kwargs):
        calls["n"] += 1
        if kwargs.get("delta_link") == "https://stale":
            return [], None, True
        return [], delta_fresh, False

    with patch("inbox.outlook.delta_inbox", new_callable=AsyncMock, side_effect=_delta_side):
        r3 = client.post(f"/api/inbox/mailboxes/{mb_id}/sync", headers=h)
    assert r3.status_code == 200
    assert r3.json()["cursorReset"] is True
    assert "deltatoken=fresh" in (mongo.mailboxes.find_one({"id": mb_id})["syncCursor"] or "")


# ---------------------------------------------------------------------------
# Permissions + isolation + AI + CRM + attachments
# ---------------------------------------------------------------------------


def test_member_cannot_sync_or_patch_mailbox(client, mongo):
    owner, _ = _register(client)
    mb_id, _ = _seed_google(mongo, owner)
    mem = _invite_member(client, owner["accessToken"])
    mem_h = _auth(mem["accessToken"])
    assert client.post(f"/api/inbox/mailboxes/{mb_id}/sync", headers=mem_h).status_code == 403
    assert client.patch(
        f"/api/inbox/mailboxes/{mb_id}", headers=mem_h, json={"syncEnabled": False},
    ).status_code == 403
    assert client.get("/api/inbox/mailboxes", headers=mem_h).status_code == 200


def test_org_isolation_threads(client, mongo):
    a, _ = _register(client, email=f"isoA_{uuid.uuid4().hex[:6]}@example.com")
    b, _ = _register(client, email=f"isoB_{uuid.uuid4().hex[:6]}@example.com")
    mb_a, _ = _seed_google(mongo, a, email_address="a@ex.com")
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tid = _uid("thr")
    mongo.email_threads.insert_one({
        "id": tid,
        "organizationId": a["user"]["organizationId"],
        "mailboxId": mb_a,
        "provider": "google",
        "providerThreadId": "t1",
        "subject": "Secret",
        "participantEmails": ["x@y.com"],
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
        "aiSummaryUpdatedAt": None,
        "createdAt": now,
        "updatedAt": now,
    })
    assert client.get(f"/api/inbox/threads/{tid}", headers=_auth(b["accessToken"])).status_code == 404
    assert client.get(f"/api/inbox/threads/{tid}", headers=_auth(a["accessToken"])).status_code == 200


def test_ai_summary_and_draft_reply(client, mongo):
    owner, _ = _register(client)
    h = _auth(owner["accessToken"])
    mb_id, _ = _seed_google(mongo, owner)
    org_id = owner["user"]["organizationId"]
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tid = _uid("thr")
    mid = _uid("msg")
    mongo.email_threads.insert_one({
        "id": tid,
        "organizationId": org_id,
        "mailboxId": mb_id,
        "provider": "google",
        "providerThreadId": "pt1",
        "subject": "Quote request",
        "participantEmails": ["buyer@acme.com"],
        "latestMessageAt": now,
        "messageCount": 1,
        "unreadCount": 1,
        "status": "open",
        "linkedClientId": None,
        "linkedLeadId": None,
        "linkedContactId": None,
        "assignedUserId": None,
        "labels": [],
        "aiSummary": None,
        "aiSummaryUpdatedAt": None,
        "createdAt": now,
        "updatedAt": now,
    })
    mongo.inbound_messages.insert_one({
        "id": mid,
        "organizationId": org_id,
        "mailboxId": mb_id,
        "threadId": tid,
        "providerMessageId": "pm1",
        "providerThreadId": "pt1",
        "internetMessageId": "<pm1@acme.com>",
        "from": "buyer@acme.com",
        "to": ["inbox@example.com"],
        "cc": [],
        "bcc": [],
        "subject": "Quote request",
        "textBody": "Can you send pricing?",
        "sanitizedHtmlBody": "<p>Can you send pricing?</p>",
        "snippet": "Can you send pricing?",
        "receivedAt": now,
        "sentAt": now,
        "isRead": False,
        "direction": "inbound",
        "attachments": [],
        "providerLabels": ["INBOX"],
        "createdAt": now,
        "updatedAt": now,
    })

    summary = {
        "summary": "Buyer wants pricing",
        "intent": "quote",
        "urgency": "medium",
        "sentiment": "neutral",
        "requestedActions": ["send quote"],
        "openQuestions": [],
        "suggestedNextStep": "Reply with pricing",
    }
    with patch("routers.inbox.ai_service.complete_json", new_callable=AsyncMock, return_value=summary):
        r = client.post(f"/api/inbox/threads/{tid}/summarize", headers=h)
    assert r.status_code == 200, r.text
    assert "pricing" in (r.json().get("aiSummary") or {}).get("summary", "").lower()

    draft_ai = {"subject": "Re: Quote request", "body": "Thanks — here is pricing."}
    with patch("routers.inbox.ai_service.complete_json", new_callable=AsyncMock, return_value=draft_ai):
        r2 = client.post(f"/api/inbox/threads/{tid}/draft-reply", headers=h)
    assert r2.status_code == 200, r2.text
    payload = r2.json()
    draft = payload["email"]
    assert draft["status"] == "pending_approval"
    assert draft["inboxThreadId"] == tid
    assert draft["inReplyTo"] == "<pm1@acme.com>"
    assert draft["mailboxId"] == mb_id
    assert draft["replyProvider"] == "google"
    ob = mongo.outbound_emails.find_one({"id": draft["id"]})
    assert ob is not None
    assert ob.get("replyProvider") == "google"


def test_manual_link_and_crm_match_on_sync(client, mongo):
    owner, _ = _register(client)
    h = _auth(owner["accessToken"])
    mb_id, _ = _seed_google(mongo, owner)
    org_id = owner["user"]["organizationId"]
    mongo.clients.insert_one({
        "id": "client-match",
        "organizationId": org_id,
        "name": "Matched Co",
        "email": "customer@acme.com",
        "status": "active",
        "created_at": "t",
        "updated_at": "t",
    })
    parsed = _parsed_gmail(mid="gm-match", thread="thr-match", sender="customer@acme.com", msgid="<match@acme.com>")
    with (
        patch("inbox.gmail.list_inbox_message_ids", new_callable=AsyncMock, return_value=(["gm-match"], None, "1")),
        patch("inbox.gmail.fetch_messages_batch", new_callable=AsyncMock, return_value=[parsed]),
        patch("inbox.gmail.discover_account", new_callable=AsyncMock, return_value={
            "providerAccountId": "inbox@example.com",
            "emailAddress": "inbox@example.com",
            "displayName": "Inbox",
            "historyId": "1",
        }),
    ):
        assert client.post(f"/api/inbox/mailboxes/{mb_id}/sync", headers=h).status_code == 200

    thr = mongo.email_threads.find_one({"organizationId": org_id, "providerThreadId": "thr-match"})
    assert thr is not None
    assert thr["linkedClientId"] == "client-match"

    # Org isolation: other org client email must not match
    other_org = _uid("other")
    mongo.clients.insert_one({
        "id": "other-client",
        "organizationId": other_org,
        "name": "Other",
        "email": "nobody-match@x.com",
        "status": "active",
        "created_at": "t",
        "updated_at": "t",
    })
    parsed2 = _parsed_gmail(mid="gm-iso", thread="thr-iso", sender="nobody-match@x.com", msgid="<iso@x.com>")
    with (
        patch("inbox.gmail.list_inbox_message_ids", new_callable=AsyncMock, return_value=(["gm-iso"], None, "1")),
        patch("inbox.gmail.fetch_messages_batch", new_callable=AsyncMock, return_value=[parsed2]),
        patch("inbox.gmail.discover_account", new_callable=AsyncMock, return_value={
            "providerAccountId": "inbox@example.com",
            "emailAddress": "inbox@example.com",
            "displayName": "Inbox",
            "historyId": "2",
        }),
    ):
        # Clear cursor so full sync runs
        mongo.mailboxes.update_one({"id": mb_id}, {"$set": {"syncCursor": None}})
        assert client.post(f"/api/inbox/mailboxes/{mb_id}/sync", headers=h).status_code == 200
    thr2 = mongo.email_threads.find_one({"organizationId": org_id, "providerThreadId": "thr-iso"})
    assert thr2["linkedClientId"] is None
    assert thr2["status"] == "unlinked"

    mongo.leads.insert_one({
        "id": "lead-1",
        "organizationId": org_id,
        "name": "Lead",
        "email": "other@x.com",
        "status": "new",
        "created_at": "t",
        "updated_at": "t",
    })
    r = client.post(
        f"/api/inbox/threads/{thr['id']}/link",
        headers=h,
        json={"leadId": "lead-1", "clientId": None},
    )
    assert r.status_code == 200, r.text
    assert r.json()["linkedLeadId"] == "lead-1"


def test_attachment_download_org_isolation(client, mongo):
    a, _ = _register(client, email=f"attA_{uuid.uuid4().hex[:6]}@example.com")
    b, _ = _register(client, email=f"attB_{uuid.uuid4().hex[:6]}@example.com")
    mb_a, _ = _seed_google(mongo, a)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tid = _uid("thr")
    mid = _uid("msg")
    aid = "att-prov-1"
    mongo.email_threads.insert_one({
        "id": tid,
        "organizationId": a["user"]["organizationId"],
        "mailboxId": mb_a,
        "provider": "google",
        "providerThreadId": "t",
        "subject": "Att",
        "participantEmails": [],
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
        "aiSummaryUpdatedAt": None,
        "createdAt": now,
        "updatedAt": now,
    })
    mongo.inbound_messages.insert_one({
        "id": mid,
        "organizationId": a["user"]["organizationId"],
        "mailboxId": mb_a,
        "threadId": tid,
        "providerMessageId": "pm-att",
        "providerThreadId": "t",
        "internetMessageId": None,
        "from": "x@y.com",
        "to": [],
        "cc": [],
        "bcc": [],
        "subject": "Att",
        "textBody": "",
        "sanitizedHtmlBody": "",
        "snippet": "",
        "receivedAt": now,
        "sentAt": now,
        "isRead": True,
        "direction": "inbound",
        "attachments": [{
            "filename": "doc.pdf",
            "mimeType": "application/pdf",
            "size": 12,
            "providerAttachmentId": aid,
            "providerMessageId": "pm-att",
        }],
        "providerLabels": [],
        "createdAt": now,
        "updatedAt": now,
    })
    assert client.get(
        f"/api/inbox/messages/{mid}/attachments/{aid}",
        headers=_auth(b["accessToken"]),
    ).status_code == 404

    with patch("inbox.gmail.download_attachment", new_callable=AsyncMock, return_value=(b"%PDF-1.4", "application/pdf")):
        r = client.get(
            f"/api/inbox/messages/{mid}/attachments/{aid}",
            headers=_auth(a["accessToken"]),
        )
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")


def test_sync_lock_via_api(client, mongo):
    owner, _ = _register(client)
    h = _auth(owner["accessToken"])
    mb_id, _ = _seed_google(mongo, owner)

    @asynccontextmanager
    async def _busy(*_a, **_k):
        raise RuntimeError("Sync already in progress for this mailbox")
        yield  # pragma: no cover

    with patch("inbox.sync_service.mailbox_sync_lock", _busy):
        r = client.post(f"/api/inbox/mailboxes/{mb_id}/sync", headers=h)
    assert r.status_code == 409


def test_inbox_events_catalog(client):
    owner, _ = _register(client)
    r = client.get("/api/inbox/events/catalog", headers=_auth(owner["accessToken"]))
    assert r.status_code == 200
    kinds = {e["kind"] for e in r.json()["events"]}
    assert "inbound_message_received" in kinds
    assert "message_linked_to_client" in kinds
    assert "thread_created" in kinds
