"""Shared business inbox API (Gmail + Outlook)."""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from audit import write_audit
from core import db, now_iso, ai_service
from dependencies import current_user, current_org, rate_limit
from inbox import gmail as gmail_sync
from inbox import outlook as outlook_sync
from inbox.events import INBOX_EVENTS, record_inbox_event
from inbox.locks import is_syncing
from inbox.sanitize import normalize_email, sanitize_html, html_to_text
from inbox.sync_service import ensure_mailbox, sync_mailbox
from integrations import store
from integrations.providers import get_provider
from permissions import normalize_role, require_admin, role_at_least
from routers.emails import create_outbound_email, get_org_email_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/inbox")

MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024


def _public_mailbox(m: dict) -> dict:
    if not m:
        return m
    out = {k: v for k, v in m.items() if k != "_id"}
    out["isSyncing"] = is_syncing(m["organizationId"], m["id"]) if m.get("id") else False
    return out


def _public_thread(t: dict) -> dict:
    return {k: v for k, v in (t or {}).items() if k != "_id"}


def _public_message(m: dict, *, include_body: bool = True) -> dict:
    if not m:
        return m
    out = {k: v for k, v in m.items() if k != "_id"}
    if not include_body:
        out.pop("textBody", None)
        out.pop("sanitizedHtmlBody", None)
    return out


class MailboxPatch(BaseModel):
    syncEnabled: Optional[bool] = None
    displayName: Optional[str] = None


class ThreadPatch(BaseModel):
    assignedUserId: Optional[str] = None
    status: Optional[str] = None
    isRead: Optional[bool] = None


class LinkBody(BaseModel):
    clientId: Optional[str] = None
    leadId: Optional[str] = None
    contactId: Optional[str] = None


class EnsureBody(BaseModel):
    provider: str  # google | microsoft


# ---------- mailboxes ----------
@router.get("/mailboxes")
async def list_mailboxes(org: str = Depends(current_org), user: dict = Depends(current_user)):
    items = await db.mailboxes.find({"organizationId": org}, {"_id": 0}).sort("provider", 1).to_list(20)
    return {"items": [_public_mailbox(i) for i in items]}


@router.post("/mailboxes/ensure")
async def ensure_mailbox_route(
    payload: EnsureBody,
    org: str = Depends(current_org),
    user: dict = Depends(require_admin),
):
    provider = (payload.provider or "").lower()
    if provider not in ("google", "microsoft"):
        raise HTTPException(status_code=400, detail="provider must be google or microsoft")
    try:
        mb = await ensure_mailbox(org, provider, user_id=user.get("id"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await write_audit(org, "inbox_mailbox_ensured", actor_id=user.get("id"), actor_email=user.get("email"), meta={"provider": provider, "mailboxId": mb["id"]})
    return _public_mailbox(mb)


@router.patch("/mailboxes/{mailbox_id}")
async def patch_mailbox(
    mailbox_id: str,
    payload: MailboxPatch,
    org: str = Depends(current_org),
    user: dict = Depends(require_admin),
):
    mb = await db.mailboxes.find_one({"id": mailbox_id, "organizationId": org}, {"_id": 0})
    if not mb:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    updates = {}
    if payload.syncEnabled is not None:
        updates["syncEnabled"] = bool(payload.syncEnabled)
    if payload.displayName is not None:
        updates["displayName"] = payload.displayName[:120]
    if updates:
        updates["updatedAt"] = now_iso()
        await db.mailboxes.update_one({"id": mailbox_id, "organizationId": org}, {"$set": updates})
    return _public_mailbox(await db.mailboxes.find_one({"id": mailbox_id}, {"_id": 0}))


@router.post("/mailboxes/{mailbox_id}/sync")
async def sync_mailbox_route(
    mailbox_id: str,
    force_full: bool = False,
    org: str = Depends(current_org),
    user: dict = Depends(require_admin),
):
    rate_limit(f"inbox-sync:{org}:{user['id']}", 10, 3600)
    try:
        result = await sync_mailbox(org, mailbox_id, user=user, force_full=force_full)
    except RuntimeError as e:
        if "already in progress" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e)) from e
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    mb = await db.mailboxes.find_one({"id": mailbox_id, "organizationId": org}, {"_id": 0})
    result["mailbox"] = _public_mailbox(mb)
    return result


# ---------- threads ----------
@router.get("/threads")
async def list_threads(
    provider: Optional[str] = None,
    mailbox_id: Optional[str] = None,
    unread: Optional[bool] = None,
    assigned: Optional[str] = None,  # me | user id | none
    linked: Optional[bool] = None,
    client_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    org: str = Depends(current_org),
    user: dict = Depends(current_user),
):
    query: dict = {"organizationId": org}
    if provider:
        query["provider"] = provider.lower()
    if mailbox_id:
        query["mailboxId"] = mailbox_id
    if unread is True:
        query["unreadCount"] = {"$gt": 0}
    elif unread is False:
        query["unreadCount"] = 0
    if assigned == "me":
        query["assignedUserId"] = user["id"]
    elif assigned == "none":
        query["$or"] = [{"assignedUserId": None}, {"assignedUserId": {"$exists": False}}]
    elif assigned:
        query["assignedUserId"] = assigned
    if linked is True:
        query["$or"] = [
            {"linkedClientId": {"$nin": [None, ""]}},
            {"linkedLeadId": {"$nin": [None, ""]}},
        ]
    elif linked is False:
        query["linkedClientId"] = None
        query["linkedLeadId"] = None
        query["status"] = {"$in": ["unlinked", None]}
    if client_id:
        query["linkedClientId"] = client_id
    if lead_id:
        query["linkedLeadId"] = lead_id
    if status:
        query["status"] = status
    if date_from or date_to:
        rng = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            rng["$lte"] = date_to
        query["latestMessageAt"] = rng
    if q:
        query["$and"] = query.get("$and", []) + [{"$or": [
            {"subject": {"$regex": q, "$options": "i"}},
            {"snippet": {"$regex": q, "$options": "i"}},
            {"participantEmails": {"$regex": q, "$options": "i"}},
        ]}]

    total = await db.email_threads.count_documents(query)
    skip = (page - 1) * page_size
    items = await db.email_threads.find(query, {"_id": 0}).sort("latestMessageAt", -1).skip(skip).limit(page_size).to_list(page_size)
    return {
        "items": [_public_thread(i) for i in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str, org: str = Depends(current_org), user: dict = Depends(current_user)):
    t = await db.email_threads.find_one({"id": thread_id, "organizationId": org}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    mailbox = await db.mailboxes.find_one({"id": t["mailboxId"], "organizationId": org}, {"_id": 0})
    return {"thread": _public_thread(t), "mailbox": _public_mailbox(mailbox) if mailbox else None}


@router.patch("/threads/{thread_id}")
async def patch_thread(
    thread_id: str,
    payload: ThreadPatch,
    org: str = Depends(current_org),
    user: dict = Depends(current_user),
):
    t = await db.email_threads.find_one({"id": thread_id, "organizationId": org}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    updates = {}
    if payload.assignedUserId is not None:
        if not role_at_least(user.get("role"), "admin") and payload.assignedUserId not in (user["id"], ""):
            # members may assign to self only
            if payload.assignedUserId != user["id"]:
                raise HTTPException(status_code=403, detail="Members can only assign conversations to themselves")
        updates["assignedUserId"] = payload.assignedUserId or None
    if payload.status is not None:
        updates["status"] = payload.status[:40]
    if payload.isRead is not None:
        if payload.isRead:
            updates["unreadCount"] = 0
            await db.inbound_messages.update_many(
                {"threadId": thread_id, "organizationId": org},
                {"$set": {"isRead": True, "updatedAt": now_iso()}},
            )
        else:
            updates["unreadCount"] = max(1, t.get("unreadCount") or 1)
    if updates:
        updates["updatedAt"] = now_iso()
        await db.email_threads.update_one({"id": thread_id, "organizationId": org}, {"$set": updates})
    return _public_thread(await db.email_threads.find_one({"id": thread_id}, {"_id": 0}))


@router.get("/threads/{thread_id}/messages")
async def list_messages(thread_id: str, org: str = Depends(current_org), user: dict = Depends(current_user)):
    t = await db.email_threads.find_one({"id": thread_id, "organizationId": org}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    msgs = await db.inbound_messages.find(
        {"threadId": thread_id, "organizationId": org}, {"_id": 0},
    ).sort("receivedAt", 1).to_list(500)
    # Outbound replies linked to this thread (sent or delivery-unknown for visibility)
    outbound = await db.outbound_emails.find(
        {
            "organizationId": org,
            "inboxThreadId": thread_id,
            "status": {"$in": ["sent", "delivery_unknown", "needs_review"]},
        },
        {"_id": 0, "versions": 0},
    ).sort("sentAt", 1).to_list(100)
    timeline = []
    for m in msgs:
        timeline.append({"kind": "inbound", **_public_message(m)})
    for o in outbound:
        timeline.append({
            "kind": "outbound",
            "id": o["id"],
            "subject": o.get("subject"),
            "textBody": o.get("textBody"),
            "to": o.get("to"),
            "sentAt": o.get("sentAt"),
            "status": o.get("status"),
            "provider": o.get("provider") or o.get("sentVia"),
            "sentVia": o.get("sentVia") or o.get("transportProvider"),
            "providerMessageId": o.get("providerMessageId"),
            "deliveryWarning": o.get("status") in ("delivery_unknown", "needs_review"),
            "failureReason": o.get("failureReason"),
            "failureActionable": o.get("failureActionable"),
        })
    timeline.sort(key=lambda x: x.get("receivedAt") or x.get("sentAt") or "")
    return {"thread": _public_thread(t), "messages": [_public_message(m) for m in msgs], "timeline": timeline}


@router.post("/threads/{thread_id}/link")
async def link_thread(thread_id: str, payload: LinkBody, org: str = Depends(current_org), user: dict = Depends(current_user)):
    t = await db.email_threads.find_one({"id": thread_id, "organizationId": org}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    updates = {"updatedAt": now_iso(), "status": "linked"}
    if payload.clientId:
        client = await db.clients.find_one({"id": payload.clientId, "organizationId": org}, {"_id": 0, "id": 1})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        updates["linkedClientId"] = payload.clientId
        updates["linkedContactId"] = payload.contactId or payload.clientId
        await record_inbox_event(org, "message_linked_to_client", thread_id=thread_id, mailbox_id=t["mailboxId"], meta={"clientId": payload.clientId})
    if payload.leadId:
        lead = await db.leads.find_one({"id": payload.leadId, "organizationId": org}, {"_id": 0, "id": 1})
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        updates["linkedLeadId"] = payload.leadId
        await record_inbox_event(org, "message_linked_to_lead", thread_id=thread_id, mailbox_id=t["mailboxId"], meta={"leadId": payload.leadId})
    if not payload.clientId and not payload.leadId:
        raise HTTPException(status_code=400, detail="Provide clientId or leadId")
    await db.email_threads.update_one({"id": thread_id, "organizationId": org}, {"$set": updates})
    return _public_thread(await db.email_threads.find_one({"id": thread_id}, {"_id": 0}))


@router.delete("/threads/{thread_id}/link")
async def unlink_thread(thread_id: str, org: str = Depends(current_org), user: dict = Depends(current_user)):
    t = await db.email_threads.find_one({"id": thread_id, "organizationId": org}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    await db.email_threads.update_one(
        {"id": thread_id, "organizationId": org},
        {"$set": {
            "linkedClientId": None, "linkedLeadId": None, "linkedContactId": None,
            "status": "unlinked", "updatedAt": now_iso(),
        }},
    )
    return _public_thread(await db.email_threads.find_one({"id": thread_id}, {"_id": 0}))


@router.post("/threads/{thread_id}/summarize")
async def summarize_thread(thread_id: str, org: str = Depends(current_org), user: dict = Depends(current_user)):
    rate_limit(f"inbox-ai:{user['id']}", 30, 3600)
    t = await db.email_threads.find_one({"id": thread_id, "organizationId": org}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    msgs = await db.inbound_messages.find(
        {"threadId": thread_id, "organizationId": org},
        {"_id": 0, "from": 1, "subject": 1, "textBody": 1, "receivedAt": 1},
    ).sort("receivedAt", 1).to_list(40)
    transcript = "\n\n".join(
        f"From: {m.get('from')}\nDate: {m.get('receivedAt')}\n{(m.get('textBody') or '')[:3000]}"
        for m in msgs
    )[:20000]
    prompt = (
        f"Thread subject: {t.get('subject')}\n"
        f"Linked client: {t.get('linkedClientId') or 'none'}; lead: {t.get('linkedLeadId') or 'none'}\n\n"
        f"Messages:\n{transcript}\n\n"
        "Return JSON with keys: summary, intent, urgency, sentiment, requestedActions (list), "
        "openQuestions (list), suggestedNextStep."
    )
    try:
        data = await ai_service.complete_json(
            "You summarize business email threads. Be concise and factual. Return only JSON.",
            prompt,
            [
                {"key": "summary", "type": "text"},
                {"key": "intent", "type": "text"},
                {"key": "urgency", "type": "text"},
                {"key": "sentiment", "type": "text"},
                {"key": "requestedActions", "type": "list"},
                {"key": "openQuestions", "type": "list"},
                {"key": "suggestedNextStep", "type": "text"},
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI summary failed: {e}") from e

    summary = {
        "summary": data.get("summary") or "",
        "intent": data.get("intent") or "",
        "urgency": data.get("urgency") or "",
        "sentiment": data.get("sentiment") or "",
        "requestedActions": data.get("requestedActions") or [],
        "openQuestions": data.get("openQuestions") or [],
        "suggestedNextStep": data.get("suggestedNextStep") or "",
    }
    await db.email_threads.update_one(
        {"id": thread_id, "organizationId": org},
        {"$set": {"aiSummary": summary, "aiSummaryUpdatedAt": now_iso(), "updatedAt": now_iso()}},
    )
    await write_audit(org, "inbox_thread_summarized", actor_id=user.get("id"), actor_email=user.get("email"), meta={"threadId": thread_id})
    return {"threadId": thread_id, "aiSummary": summary}


@router.post("/threads/{thread_id}/draft-reply")
async def draft_reply(thread_id: str, org: str = Depends(current_org), user: dict = Depends(current_user)):
    rate_limit(f"inbox-ai:{user['id']}", 30, 3600)
    t = await db.email_threads.find_one({"id": thread_id, "organizationId": org}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    mailbox = await db.mailboxes.find_one({"id": t["mailboxId"], "organizationId": org}, {"_id": 0})
    msgs = await db.inbound_messages.find(
        {"threadId": thread_id, "organizationId": org},
        {"_id": 0},
    ).sort("receivedAt", 1).to_list(40)
    if not msgs:
        raise HTTPException(status_code=400, detail="Thread has no messages")
    last = msgs[-1]
    # Context
    client_ctx = ""
    if t.get("linkedClientId"):
        c = await db.clients.find_one({"id": t["linkedClientId"], "organizationId": org}, {"_id": 0, "name": 1, "email": 1})
        if c:
            client_ctx = f"Client: {c.get('name')} <{c.get('email')}>"
    org_doc = await db.organizations.find_one({"id": org}, {"_id": 0, "name": 1, "settings": 1})
    org_name = (org_doc or {}).get("name") or "our company"
    sig = ((org_doc or {}).get("settings") or {}).get("email", {}).get("companySignature") or ""

    transcript = "\n\n".join(
        f"From: {m.get('from')}\n{(m.get('textBody') or '')[:2500]}" for m in msgs[-8:]
    )[:12000]
    prompt = (
        f"Write a professional reply email for {org_name}.\n"
        f"{client_ctx}\nSubject was: {t.get('subject')}\n"
        f"Latest sender: {last.get('from')}\n\nThread:\n{transcript}\n\n"
        "Do not invent facts. Return JSON with keys subject, body (plain text)."
    )
    try:
        data = await ai_service.complete_json(
            "You draft concise professional email replies. Return only JSON.",
            prompt,
            [{"key": "subject", "type": "text"}, {"key": "body", "type": "text"}],
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI draft failed: {e}") from e

    subject = (data.get("subject") or t.get("subject") or "Re:").strip()
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    body = (data.get("body") or "").strip()
    if sig and sig not in body:
        body = f"{body}\n\n{sig}"

    to_addr = last.get("from") or (t.get("participantEmails") or [None])[0]
    if not to_addr:
        raise HTTPException(status_code=400, detail="No recipient for reply")

    org_email = await get_org_email_settings(org)
    status = "pending_approval" if org_email.get("approvalRequired") else "draft"
    original_ai = {"subject": subject, "textBody": body, "htmlBody": ""}

    # Build threading headers from last inbound
    in_reply_to = last.get("internetMessageId")
    references = last.get("references") or last.get("internetMessageId")

    doc = await create_outbound_email(
        org_id=org,
        user=user,
        to=[to_addr],
        subject=subject,
        text_body=body,
        source="ai",
        client_id=t.get("linkedClientId"),
        lead_id=t.get("linkedLeadId"),
        contact_id=t.get("linkedContactId"),
        original_ai=original_ai,
        status=status,
        inbox_thread_id=thread_id,
        mailbox_id=t.get("mailboxId"),
        provider_thread_id=t.get("providerThreadId"),
        in_reply_to=in_reply_to,
        references=references,
        reply_provider=(mailbox or {}).get("provider"),
    )
    await write_audit(
        org, "inbox_reply_draft_created",
        actor_id=user.get("id"), actor_email=user.get("email"),
        meta={"threadId": thread_id, "emailId": doc["id"]},
    )
    return {"email": doc, "threadId": thread_id}


# ---------- attachments ----------
@router.get("/messages/{message_id}/attachments/{attachment_id}")
async def download_attachment(
    message_id: str,
    attachment_id: str,
    org: str = Depends(current_org),
    user: dict = Depends(current_user),
):
    msg = await db.inbound_messages.find_one({"id": message_id, "organizationId": org}, {"_id": 0})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    meta = next((a for a in (msg.get("attachments") or []) if a.get("providerAttachmentId") == attachment_id), None)
    if not meta:
        raise HTTPException(status_code=404, detail="Attachment not found")
    size = int(meta.get("size") or 0)
    if size > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=400, detail="Attachment exceeds maximum download size")

    mailbox = await db.mailboxes.find_one({"id": msg["mailboxId"], "organizationId": org}, {"_id": 0})
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    filename = re.sub(r"[^\w.\- ()]", "_", meta.get("filename") or "attachment")[:180]
    raw = b""
    mime = meta.get("mimeType") or "application/octet-stream"
    try:
        if mailbox["provider"] == "google":
            integ = await store.get_by_provider(org, "google")
            if not integ:
                raise RuntimeError("Google is not connected")
            creds = await store.load_credentials(integ)
            if not creds.get("access_token") and creds.get("refresh_token"):
                creds = await get_provider("google").refresh(creds)
                await store.save_credentials(org, integ["id"], creds)
            raw, dl_mime = await gmail_sync.download_attachment(
                creds["access_token"], msg["providerMessageId"], attachment_id,
            )
            mime = meta.get("mimeType") or dl_mime
        elif mailbox["provider"] == "microsoft":
            integ = await store.get_by_provider(org, "microsoft")
            if not integ:
                raise RuntimeError("Microsoft is not connected")
            creds = await store.load_credentials(integ)
            if not creds.get("access_token") and creds.get("refresh_token"):
                creds = await get_provider("microsoft").refresh(creds)
                await store.save_credentials(org, integ["id"], creds)
            raw, dl_mime, name = await outlook_sync.download_attachment(
                creds["access_token"], msg["providerMessageId"], attachment_id,
            )
            filename = re.sub(r"[^\w.\- ()]", "_", name or filename)[:180]
            mime = dl_mime or meta.get("mimeType") or "application/octet-stream"
        else:
            raise HTTPException(status_code=400, detail="Unsupported mailbox provider")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {e}") from e

    if len(raw) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=400, detail="Attachment exceeds maximum download size")

    return Response(
        content=raw,
        media_type=mime or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


_EVENT_DESCRIPTIONS = {
    "inbound_message_received": "A new inbound message was synchronized into the shared inbox.",
    "thread_created": "A new conversation thread was created from inbound mail.",
    "unread_message_received": "An unread inbound message was synchronized.",
    "message_linked_to_client": "A thread was linked to a client (auto-match or manual).",
    "message_linked_to_lead": "A thread was linked to a lead (auto-match or manual).",
}


@router.get("/events/catalog")
async def inbox_event_catalog(user: dict = Depends(current_user)):
    return {
        "events": [
            {"kind": e, "description": _EVENT_DESCRIPTIONS.get(e, e)}
            for e in INBOX_EVENTS
        ],
    }
