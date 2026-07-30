"""Reusable inbox synchronization service (HTTP-independent)."""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from audit import write_audit
from core import db, now_iso
from inbox import gmail as gmail_sync
from inbox import outlook as outlook_sync
from inbox.events import record_inbox_event
from inbox.locks import mailbox_sync_lock
from inbox.matching import match_sender
from inbox.sanitize import normalize_email
from integrations import store
from integrations.providers import get_provider

logger = logging.getLogger(__name__)

DEFAULT_PAGE_LIMIT = 40
MAX_MESSAGES_PER_SYNC = 80


async def _google_token(org_id: str) -> tuple[dict, dict]:
    doc = await store.get_by_provider(org_id, "google")
    if not doc or doc.get("status") not in ("connected", "error"):
        raise RuntimeError("Google Workspace is not connected")
    creds = await store.load_credentials(doc)
    if not creds.get("access_token") and creds.get("refresh_token"):
        provider = get_provider("google")
        creds = await provider.refresh(creds)
        await store.save_credentials(org_id, doc["id"], creds, status="connected")
    if not creds.get("access_token"):
        raise RuntimeError("Google access token missing — reconnect the integration")
    return doc, creds


async def _microsoft_token(org_id: str) -> tuple[dict, dict]:
    doc = await store.get_by_provider(org_id, "microsoft")
    if not doc or doc.get("status") not in ("connected", "error"):
        raise RuntimeError("Microsoft 365 is not connected")
    creds = await store.load_credentials(doc)
    if not creds.get("access_token") and creds.get("refresh_token"):
        provider = get_provider("microsoft")
        creds = await provider.refresh(creds)
        await store.save_credentials(org_id, doc["id"], creds, status="connected")
    if not creds.get("access_token"):
        raise RuntimeError("Microsoft access token missing — reconnect the integration")
    return doc, creds


async def ensure_mailbox(org_id: str, provider: str, user_id: str = None) -> dict:
    """Discover provider account and upsert mailbox row."""
    provider = provider.lower()
    if provider == "google":
        integ, creds = await _google_token(org_id)
        account = await gmail_sync.discover_account(creds["access_token"])
    elif provider == "microsoft":
        integ, creds = await _microsoft_token(org_id)
        account = await outlook_sync.discover_account(creds["access_token"])
    else:
        raise ValueError(f"Unsupported inbox provider: {provider}")

    existing = await db.mailboxes.find_one({
        "organizationId": org_id,
        "provider": provider,
        "providerAccountId": account["providerAccountId"] or account["emailAddress"],
    }, {"_id": 0})
    now = now_iso()
    if existing:
        await db.mailboxes.update_one(
            {"id": existing["id"], "organizationId": org_id},
            {"$set": {
                "emailAddress": account["emailAddress"],
                "displayName": account.get("displayName") or account["emailAddress"],
                "integrationId": integ["id"],
                "updatedAt": now,
            }},
        )
        return await db.mailboxes.find_one({"id": existing["id"]}, {"_id": 0})

    doc = {
        "id": str(uuid.uuid4()),
        "organizationId": org_id,
        "provider": provider,
        "integrationId": integ["id"],
        "providerAccountId": account["providerAccountId"] or account["emailAddress"],
        "emailAddress": account["emailAddress"],
        "displayName": account.get("displayName") or account["emailAddress"],
        "syncEnabled": True,
        "syncStatus": "idle",
        "lastSyncAt": None,
        "lastSuccessfulSyncAt": None,
        "lastError": None,
        "syncCursor": account.get("historyId") or None,
        "createdAt": now,
        "updatedAt": now,
        "createdBy": user_id,
    }
    await db.mailboxes.insert_one(dict(doc))
    return doc


async def _upsert_message(org_id: str, mailbox: dict, parsed: dict) -> tuple[dict, bool]:
    """Insert message if new. Returns (message_doc, created)."""
    # Dedup by providerMessageId OR internetMessageId within org/mailbox
    existing = await db.inbound_messages.find_one({
        "organizationId": org_id,
        "mailboxId": mailbox["id"],
        "$or": [
            {"providerMessageId": parsed["providerMessageId"]},
            *([{ "internetMessageId": parsed["internetMessageId"] }] if parsed.get("internetMessageId") else []),
        ],
    }, {"_id": 0})
    if existing:
        return existing, False

    # Also skip if this was our outbound (same internet message id or provider message id)
    outbound_q = [{"providerMessageId": parsed["providerMessageId"]}]
    if parsed.get("internetMessageId"):
        mid = (parsed.get("internetMessageId") or "").strip()
        outbound_q.extend([
            {"internetMessageId": mid},
            {"internetMessageId": mid.strip("<>")},
            {"internetMessageId": f"<{mid.strip('<>')}>"},
        ])
    outbound = await db.outbound_emails.find_one(
        {"organizationId": org_id, "$or": outbound_q},
        {"_id": 0, "id": 1},
    )
    if outbound:
        return {"id": None, "skippedOutbound": True}, False

    match = await match_sender(org_id, parsed.get("from") or "")
    now = now_iso()
    thread = await _ensure_thread(org_id, mailbox, parsed, match)

    msg = {
        "id": str(uuid.uuid4()),
        "organizationId": org_id,
        "mailboxId": mailbox["id"],
        "threadId": thread["id"],
        "providerMessageId": parsed["providerMessageId"],
        "providerThreadId": parsed["providerThreadId"],
        "internetMessageId": parsed.get("internetMessageId"),
        "inReplyTo": parsed.get("inReplyTo"),
        "references": parsed.get("references"),
        "from": parsed.get("from"),
        "fromRaw": parsed.get("fromRaw"),
        "to": parsed.get("to") or [],
        "cc": parsed.get("cc") or [],
        "bcc": parsed.get("bcc") or [],
        "subject": parsed.get("subject"),
        "textBody": parsed.get("textBody") or "",
        "sanitizedHtmlBody": parsed.get("sanitizedHtmlBody") or "",
        "snippet": parsed.get("snippet") or "",
        "receivedAt": parsed.get("receivedAt") or now,
        "sentAt": parsed.get("sentAt"),
        "isRead": bool(parsed.get("isRead")),
        "direction": "inbound",
        "attachments": parsed.get("attachments") or [],
        "providerLabels": parsed.get("providerLabels") or [],
        "createdAt": now,
        "updatedAt": now,
    }
    try:
        await db.inbound_messages.insert_one(dict(msg))
    except Exception:
        # unique index race
        existing = await db.inbound_messages.find_one({
            "organizationId": org_id,
            "mailboxId": mailbox["id"],
            "providerMessageId": parsed["providerMessageId"],
        }, {"_id": 0})
        return existing or msg, False

    # Update thread counters
    unread_inc = 0 if msg["isRead"] else 1
    await db.email_threads.update_one(
        {"id": thread["id"], "organizationId": org_id},
        {"$inc": {"messageCount": 1, "unreadCount": unread_inc},
         "$set": {
             "latestMessageAt": msg["receivedAt"],
             "subject": msg["subject"] or thread.get("subject"),
             "updatedAt": now,
             "snippet": msg["snippet"],
         },
         "$addToSet": {"participantEmails": {"$each": list(filter(None, [msg.get("from"), *(msg.get("to") or [])]))}}},
    )
    await record_inbox_event(
        org_id, "inbound_message_received",
        mailbox_id=mailbox["id"], thread_id=thread["id"], message_id=msg["id"],
        meta={"provider": mailbox["provider"], "from": msg.get("from")},
    )
    if unread_inc:
        await record_inbox_event(
            org_id, "unread_message_received",
            mailbox_id=mailbox["id"], thread_id=thread["id"], message_id=msg["id"],
        )
    if match.get("matchType") == "client":
        await record_inbox_event(
            org_id, "message_linked_to_client",
            mailbox_id=mailbox["id"], thread_id=thread["id"], message_id=msg["id"],
            meta={"clientId": match.get("clientId")},
        )
    elif match.get("matchType") == "lead":
        await record_inbox_event(
            org_id, "message_linked_to_lead",
            mailbox_id=mailbox["id"], thread_id=thread["id"], message_id=msg["id"],
            meta={"leadId": match.get("leadId")},
        )
    return msg, True


async def _ensure_thread(org_id: str, mailbox: dict, parsed: dict, match: dict) -> dict:
    existing = await db.email_threads.find_one({
        "organizationId": org_id,
        "mailboxId": mailbox["id"],
        "providerThreadId": parsed["providerThreadId"],
    }, {"_id": 0})
    if existing:
        updates = {}
        if match.get("clientId") and not existing.get("linkedClientId"):
            updates["linkedClientId"] = match["clientId"]
            updates["linkedContactId"] = match.get("contactId")
            updates["status"] = existing.get("status") if existing.get("status") != "unlinked" else "linked"
        if match.get("leadId") and not existing.get("linkedLeadId"):
            updates["linkedLeadId"] = match["leadId"]
            updates["status"] = existing.get("status") if existing.get("status") != "unlinked" else "linked"
        if updates:
            updates["updatedAt"] = now_iso()
            await db.email_threads.update_one({"id": existing["id"]}, {"$set": updates})
            existing.update(updates)
        return existing

    now = now_iso()
    status = "linked" if match.get("matchType") else "unlinked"
    thread = {
        "id": str(uuid.uuid4()),
        "organizationId": org_id,
        "mailboxId": mailbox["id"],
        "provider": mailbox["provider"],
        "providerThreadId": parsed["providerThreadId"],
        "subject": parsed.get("subject") or "(no subject)",
        "participantEmails": list(filter(None, [parsed.get("from"), *(parsed.get("to") or [])])),
        "latestMessageAt": parsed.get("receivedAt") or now,
        "messageCount": 0,
        "unreadCount": 0,
        "status": status,
        "linkedClientId": match.get("clientId"),
        "linkedLeadId": match.get("leadId"),
        "linkedContactId": match.get("contactId"),
        "assignedUserId": None,
        "labels": [],
        "aiSummary": None,
        "aiSummaryUpdatedAt": None,
        "snippet": parsed.get("snippet") or "",
        "createdAt": now,
        "updatedAt": now,
    }
    await db.email_threads.insert_one(dict(thread))
    await record_inbox_event(
        org_id, "thread_created",
        mailbox_id=mailbox["id"], thread_id=thread["id"],
        meta={"provider": mailbox["provider"]},
    )
    return thread


async def sync_mailbox(
    org_id: str,
    mailbox_id: str,
    *,
    user: dict = None,
    force_full: bool = False,
    max_messages: int = MAX_MESSAGES_PER_SYNC,
) -> dict:
    mailbox = await db.mailboxes.find_one({"id": mailbox_id, "organizationId": org_id}, {"_id": 0})
    if not mailbox:
        raise ValueError("Mailbox not found")
    if not mailbox.get("syncEnabled", True):
        raise RuntimeError("Sync is disabled for this mailbox")

    async with mailbox_sync_lock(org_id, mailbox_id):
        await db.mailboxes.update_one(
            {"id": mailbox_id, "organizationId": org_id},
            {"$set": {"syncStatus": "syncing", "lastSyncAt": now_iso(), "lastError": None, "updatedAt": now_iso()}},
        )
        created = 0
        scanned = 0
        cursor_reset = False
        try:
            if mailbox["provider"] == "google":
                created, scanned, cursor_reset = await _sync_gmail(org_id, mailbox, force_full=force_full, max_messages=max_messages)
            elif mailbox["provider"] == "microsoft":
                created, scanned, cursor_reset = await _sync_outlook(org_id, mailbox, force_full=force_full, max_messages=max_messages)
            else:
                raise ValueError(f"Unsupported provider {mailbox['provider']}")

            await db.mailboxes.update_one(
                {"id": mailbox_id, "organizationId": org_id},
                {"$set": {
                    "syncStatus": "idle",
                    "lastSuccessfulSyncAt": now_iso(),
                    "lastSyncAt": now_iso(),
                    "lastError": None,
                    "updatedAt": now_iso(),
                }},
            )
            if user:
                await write_audit(
                    org_id, "inbox_sync_completed",
                    actor_id=user.get("id"), actor_email=user.get("email"),
                    meta={"mailboxId": mailbox_id, "created": created, "scanned": scanned, "cursorReset": cursor_reset},
                )
            return {
                "ok": True,
                "mailboxId": mailbox_id,
                "provider": mailbox["provider"],
                "messagesScanned": scanned,
                "messagesCreated": created,
                "cursorReset": cursor_reset,
            }
        except Exception as e:
            logger.exception("Inbox sync failed mailbox=%s", mailbox_id)
            await db.mailboxes.update_one(
                {"id": mailbox_id, "organizationId": org_id},
                {"$set": {
                    "syncStatus": "error",
                    "lastError": str(e)[:500],
                    "lastSyncAt": now_iso(),
                    "updatedAt": now_iso(),
                }},
            )
            if user:
                await write_audit(
                    org_id, "inbox_sync_failed",
                    actor_id=user.get("id"), actor_email=user.get("email"),
                    meta={"mailboxId": mailbox_id, "error": str(e)[:200]},
                )
            raise


async def _refresh_google_if_needed(org_id: str, creds: dict, integ: dict) -> dict:
    try:
        return creds
    finally:
        pass


async def _sync_gmail(org_id: str, mailbox: dict, *, force_full: bool, max_messages: int) -> tuple[int, int, bool]:
    integ, creds = await _google_token(org_id)
    token = creds["access_token"]
    created = 0
    scanned = 0
    cursor_reset = False
    message_ids: list = []

    cursor = None if force_full else mailbox.get("syncCursor")
    if cursor:
        try:
            ids, new_hist, invalid = await gmail_sync.history_message_ids(token, cursor, max_results=max_messages)
            if invalid:
                cursor_reset = True
                message_ids = []
            else:
                message_ids = ids
                if new_hist:
                    await db.mailboxes.update_one(
                        {"id": mailbox["id"]}, {"$set": {"syncCursor": new_hist}},
                    )
        except PermissionError:
            provider = get_provider("google")
            creds = await provider.refresh(creds)
            await store.save_credentials(org_id, integ["id"], creds)
            token = creds["access_token"]
            ids, new_hist, invalid = await gmail_sync.history_message_ids(token, cursor, max_results=max_messages)
            if invalid:
                cursor_reset = True
            else:
                message_ids = ids
                if new_hist:
                    await db.mailboxes.update_one({"id": mailbox["id"]}, {"$set": {"syncCursor": new_hist}})

    if not cursor or cursor_reset or force_full:
        # Initial / fallback list
        page_token = None
        message_ids = []
        while len(message_ids) < max_messages:
            batch, page_token, _ = await gmail_sync.list_inbox_message_ids(
                token, max_results=min(50, max_messages - len(message_ids)), page_token=page_token,
            )
            message_ids.extend(batch)
            if not page_token or not batch:
                break
        # Refresh history cursor from profile
        account = await gmail_sync.discover_account(token)
        if account.get("historyId"):
            await db.mailboxes.update_one(
                {"id": mailbox["id"]}, {"$set": {"syncCursor": account["historyId"]}},
            )

    parsed_list = await gmail_sync.fetch_messages_batch(token, message_ids, limit=max_messages)
    for parsed in parsed_list:
        scanned += 1
        _, was_created = await _upsert_message(org_id, mailbox, parsed)
        if was_created:
            created += 1
    return created, scanned, cursor_reset


async def _sync_outlook(org_id: str, mailbox: dict, *, force_full: bool, max_messages: int) -> tuple[int, int, bool]:
    integ, creds = await _microsoft_token(org_id)
    token = creds["access_token"]
    created = 0
    scanned = 0
    cursor_reset = False
    messages = []

    delta = None if force_full else mailbox.get("syncCursor")
    if delta and not force_full:
        try:
            msgs, new_link, invalid = await outlook_sync.delta_inbox(token, delta_link=delta, top=max_messages)
            if invalid:
                cursor_reset = True
            else:
                messages = msgs
                if new_link:
                    await db.mailboxes.update_one({"id": mailbox["id"]}, {"$set": {"syncCursor": new_link}})
        except PermissionError:
            provider = get_provider("microsoft")
            creds = await provider.refresh(creds)
            await store.save_credentials(org_id, integ["id"], creds)
            token = creds["access_token"]
            msgs, new_link, invalid = await outlook_sync.delta_inbox(token, delta_link=delta, top=max_messages)
            if invalid:
                cursor_reset = True
            else:
                messages = msgs
                if new_link:
                    await db.mailboxes.update_one({"id": mailbox["id"]}, {"$set": {"syncCursor": new_link}})

    if not delta or cursor_reset or force_full:
        messages = []
        next_url = None
        # Prefer delta without link for initial cursor, else list pages
        try:
            msgs, new_link, invalid = await outlook_sync.delta_inbox(token, delta_link=None, top=max_messages)
            if not invalid:
                messages = msgs
                if new_link:
                    await db.mailboxes.update_one({"id": mailbox["id"]}, {"$set": {"syncCursor": new_link}})
            else:
                raise RuntimeError("delta unavailable")
        except Exception:
            while len(messages) < max_messages:
                batch, next_url = await outlook_sync.list_inbox_page(
                    token, top=min(25, max_messages - len(messages)), skip_token_url=next_url,
                )
                messages.extend(batch)
                if not next_url or not batch:
                    break

    for parsed in messages[:max_messages]:
        scanned += 1
        _, was_created = await _upsert_message(org_id, mailbox, parsed)
        if was_created:
            created += 1
    return created, scanned, cursor_reset
