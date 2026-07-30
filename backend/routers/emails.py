"""Outbound email drafts, approval workflow, and safe sending.

Collection: outbound_emails (organization-scoped).
Provider keys never appear in responses.
"""
from __future__ import annotations

import html
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

from audit import write_audit
from config import get_settings
from core import db, now_iso, ai_service
from dependencies import current_user, current_org
from email_providers import EmailMessage, get_email_provider, outbound_sending_allowed
from inbox.transport import execute_native_send, resolve_transport, transport_public
from inbox.transport_errors import TransportError, AMBIGUOUS_DELIVERY, ACTIONABLE
from permissions import normalize_role, require_admin, role_at_least

router = APIRouter(prefix="/api/emails")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_RECIPIENTS = 20
EDITABLE = {"draft", "pending_approval", "approved", "rejected", "failed", "needs_review", "delivery_unknown"}
TERMINAL_SENT = {"sent", "sending"}
STATUSES = {
    "draft", "pending_approval", "approved", "scheduled",
    "sending", "sent", "failed", "cancelled", "rejected",
    "needs_review", "delivery_unknown",
}

DEFAULT_ORG_EMAIL = {
    "senderName": "",
    "senderEmail": "",
    "replyToEmail": "",
    "companySignature": "",
    "sendingEnabled": False,
    "dailySendingLimit": 50,
    "approvalRequired": True,
    "autoSendFromAutomation": False,
}


# ---------------- helpers ----------------
def normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def normalize_emails(values) -> List[str]:
    if not values:
        return []
    if isinstance(values, str):
        values = [v.strip() for v in values.replace(";", ",").split(",") if v.strip()]
    out, seen = [], set()
    for v in values:
        e = normalize_email(v)
        if not e:
            continue
        if not EMAIL_RE.match(e):
            raise HTTPException(status_code=400, detail=f"Invalid email address: {v}")
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def _text_to_html(text: str) -> str:
    return "<p>" + html.escape(text or "").replace("\n", "<br/>") + "</p>"


def _html_to_text(html_body: str) -> str:
    if not html_body:
        return ""
    t = re.sub(r"<br\s*/?>", "\n", html_body, flags=re.I)
    t = re.sub(r"</p\s*>", "\n\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(t).strip()


async def get_org_email_settings(org_id: str) -> dict:
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0, "settings.email": 1, "name": 1})
    raw = ((org or {}).get("settings") or {}).get("email") or {}
    merged = {**DEFAULT_ORG_EMAIL, **raw}
    # Clamp limit
    try:
        merged["dailySendingLimit"] = max(1, min(int(merged.get("dailySendingLimit") or 50), 10000))
    except (TypeError, ValueError):
        merged["dailySendingLimit"] = 50
    merged["orgName"] = (org or {}).get("name") or ""
    return merged


def public_email(doc: dict, *, include_preview: bool = False) -> dict:
    if not doc:
        return doc
    out = {k: v for k, v in doc.items() if k != "_id"}
    # Never expose secrets
    out.pop("idempotencyKey", None)
    if not include_preview:
        out.pop("consolePreview", None)
    return out


async def _creator_name(user_id: str) -> str:
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "firstName": 1, "lastName": 1, "email": 1})
    if not u:
        return ""
    name = f"{u.get('firstName', '')} {u.get('lastName', '')}".strip()
    return name or u.get("email") or ""


def _version_entry(user: dict, kind: str, subject: str, html_body: str, text_body: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "at": now_iso(),
        "by": user.get("id"),
        "byEmail": user.get("email"),
        "kind": kind,  # ai_suggestion | user_edit | submitted | approved | sent | system
        "subject": subject,
        "htmlBody": html_body,
        "textBody": text_body,
    }


async def create_outbound_email(
    *,
    org_id: str,
    user: dict,
    to: List[str],
    subject: str,
    html_body: str = "",
    text_body: str = "",
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    source: str = "manual",
    automation_id: Optional[str] = None,
    automation_approval_id: Optional[str] = None,
    client_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    original_ai: Optional[dict] = None,
    status: Optional[str] = None,
    inbox_thread_id: Optional[str] = None,
    mailbox_id: Optional[str] = None,
    provider_thread_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
    reply_provider: Optional[str] = None,
    internet_message_id: Optional[str] = None,
) -> dict:
    to_n = normalize_emails(to)
    cc_n = normalize_emails(cc)
    bcc_n = normalize_emails(bcc)
    if not to_n:
        raise HTTPException(status_code=400, detail="At least one recipient (to) is required")
    if len(to_n) + len(cc_n) + len(bcc_n) > MAX_RECIPIENTS:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_RECIPIENTS} recipients allowed")
    if not (subject or "").strip():
        raise HTTPException(status_code=400, detail="Subject is required")

    if not html_body and text_body:
        html_body = _text_to_html(text_body)
    if not text_body and html_body:
        text_body = _html_to_text(html_body)

    org_email = await get_org_email_settings(org_id)
    if status is None:
        status = "pending_approval" if org_email.get("approvalRequired") and source == "automation" else "draft"

    versions = []
    if original_ai:
        versions.append(_version_entry(
            user, "ai_suggestion",
            original_ai.get("subject") or subject,
            original_ai.get("htmlBody") or html_body,
            original_ai.get("textBody") or text_body,
        ))
    versions.append(_version_entry(user, "user_edit" if source == "manual" else "system", subject, html_body, text_body))

    doc = {
        "id": str(uuid.uuid4()),
        "organizationId": org_id,
        "createdBy": user["id"],
        "createdByName": await _creator_name(user["id"]) or user.get("email"),
        "createdByEmail": user.get("email"),
        "automationId": automation_id,
        "automationApprovalId": automation_approval_id,
        "clientId": client_id,
        "leadId": lead_id,
        "contactId": contact_id,
        "to": to_n,
        "cc": cc_n,
        "bcc": bcc_n,
        "subject": subject.strip(),
        "htmlBody": html_body,
        "textBody": text_body,
        "status": status,
        "source": source,  # manual | ai | automation
        "provider": None,
        "providerMessageId": None,
        "deliveryStatus": None,  # delivered | bounced | complained (from webhooks)
        "approvalStatus": "pending" if status == "pending_approval" else ("not_required" if not org_email.get("approvalRequired") else "none"),
        "approvedBy": None,
        "approvedAt": None,
        "rejectedBy": None,
        "rejectedAt": None,
        "rejectionReason": None,
        "scheduledFor": None,
        "sentAt": None,
        "failedAt": None,
        "failureReason": None,
        "sendAttempts": 0,
        "originalAiSuggestion": original_ai,
        "versions": versions,
        # Inbox reply threading (optional; standalone outbound emails leave these null)
        "inboxThreadId": inbox_thread_id,
        "mailboxId": mailbox_id,
        "providerThreadId": provider_thread_id,
        "providerConversationId": provider_thread_id,
        "inReplyTo": in_reply_to,
        "references": references,
        "replyProvider": reply_provider,
        "internetMessageId": internet_message_id,
        # Transport (resolved at send time; may be pre-set for inbox replies)
        "transportProvider": (
            "gmail" if reply_provider == "google"
            else ("microsoft" if reply_provider == "microsoft" else None)
        ),
        "integrationId": None,
        "sentVia": None,
        "providerRawStatus": None,
        "transportMetadata": None,
        "lastSendAttemptId": None,
        "lastSendAttemptAt": None,
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }
    await db.outbound_emails.insert_one(dict(doc))
    await write_audit(
        org_id, "email_draft_created",
        actor_id=user.get("id"), actor_email=user.get("email"),
        meta={"emailId": doc["id"], "source": source, "status": status, "toCount": len(to_n)},
    )
    return doc


async def _get_owned(email_id: str, org_id: str) -> dict:
    doc = await db.outbound_emails.find_one({"id": email_id, "organizationId": org_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Email not found")
    return doc


def _can_manage(user: dict, doc: dict) -> bool:
    role = normalize_role(user.get("role"))
    if role_at_least(role, "admin"):
        return True
    return doc.get("createdBy") == user["id"]


async def _count_sent_today(org_id: str) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    return await db.outbound_emails.count_documents({
        "organizationId": org_id,
        "status": "sent",
        "sentAt": {"$gte": start},
    })


async def perform_send(doc: dict, user: dict, *, force_retry: bool = False) -> dict:
    """Atomically transition to sending and deliver via routed transport."""
    org_id = doc["organizationId"]
    settings = get_settings()

    # Resolve transport early (threaded replies must not silently use Resend)
    try:
        plan = await resolve_transport(org_id, doc)
    except TransportError as e:
        raise HTTPException(
            status_code=e.http_status,
            detail={"code": e.code, "message": e.message, "actionable": e.actionable},
        ) from e

    if plan.is_threaded_reply:
        # Native path: global EMAIL_SENDING_ENABLED still required; Resend config not required
        import os
        raw = os.environ.get("EMAIL_SENDING_ENABLED")
        if raw is not None and str(raw).strip() != "":
            enabled = str(raw).strip().lower() in {"1", "true", "yes", "on"}
        else:
            enabled = bool(settings.email_sending_enabled)
        if not enabled:
            raise HTTPException(status_code=403, detail="Email sending is disabled (EMAIL_SENDING_ENABLED=false)")
        if plan.reconnect_required or not plan.connected:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "disconnected_integration",
                    "message": plan.warning or ACTIONABLE.get("disconnected_integration"),
                    "actionable": plan.warning or ACTIONABLE.get("disconnected_integration"),
                    "transport": transport_public(plan),
                },
            )
    else:
        allowed, reason = outbound_sending_allowed(settings)
        if not allowed:
            raise HTTPException(status_code=403, detail=reason)

    org_email = await get_org_email_settings(org_id)
    if not org_email.get("sendingEnabled"):
        raise HTTPException(status_code=403, detail="Organization email sending is disabled")

    if org_email.get("approvalRequired"):
        if doc.get("status") not in ("approved", "failed", "needs_review", "delivery_unknown") and not (
            force_retry and doc.get("status") in ("failed", "needs_review", "delivery_unknown")
            and doc.get("approvalStatus") == "approved"
        ):
            if doc.get("approvalStatus") != "approved" and doc.get("status") != "approved":
                raise HTTPException(status_code=403, detail="Draft must be approved before sending")

    if doc.get("status") in ("sent", "cancelled", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot send email in status '{doc.get('status')}'")

    # Never retry a confirmed successful send
    if doc.get("providerMessageId") and doc.get("status") == "sent":
        raise HTTPException(status_code=400, detail="Email already sent")

    to_n = normalize_emails(doc.get("to"))
    cc_n = normalize_emails(doc.get("cc"))
    bcc_n = normalize_emails(doc.get("bcc"))
    if not to_n:
        raise HTTPException(status_code=400, detail="No valid recipients")
    if len(to_n) + len(cc_n) + len(bcc_n) > MAX_RECIPIENTS:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_RECIPIENTS} recipients allowed")

    limit = min(int(org_email.get("dailySendingLimit") or settings.email_daily_limit), settings.email_daily_limit)
    sent_today = await _count_sent_today(org_id)
    if sent_today >= limit:
        raise HTTPException(status_code=429, detail=f"Daily sending limit reached ({limit})")

    attempt_id = str(uuid.uuid4())
    # Atomic claim — prevents double-send
    allowed_from = ["approved", "scheduled", "draft", "pending_approval", "failed", "needs_review", "delivery_unknown"]
    if org_email.get("approvalRequired"):
        allowed_from = ["approved", "scheduled", "failed", "needs_review", "delivery_unknown"]
    claimed = await db.outbound_emails.find_one_and_update(
        {"id": doc["id"], "organizationId": org_id, "status": {"$in": allowed_from}},
        {"$set": {
            "status": "sending",
            "updatedAt": now_iso(),
            "lastSendAttemptId": attempt_id,
            "lastSendAttemptAt": now_iso(),
            "transportProvider": plan.transport_provider,
            "mailboxId": plan.mailbox_id or doc.get("mailboxId"),
            "integrationId": plan.integration_id,
        }, "$inc": {"sendAttempts": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if claimed:
        claimed.pop("_id", None)
    if not claimed:
        current = await _get_owned(doc["id"], org_id)
        if current.get("status") == "sent":
            raise HTTPException(status_code=400, detail="Email already sent")
        if current.get("status") == "sending":
            raise HTTPException(status_code=409, detail="Send already in progress")
        raise HTTPException(status_code=409, detail=f"Cannot send from status '{current.get('status')}'")

    await write_audit(
        org_id, "email_send_attempted",
        actor_id=user.get("id"), actor_email=user.get("email"),
        meta={
            "emailId": doc["id"],
            "attempt": (claimed.get("sendAttempts") or 1),
            "attemptId": attempt_id,
            "transportProvider": plan.transport_provider,
            "native": plan.is_threaded_reply,
        },
    )
    if plan.is_threaded_reply:
        await write_audit(
            org_id, "native_send_attempted",
            actor_id=user.get("id"), actor_email=user.get("email"),
            meta={"emailId": doc["id"], "transport": plan.transport_provider, "mailboxId": plan.mailbox_id},
        )

    # Append signature if configured
    html_body = claimed.get("htmlBody") or ""
    text_body = claimed.get("textBody") or ""
    sig = (org_email.get("companySignature") or "").strip()
    if sig and sig not in (text_body or "") and sig not in (html_body or ""):
        html_body = html_body + "<br/><br/>" + _text_to_html(sig)
        text_body = (text_body or "") + "\n\n" + sig

    from_name = (org_email.get("senderName") or settings.from_name or "").strip()
    from_email = (org_email.get("senderEmail") or settings.from_email or "").strip()
    reply_to = (org_email.get("replyToEmail") or settings.reply_to_email or "").strip() or None

    try:
        if plan.transport_provider in ("gmail", "microsoft"):
            native = await execute_native_send(
                org_id, claimed, plan,
                to=to_n, cc=cc_n, bcc=bcc_n,
                subject=claimed["subject"],
                html_body=html_body, text_body=text_body,
                from_name=from_name,
            )
            ambiguous = (native.get("providerRawStatus") == "accepted_unconfirmed") or not native.get("deliveryConfirmed", True)
            versions = list(claimed.get("versions") or [])
            versions.append(_version_entry(user, "sent", claimed["subject"], html_body, text_body))
            status = "delivery_unknown" if ambiguous else "sent"
            update = {
                "status": status,
                "provider": native.get("provider"),
                "sentVia": native.get("provider"),
                "transportProvider": plan.transport_provider,
                "providerMessageId": native.get("providerMessageId"),
                "providerThreadId": native.get("providerThreadId") or plan.provider_thread_id,
                "providerConversationId": native.get("providerConversationId") or plan.provider_conversation_id,
                "internetMessageId": native.get("internetMessageId"),
                "providerRawStatus": native.get("providerRawStatus"),
                "transportMetadata": {
                    "mailboxEmail": plan.mailbox_email,
                    "label": plan.label,
                    "deliveryConfirmed": native.get("deliveryConfirmed", True),
                },
                "sentAt": now_iso(),
                "failedAt": None,
                "failureReason": None if not ambiguous else ACTIONABLE.get(AMBIGUOUS_DELIVERY),
                "updatedAt": now_iso(),
                "versions": versions,
                "htmlBody": html_body,
                "textBody": text_body,
                "mailboxId": plan.mailbox_id,
                "integrationId": plan.integration_id,
            }
            # Guard: only finalize if still sending (idempotent)
            res = await db.outbound_emails.update_one(
                {"id": doc["id"], "organizationId": org_id, "status": "sending", "lastSendAttemptId": attempt_id},
                {"$set": update},
            )
            if res.matched_count == 0:
                # Already finalized by another worker — return current
                return public_email(await _get_owned(doc["id"], org_id), include_preview=settings.is_development)

            audit_event = (
                "gmail_send_succeeded" if plan.transport_provider == "gmail" and status == "sent"
                else "microsoft_send_succeeded" if plan.transport_provider == "microsoft" and status == "sent"
                else "delivery_ambiguous"
            )
            await write_audit(
                org_id, audit_event,
                actor_id=user.get("id"), actor_email=user.get("email"),
                meta={
                    "emailId": doc["id"],
                    "provider": native.get("provider"),
                    "providerMessageId": native.get("providerMessageId"),
                    "status": status,
                },
            )
        else:
            # Standalone console / Resend
            provider = get_email_provider(settings)
            result = await provider.send(EmailMessage(
                to=to_n, cc=cc_n or None, bcc=bcc_n or None,
                subject=claimed["subject"], html=html_body, text=text_body or None,
                from_email=from_email, from_name=from_name, reply_to=reply_to,
                tags=[{"name": "outbound_id", "value": doc["id"][:50]}],
            ))
            if result.ok:
                versions = list(claimed.get("versions") or [])
                versions.append(_version_entry(user, "sent", claimed["subject"], html_body, text_body))
                update = {
                    "status": "sent",
                    "provider": result.provider,
                    "sentVia": result.provider,
                    "transportProvider": plan.transport_provider,
                    "providerMessageId": result.provider_message_id,
                    "sentAt": now_iso(),
                    "failedAt": None,
                    "failureReason": None,
                    "updatedAt": now_iso(),
                    "versions": versions,
                    "htmlBody": html_body,
                    "textBody": text_body,
                }
                if result.preview and settings.is_development:
                    update["consolePreview"] = result.preview
                await db.outbound_emails.update_one(
                    {"id": doc["id"], "organizationId": org_id, "status": "sending", "lastSendAttemptId": attempt_id},
                    {"$set": update},
                )
                await write_audit(
                    org_id, "email_sent",
                    actor_id=user.get("id"), actor_email=user.get("email"),
                    meta={"emailId": doc["id"], "provider": result.provider, "providerMessageId": result.provider_message_id},
                )
            else:
                update = {
                    "status": "failed",
                    "provider": result.provider,
                    "sentVia": result.provider,
                    "transportProvider": plan.transport_provider,
                    "failedAt": now_iso(),
                    "failureReason": (result.error or "Send failed")[:500],
                    "updatedAt": now_iso(),
                }
                await db.outbound_emails.update_one(
                    {"id": doc["id"], "organizationId": org_id, "status": "sending"},
                    {"$set": update},
                )
                await write_audit(
                    org_id, "email_failed",
                    actor_id=user.get("id"), actor_email=user.get("email"),
                    meta={"emailId": doc["id"], "error": update["failureReason"]},
                )
    except TransportError as e:
        fail_status = "delivery_unknown" if e.code == AMBIGUOUS_DELIVERY else "failed"
        if e.code == AMBIGUOUS_DELIVERY:
            fail_status = "needs_review"
        update = {
            "status": fail_status,
            "provider": plan.transport_provider,
            "sentVia": plan.transport_provider,
            "transportProvider": plan.transport_provider,
            "failedAt": now_iso(),
            "failureReason": e.message[:500],
            "failureCode": e.code,
            "failureActionable": e.actionable,
            "updatedAt": now_iso(),
        }
        await db.outbound_emails.update_one(
            {"id": doc["id"], "organizationId": org_id, "status": "sending"},
            {"$set": update},
        )
        event = (
            "gmail_send_failed" if plan.transport_provider == "gmail"
            else "microsoft_send_failed" if plan.transport_provider == "microsoft"
            else "email_failed"
        )
        if e.code == AMBIGUOUS_DELIVERY:
            event = "delivery_ambiguous"
        if e.code in ("expired_authorization", "disconnected_integration"):
            event = "provider_reconnection_required"
        await write_audit(
            org_id, event,
            actor_id=user.get("id"), actor_email=user.get("email"),
            meta={"emailId": doc["id"], "code": e.code, "error": e.message[:200]},
        )
        raise HTTPException(
            status_code=e.http_status,
            detail={"code": e.code, "message": e.message, "actionable": e.actionable},
        ) from e

    out = public_email(await _get_owned(doc["id"], org_id), include_preview=settings.is_development)
    try:
        out["transport"] = transport_public(plan)
    except Exception:
        pass
    return out



# ---------------- routes ----------------
class EmailCreate(BaseModel):
    to: List[str] = Field(default_factory=list)
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    subject: str = ""
    htmlBody: Optional[str] = None
    textBody: Optional[str] = None
    clientId: Optional[str] = None
    leadId: Optional[str] = None
    contactId: Optional[str] = None
    source: Optional[str] = "manual"
    generateAi: bool = False
    aiInstruction: Optional[str] = None


class EmailUpdate(BaseModel):
    to: Optional[List[str]] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    subject: Optional[str] = None
    htmlBody: Optional[str] = None
    textBody: Optional[str] = None
    clientId: Optional[str] = None
    leadId: Optional[str] = None
    contactId: Optional[str] = None


class RejectBody(BaseModel):
    reason: Optional[str] = None


class ImproveBody(BaseModel):
    instruction: Optional[str] = None
    command: Optional[str] = "improve"  # improve | rewrite | shorten | email


@router.get("")
async def list_emails(
    status: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    org: str = Depends(current_org),
    user: dict = Depends(current_user),
):
    query: dict = {"organizationId": org}
    role = normalize_role(user.get("role"))
    if not role_at_least(role, "admin"):
        query["createdBy"] = user["id"]
    if status:
        # bucket aliases
        buckets = {
            "drafts": ["draft"],
            "awaiting_approval": ["pending_approval"],
            "scheduled": ["scheduled"],
            "sent": ["sent"],
            "failed": ["failed", "needs_review", "delivery_unknown"],
        }
        query["status"] = {"$in": buckets[status]} if status in buckets else status
    if q:
        query["$or"] = [
            {"subject": {"$regex": q, "$options": "i"}},
            {"to": {"$regex": q, "$options": "i"}},
        ]
    items = await db.outbound_emails.find(query, {"_id": 0, "versions": 0, "htmlBody": 0}).sort("updatedAt", -1).to_list(limit)
    counts = {}
    base = {"organizationId": org}
    if not role_at_least(role, "admin"):
        base["createdBy"] = user["id"]
    for key, statuses in [
        ("drafts", ["draft"]),
        ("awaiting_approval", ["pending_approval"]),
        ("scheduled", ["scheduled"]),
        ("sent", ["sent"]),
        ("failed", ["failed", "needs_review", "delivery_unknown"]),
        ("cancelled", ["cancelled"]),
    ]:
        counts[key] = await db.outbound_emails.count_documents({**base, "status": {"$in": statuses}})
    return {"items": [public_email(i) for i in items], "counts": counts}


@router.get("/status")
async def sending_status(org: str = Depends(current_org)):
    """Non-sensitive sending status for any org member."""
    settings = get_settings()
    org_email = await get_org_email_settings(org)
    allowed, reason = outbound_sending_allowed(settings)
    sent_today = await _count_sent_today(org)
    limit = min(int(org_email.get("dailySendingLimit") or settings.email_daily_limit), settings.email_daily_limit)
    return {
        "globalSendingEnabled": settings.email_sending_enabled,
        "organizationSendingEnabled": bool(org_email.get("sendingEnabled")),
        "approvalRequired": bool(org_email.get("approvalRequired")),
        "provider": settings.email_provider,
        "providerConfigured": get_email_provider(settings).is_configured(),
        "canSend": allowed and bool(org_email.get("sendingEnabled")),
        "blockedReason": None if (allowed and org_email.get("sendingEnabled")) else (reason if not allowed else "Organization email sending is disabled"),
        "sentToday": sent_today,
        "dailyLimit": limit,
        "maxRecipients": MAX_RECIPIENTS,
    }


@router.get("/{email_id}")
async def get_email(email_id: str, org: str = Depends(current_org), user: dict = Depends(current_user)):
    doc = await _get_owned(email_id, org)
    if not _can_manage(user, doc) and not role_at_least(user.get("role"), "admin"):
        raise HTTPException(status_code=403, detail="Not allowed")
    settings = get_settings()
    out = public_email(doc, include_preview=settings.is_development)
    try:
        plan = await resolve_transport(org, doc)
        out["transport"] = transport_public(plan)
    except TransportError as e:
        out["transport"] = {
            "transportProvider": doc.get("transportProvider") or doc.get("replyProvider"),
            "reconnectRequired": True,
            "connected": False,
            "warning": e.message,
            "actionable": e.actionable,
            "isThreadedReply": bool(doc.get("inboxThreadId") or doc.get("mailboxId")),
            "label": "Reconnect required",
        }
    return out



@router.post("")
async def create_email(payload: EmailCreate, org: str = Depends(current_org), user: dict = Depends(current_user)):
    subject = (payload.subject or "").strip()
    text_body = payload.textBody or ""
    html_body = payload.htmlBody or ""
    original_ai = None
    source = payload.source or "manual"

    if payload.generateAi:
        source = "ai"
        instruction = payload.aiInstruction or "Write a professional, warm follow-up email."
        prompt = (
            f"Write an email.\nInstruction: {instruction}\n"
            f"Subject hint: {subject or '(choose an appropriate subject)'}\n"
            "Return JSON with keys subject, body (plain text)."
        )
        try:
            data = await ai_service.complete_json(
                "You write concise professional business emails. Return only JSON.",
                prompt,
                ["subject", "body"],
            )
            subject = (data.get("subject") or subject or "Follow-up").strip()
            text_body = data.get("body") or text_body
            html_body = _text_to_html(text_body)
            original_ai = {"subject": subject, "textBody": text_body, "htmlBody": html_body}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"AI draft generation failed: {e}")

    if not subject:
        subject = "Untitled draft"
    doc = await create_outbound_email(
        org_id=org, user=user, to=payload.to or [], cc=payload.cc, bcc=payload.bcc,
        subject=subject, html_body=html_body, text_body=text_body,
        client_id=payload.clientId, lead_id=payload.leadId, contact_id=payload.contactId,
        source=source, original_ai=original_ai, status="draft",
    )
    return public_email(doc)


@router.patch("/{email_id}")
async def update_email(email_id: str, payload: EmailUpdate, org: str = Depends(current_org), user: dict = Depends(current_user)):
    doc = await _get_owned(email_id, org)
    if not _can_manage(user, doc):
        raise HTTPException(status_code=403, detail="Not allowed")
    if doc.get("status") not in EDITABLE:
        raise HTTPException(status_code=400, detail=f"Cannot edit email in status '{doc.get('status')}'")

    updates = {}
    if payload.to is not None:
        updates["to"] = normalize_emails(payload.to)
    if payload.cc is not None:
        updates["cc"] = normalize_emails(payload.cc)
    if payload.bcc is not None:
        updates["bcc"] = normalize_emails(payload.bcc)
    if payload.subject is not None:
        updates["subject"] = payload.subject.strip()
    if payload.htmlBody is not None:
        updates["htmlBody"] = payload.htmlBody
        if payload.textBody is None:
            updates["textBody"] = _html_to_text(payload.htmlBody)
    if payload.textBody is not None:
        updates["textBody"] = payload.textBody
        if payload.htmlBody is None:
            updates["htmlBody"] = _text_to_html(payload.textBody)
    for k, field in [("clientId", "clientId"), ("leadId", "leadId"), ("contactId", "contactId")]:
        val = getattr(payload, k)
        if val is not None:
            updates[field] = val

    total = len(updates.get("to", doc.get("to") or [])) + len(updates.get("cc", doc.get("cc") or [])) + len(updates.get("bcc", doc.get("bcc") or []))
    if total > MAX_RECIPIENTS:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_RECIPIENTS} recipients allowed")
    if "to" in updates and not updates["to"]:
        raise HTTPException(status_code=400, detail="At least one recipient (to) is required")

    subject = updates.get("subject", doc["subject"])
    html_body = updates.get("htmlBody", doc.get("htmlBody") or "")
    text_body = updates.get("textBody", doc.get("textBody") or "")
    versions = list(doc.get("versions") or [])
    versions.append(_version_entry(user, "user_edit", subject, html_body, text_body))
    updates["versions"] = versions
    updates["updatedAt"] = now_iso()
    # Re-edit after reject → back to draft
    if doc.get("status") == "rejected":
        updates["status"] = "draft"
        updates["approvalStatus"] = "none"

    await db.outbound_emails.update_one({"id": email_id, "organizationId": org}, {"$set": updates})
    await write_audit(org, "email_draft_edited", actor_id=user.get("id"), actor_email=user.get("email"), meta={"emailId": email_id})
    return public_email(await _get_owned(email_id, org))


@router.post("/{email_id}/submit")
async def submit_for_approval(email_id: str, org: str = Depends(current_org), user: dict = Depends(current_user)):
    doc = await _get_owned(email_id, org)
    if not _can_manage(user, doc):
        raise HTTPException(status_code=403, detail="Not allowed")
    if doc.get("status") not in ("draft", "rejected", "failed"):
        raise HTTPException(status_code=400, detail="Only drafts can be submitted for approval")
    org_email = await get_org_email_settings(org)
    if not org_email.get("approvalRequired"):
        # No approval needed — mark approved for send readiness
        await db.outbound_emails.update_one(
            {"id": email_id, "organizationId": org},
            {"$set": {"status": "approved", "approvalStatus": "not_required", "updatedAt": now_iso()}},
        )
    else:
        await db.outbound_emails.update_one(
            {"id": email_id, "organizationId": org},
            {"$set": {
                "status": "pending_approval", "approvalStatus": "pending",
                "updatedAt": now_iso(),
            }},
        )
    await write_audit(org, "email_submitted_for_approval", actor_id=user.get("id"), actor_email=user.get("email"), meta={"emailId": email_id})
    return public_email(await _get_owned(email_id, org))


@router.post("/{email_id}/approve")
async def approve_email(email_id: str, org: str = Depends(current_org), user: dict = Depends(require_admin)):
    doc = await _get_owned(email_id, org)
    if doc.get("status") not in ("pending_approval", "draft", "rejected"):
        raise HTTPException(status_code=400, detail="Email is not awaiting approval")
    org_email = await get_org_email_settings(org)
    # Self-approval blocked for non-owners when approval is required
    if org_email.get("approvalRequired") and doc.get("createdBy") == user["id"]:
        if normalize_role(user.get("role")) != "owner":
            raise HTTPException(status_code=403, detail="You cannot approve your own drafts when approval is required")
    await db.outbound_emails.update_one(
        {"id": email_id, "organizationId": org},
        {"$set": {
            "status": "approved", "approvalStatus": "approved",
            "approvedBy": user["id"], "approvedAt": now_iso(),
            "rejectedBy": None, "rejectedAt": None, "rejectionReason": None,
            "updatedAt": now_iso(),
        }},
    )
    await write_audit(org, "email_approved", actor_id=user.get("id"), actor_email=user.get("email"), meta={"emailId": email_id})
    return public_email(await _get_owned(email_id, org))


@router.post("/{email_id}/reject")
async def reject_email(email_id: str, payload: RejectBody, org: str = Depends(current_org), user: dict = Depends(require_admin)):
    doc = await _get_owned(email_id, org)
    if doc.get("status") not in ("pending_approval", "approved", "draft"):
        raise HTTPException(status_code=400, detail="Email cannot be rejected in its current status")
    await db.outbound_emails.update_one(
        {"id": email_id, "organizationId": org},
        {"$set": {
            "status": "rejected", "approvalStatus": "rejected",
            "rejectedBy": user["id"], "rejectedAt": now_iso(),
            "rejectionReason": (payload.reason or "")[:500],
            "updatedAt": now_iso(),
        }},
    )
    await write_audit(org, "email_rejected", actor_id=user.get("id"), actor_email=user.get("email"), meta={"emailId": email_id})
    return public_email(await _get_owned(email_id, org))


@router.post("/{email_id}/send")
async def send_email(email_id: str, org: str = Depends(current_org), user: dict = Depends(current_user)):
    doc = await _get_owned(email_id, org)
    if doc.get("status") == "sent":
        raise HTTPException(status_code=400, detail="Email already sent")
    if doc.get("status") == "sending":
        raise HTTPException(status_code=409, detail="Send already in progress")
    role = normalize_role(user.get("role"))
    org_email = await get_org_email_settings(org)
    if org_email.get("approvalRequired"):
        if not role_at_least(role, "admin"):
            raise HTTPException(status_code=403, detail="Only owners and admins can send when approval is required")
        if doc.get("status") not in ("approved", "failed", "scheduled", "needs_review", "delivery_unknown"):
            raise HTTPException(status_code=403, detail="Draft must be approved before sending")
    else:
        if not _can_manage(user, doc):
            raise HTTPException(status_code=403, detail="Not allowed")
        # Auto-promote editable drafts to approved when approval is not required
        if doc.get("status") in ("draft", "pending_approval", "rejected"):
            await db.outbound_emails.update_one(
                {"id": email_id, "organizationId": org},
                {"$set": {"status": "approved", "approvalStatus": "not_required", "updatedAt": now_iso()}},
            )
            doc = await _get_owned(email_id, org)
    return await perform_send(doc, user)


@router.post("/{email_id}/cancel")
async def cancel_email(email_id: str, org: str = Depends(current_org), user: dict = Depends(current_user)):
    doc = await _get_owned(email_id, org)
    if not _can_manage(user, doc):
        raise HTTPException(status_code=403, detail="Not allowed")
    if doc.get("status") in ("sent", "sending", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel email in status '{doc.get('status')}'")
    await db.outbound_emails.update_one(
        {"id": email_id, "organizationId": org},
        {"$set": {"status": "cancelled", "updatedAt": now_iso()}},
    )
    await write_audit(org, "email_cancelled", actor_id=user.get("id"), actor_email=user.get("email"), meta={"emailId": email_id})
    return public_email(await _get_owned(email_id, org))


@router.post("/{email_id}/retry")
async def retry_email(email_id: str, org: str = Depends(current_org), user: dict = Depends(current_user)):
    doc = await _get_owned(email_id, org)
    if doc.get("status") not in ("failed", "needs_review", "delivery_unknown"):
        raise HTTPException(status_code=400, detail="Only failed or unconfirmed emails can be retried")
    if doc.get("status") in ("needs_review", "delivery_unknown") and doc.get("providerMessageId"):
        raise HTTPException(
            status_code=400,
            detail="Delivery may have succeeded — confirm in the provider mailbox before retrying",
        )
    role = normalize_role(user.get("role"))
    if not role_at_least(role, "admin") and doc.get("createdBy") != user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    await write_audit(org, "email_retried", actor_id=user.get("id"), actor_email=user.get("email"), meta={"emailId": email_id})
    # Move back to approved so perform_send can claim
    next_status = "approved" if doc.get("approvalStatus") in ("approved", "not_required") else "draft"
    await db.outbound_emails.update_one(
        {"id": email_id, "organizationId": org, "status": {"$in": ["failed", "needs_review", "delivery_unknown"]}},
        {"$set": {"status": next_status, "updatedAt": now_iso(), "failureReason": None, "failureCode": None}},
    )
    doc = await _get_owned(email_id, org)
    return await perform_send(doc, user, force_retry=True)


@router.post("/{email_id}/improve")
async def improve_email(email_id: str, payload: ImproveBody, org: str = Depends(current_org), user: dict = Depends(current_user)):
    doc = await _get_owned(email_id, org)
    if not _can_manage(user, doc):
        raise HTTPException(status_code=403, detail="Not allowed")
    if doc.get("status") not in EDITABLE:
        raise HTTPException(status_code=400, detail="Cannot improve a non-editable email")
    command = (payload.command or "improve").lower()
    instruction = payload.instruction or {
        "improve": "Make this clearer and more persuasive while staying professional.",
        "rewrite": "Rewrite in a polished professional tone.",
        "shorten": "Shorten while keeping the key ask.",
        "email": "Polish this into a warm professional follow-up email.",
    }.get(command, "Improve this email.")
    body = doc.get("textBody") or _html_to_text(doc.get("htmlBody") or "")
    prompt = (
        f"Command: {command}\nInstruction: {instruction}\n"
        f"Current subject: {doc.get('subject')}\nCurrent body:\n{body}\n"
        "Return JSON with keys subject, body."
    )
    try:
        data = await ai_service.complete_json(
            "You improve business emails. Preserve intent. Return only JSON.",
            prompt,
            ["subject", "body"],
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI improve failed: {e}")

    subject = (data.get("subject") or doc["subject"]).strip()
    text_body = data.get("body") or body
    html_body = _text_to_html(text_body)
    original = doc.get("originalAiSuggestion")
    if not original:
        original = {"subject": doc["subject"], "textBody": body, "htmlBody": doc.get("htmlBody") or ""}
    versions = list(doc.get("versions") or [])
    versions.append(_version_entry(user, "ai_suggestion", subject, html_body, text_body))
    await db.outbound_emails.update_one(
        {"id": email_id, "organizationId": org},
        {"$set": {
            "subject": subject, "textBody": text_body, "htmlBody": html_body,
            "originalAiSuggestion": original,
            "versions": versions, "updatedAt": now_iso(), "source": doc.get("source") if doc.get("source") != "manual" else "ai",
        }},
    )
    await write_audit(org, "email_draft_edited", actor_id=user.get("id"), actor_email=user.get("email"), meta={"emailId": email_id, "via": "ai_improve"})
    return public_email(await _get_owned(email_id, org))
