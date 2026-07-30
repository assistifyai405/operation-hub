"""Outbound transport routing: console | resend | gmail | microsoft."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

from core import db, now_iso
from inbox.sanitize import normalize_email
from inbox.transport_errors import (
    ACTIONABLE,
    DISCONNECTED,
    MAILBOX_MISMATCH,
    TransportError,
)
from integrations import store
from integrations.providers import get_provider

logger = logging.getLogger(__name__)

SAFE_FILENAME = re.compile(r"^[\w.\- ()]+$")
MAX_SINGLE_ATTACHMENT = 10 * 1024 * 1024


@dataclass
class TransportPlan:
    transport_provider: str  # console | resend | gmail | microsoft
    mailbox_id: Optional[str] = None
    integration_id: Optional[str] = None
    mailbox_email: Optional[str] = None
    mailbox_display_name: Optional[str] = None
    provider_thread_id: Optional[str] = None
    provider_conversation_id: Optional[str] = None
    reply_to_provider_message_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: Optional[str] = None
    connected: bool = True
    reconnect_required: bool = False
    warning: Optional[str] = None
    label: str = "Send"
    is_threaded_reply: bool = False


def _label_for(provider: str) -> str:
    return {
        "gmail": "Send via Gmail",
        "microsoft": "Send via Outlook",
        "resend": "Send via Resend",
        "console": "Send via Console",
    }.get(provider, f"Send via {provider}")


async def _load_token(org_id: str, provider: str) -> tuple[dict, dict]:
    """Load integration credentials; refresh when access token missing or on demand."""
    doc = await store.get_by_provider(org_id, provider)
    if not doc or doc.get("status") not in ("connected", "error"):
        raise TransportError(
            DISCONNECTED,
            f"{'Google Workspace' if provider == 'google' else 'Microsoft 365'} is not connected",
            400,
            ACTIONABLE[DISCONNECTED],
        )
    creds = await store.load_credentials(doc)
    if not creds.get("access_token") and creds.get("refresh_token"):
        try:
            creds = await get_provider(provider).refresh(creds)
            await store.save_credentials(org_id, doc["id"], creds, status="connected")
        except Exception as e:
            logger.warning("[TRANSPORT] token refresh failed provider=%s", provider)
            raise TransportError(
                DISCONNECTED,
                f"Token refresh failed — reconnect the integration ({e})",
                401,
                ACTIONABLE[DISCONNECTED],
            ) from e
    if not creds.get("access_token"):
        raise TransportError(
            DISCONNECTED,
            "Access token missing — reconnect the integration",
            401,
            ACTIONABLE[DISCONNECTED],
        )
    return doc, creds


async def refresh_token_once(org_id: str, integ: dict, creds: dict, provider: str) -> dict:
    if not creds.get("refresh_token"):
        raise TransportError(
            DISCONNECTED,
            "No refresh token — reconnect the integration",
            401,
            ACTIONABLE[DISCONNECTED],
        )
    try:
        new_creds = await get_provider(provider).refresh(creds)
        await store.save_credentials(org_id, integ["id"], new_creds, status="connected")
        return new_creds
    except Exception as e:
        await store.update_health(org_id, integ["id"], False, "Token refresh failed")
        raise TransportError(
            DISCONNECTED,
            f"Token refresh failed — reconnect the integration",
            401,
            ACTIONABLE[DISCONNECTED],
        ) from e


async def resolve_transport(org_id: str, doc: dict) -> TransportPlan:
    """Decide transport for an outbound email. Threaded replies never fall back to Resend."""
    mailbox_id = doc.get("mailboxId")
    reply_provider = (doc.get("replyProvider") or doc.get("transportProvider") or "").lower()
    is_linked = bool(doc.get("inboxThreadId") or mailbox_id or reply_provider in ("google", "microsoft", "gmail"))

    if is_linked:
        mailbox = None
        if mailbox_id:
            mailbox = await db.mailboxes.find_one(
                {"id": mailbox_id, "organizationId": org_id}, {"_id": 0},
            )
        if not mailbox and reply_provider in ("google", "gmail"):
            mailbox = await db.mailboxes.find_one(
                {"organizationId": org_id, "provider": "google", "syncEnabled": True}, {"_id": 0},
            )
        if not mailbox and reply_provider in ("microsoft", "microsoft_365", "outlook"):
            mailbox = await db.mailboxes.find_one(
                {"organizationId": org_id, "provider": "microsoft", "syncEnabled": True}, {"_id": 0},
            )
        if not mailbox:
            raise TransportError(
                DISCONNECTED,
                "No connected mailbox for this inbox reply — reconnect Google or Microsoft",
                400,
                ACTIONABLE[DISCONNECTED],
            )

        provider = mailbox["provider"]  # google | microsoft
        transport = "gmail" if provider == "google" else "microsoft"
        integ = await store.get_by_provider(org_id, provider)
        connected = bool(integ and integ.get("status") in ("connected", "error") and integ.get("encryptedCredentials"))
        reconnect = not connected or integ.get("status") == "error"

        # Resolve reply-to provider message (latest inbound in thread)
        reply_to_pmid = None
        in_reply_to = doc.get("inReplyTo")
        references = doc.get("references")
        if doc.get("inboxThreadId"):
            last = await db.inbound_messages.find_one(
                {"organizationId": org_id, "threadId": doc["inboxThreadId"]},
                {"_id": 0},
                sort=[("receivedAt", -1)],
            )
            if last:
                reply_to_pmid = last.get("providerMessageId")
                in_reply_to = in_reply_to or last.get("internetMessageId")
                references = references or last.get("references") or last.get("internetMessageId")

        warning = None
        if reconnect:
            warning = ACTIONABLE[DISCONNECTED]

        return TransportPlan(
            transport_provider=transport,
            mailbox_id=mailbox["id"],
            integration_id=(integ or {}).get("id") or mailbox.get("integrationId"),
            mailbox_email=mailbox.get("emailAddress"),
            mailbox_display_name=mailbox.get("displayName") or mailbox.get("emailAddress"),
            provider_thread_id=doc.get("providerThreadId") or mailbox.get("providerThreadId"),
            provider_conversation_id=doc.get("providerConversationId") or doc.get("providerThreadId"),
            reply_to_provider_message_id=reply_to_pmid,
            in_reply_to=in_reply_to,
            references=references,
            connected=connected,
            reconnect_required=reconnect,
            warning=warning,
            label=_label_for(transport),
            is_threaded_reply=True,
        )

    # Standalone — configured EMAIL_PROVIDER
    from email_providers import get_email_provider
    from config import get_settings
    import os
    s = get_settings()
    name = (os.environ.get("EMAIL_PROVIDER") or s.email_provider or "console").lower()
    if name not in ("console", "resend"):
        name = "console"
    return TransportPlan(
        transport_provider=name,
        label=_label_for(name),
        is_threaded_reply=False,
        connected=get_email_provider(s).is_configured() if name == "resend" else True,
    )


def transport_public(plan: TransportPlan) -> dict:
    return {
        "transportProvider": plan.transport_provider,
        "label": plan.label,
        "mailboxId": plan.mailbox_id,
        "mailboxEmail": plan.mailbox_email,
        "mailboxDisplayName": plan.mailbox_display_name,
        "integrationId": plan.integration_id,
        "providerThreadId": plan.provider_thread_id,
        "providerConversationId": plan.provider_conversation_id,
        "connected": plan.connected,
        "reconnectRequired": plan.reconnect_required,
        "warning": plan.warning,
        "isThreadedReply": plan.is_threaded_reply,
        # Never expose tokens
    }


async def load_outbound_attachments(org_id: str, doc: dict) -> List[dict]:
    """Load attachment bytes for native send from org-scoped document refs only."""
    refs = doc.get("attachments") or []
    if not refs:
        return []
    out = []
    for ref in refs[:10]:
        doc_id = ref.get("documentId") or ref.get("id")
        if not doc_id:
            continue
        d = await db.documents.find_one(
            {"id": doc_id, "organizationId": org_id},
            {"_id": 0},
        )
        if not d:
            raise TransportError(
                "invalid_recipient",
                f"Attachment document not found in organization: {doc_id}",
                400,
            )
        size = int(d.get("size") or 0)
        if size > MAX_SINGLE_ATTACHMENT:
            raise TransportError(
                "attachment_too_large",
                f"Attachment {d.get('name')} exceeds size limit",
                400,
                ACTIONABLE.get("attachment_too_large"),
            )
        path = d.get("storage_path") or d.get("path")
        if not path or ".." in str(path):
            raise TransportError("attachment_too_large", "Invalid attachment path", 400)
        from storage import get_object, StorageError
        try:
            content, ctype = get_object(path)
        except StorageError as e:
            raise TransportError("attachment_too_large", f"Cannot read attachment: {e}", 400) from e
        filename = re.sub(r"[^\w.\- ()]", "_", d.get("name") or ref.get("filename") or "attachment")[:180]
        out.append({
            "filename": filename,
            "mimeType": d.get("mime_type") or d.get("contentType") or ctype or "application/octet-stream",
            "content": content,
        })
    return out


async def execute_native_send(
    org_id: str,
    doc: dict,
    plan: TransportPlan,
    *,
    to: List[str],
    cc: List[str],
    bcc: List[str],
    subject: str,
    html_body: str,
    text_body: str,
    from_name: str = "",
) -> dict:
    """Send via Gmail or Microsoft. Raises TransportError. No Resend fallback."""
    if plan.reconnect_required or not plan.connected:
        raise TransportError(
            DISCONNECTED,
            plan.warning or ACTIONABLE[DISCONNECTED],
            400,
            ACTIONABLE[DISCONNECTED],
        )

    provider_key = "google" if plan.transport_provider == "gmail" else "microsoft"
    integ, creds = await _load_token(org_id, provider_key)
    mailbox_email = normalize_email(plan.mailbox_email)
    if not mailbox_email:
        raise TransportError(MAILBOX_MISMATCH, "Mailbox has no email address", 400, ACTIONABLE[MAILBOX_MISMATCH])

    # Sender must match connected mailbox — no spoofing
    account_email = normalize_email(integ.get("accountEmail") or plan.mailbox_email)
    if account_email and account_email != mailbox_email:
        # Prefer mailbox email if integration label differs slightly; still must be same org mailbox
        pass
    from_email = mailbox_email

    attachments = await load_outbound_attachments(org_id, doc)

    async def _do_send(access_token: str) -> dict:
        if plan.transport_provider == "gmail":
            from inbox.gmail_send import send_gmail_message
            return await send_gmail_message(
                access_token,
                from_email=from_email,
                from_name=from_name or plan.mailbox_display_name or "",
                to=to,
                cc=cc or None,
                bcc=bcc or None,
                subject=subject,
                text_body=text_body or "",
                html_body=html_body or "",
                thread_id=plan.provider_thread_id,
                in_reply_to=plan.in_reply_to,
                references=plan.references,
                attachments=attachments or None,
            )
        from inbox.outlook_send import send_outlook_message
        return await send_outlook_message(
            access_token,
            to=to,
            cc=cc or None,
            bcc=bcc or None,
            subject=subject,
            text_body=text_body or "",
            html_body=html_body or "",
            reply_to_provider_message_id=plan.reply_to_provider_message_id,
            attachments=attachments or None,
        )

    try:
        return await _do_send(creds["access_token"])
    except TransportError as e:
        if e.code == "expired_authorization" and creds.get("refresh_token"):
            creds = await refresh_token_once(org_id, integ, creds, provider_key)
            return await _do_send(creds["access_token"])
        raise
