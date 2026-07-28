"""Microsoft Outlook inbox sync via Graph delta queries."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from inbox.sanitize import html_to_text, normalize_email, parse_address_list, sanitize_html

logger = logging.getLogger(__name__)

GRAPH = "https://graph.microsoft.com/v1.0"


async def _get(client: httpx.AsyncClient, url: str, token: str, params: dict = None) -> dict:
    r = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 401:
        raise PermissionError("Microsoft token expired")
    if r.status_code == 429:
        raise RuntimeError("Microsoft Graph rate limit exceeded — retry later")
    r.raise_for_status()
    return r.json()


def _addr_list(field) -> List[str]:
    if not field:
        return []
    recipients = field if isinstance(field, list) else []
    out = []
    for r in recipients:
        addr = ((r or {}).get("emailAddress") or {}).get("address")
        if addr:
            out.append(normalize_email(addr))
    return out


def parse_outlook_message(msg: dict) -> dict:
    body = msg.get("body") or {}
    content = body.get("content") or ""
    content_type = (body.get("contentType") or "").lower()
    html = content if content_type == "html" else ""
    text = content if content_type != "html" else html_to_text(content)
    if not text and html:
        text = html_to_text(html)
    sanitized = sanitize_html(html) if html else ""
    frm = ((msg.get("from") or {}).get("emailAddress") or {})
    conversation_id = msg.get("conversationId") or msg.get("id")
    attachments = []
    if msg.get("hasAttachments"):
        # Metadata filled on demand / if expanded
        for att in msg.get("attachments") or []:
            if att.get("@odata.type", "").endswith("fileAttachment") or att.get("name"):
                attachments.append({
                    "filename": (att.get("name") or "attachment")[:255],
                    "mimeType": att.get("contentType") or "application/octet-stream",
                    "size": int(att.get("size") or 0),
                    "providerAttachmentId": att.get("id"),
                    "providerMessageId": msg.get("id"),
                })
    return {
        "providerMessageId": msg["id"],
        "providerThreadId": conversation_id,
        "internetMessageId": msg.get("internetMessageId"),
        "inReplyTo": None,
        "references": None,
        "from": normalize_email(frm.get("address") or ""),
        "fromRaw": frm.get("address") or "",
        "to": _addr_list(msg.get("toRecipients")),
        "cc": _addr_list(msg.get("ccRecipients")),
        "bcc": _addr_list(msg.get("bccRecipients")),
        "subject": msg.get("subject") or "(no subject)",
        "textBody": (text or "")[:500000],
        "sanitizedHtmlBody": sanitized[:500000],
        "snippet": (msg.get("bodyPreview") or (text or "")[:240])[:500],
        "receivedAt": msg.get("receivedDateTime"),
        "sentAt": msg.get("sentDateTime") or msg.get("receivedDateTime"),
        "isRead": bool(msg.get("isRead")),
        "direction": "inbound",
        "attachments": attachments,
        "providerLabels": ["Inbox"],
    }


async def discover_account(token: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        me = await _get(client, f"{GRAPH}/me", token)
        return {
            "providerAccountId": me.get("id") or "",
            "emailAddress": normalize_email(me.get("mail") or me.get("userPrincipalName") or ""),
            "displayName": me.get("displayName") or "",
        }


async def list_inbox_page(
    token: str,
    *,
    top: int = 25,
    skip_token_url: str = None,
) -> Tuple[List[dict], Optional[str]]:
    """Initial sync page from Inbox (excludes Junk/Deleted)."""
    select = (
        "id,conversationId,subject,bodyPreview,body,from,toRecipients,ccRecipients,"
        "bccRecipients,receivedDateTime,sentDateTime,isRead,hasAttachments,internetMessageId"
    )
    async with httpx.AsyncClient(timeout=60) as client:
        if skip_token_url:
            data = await _get(client, skip_token_url, token)
        else:
            data = await _get(
                client,
                f"{GRAPH}/me/mailFolders/Inbox/messages",
                token,
                {"$top": min(top, 50), "$select": select, "$orderby": "receivedDateTime desc"},
            )
        messages = [parse_outlook_message(m) for m in (data.get("value") or [])]
        next_link = data.get("@odata.nextLink")
        return messages, next_link


async def delta_inbox(
    token: str,
    *,
    delta_link: str = None,
    top: int = 25,
) -> Tuple[List[dict], Optional[str], bool]:
    """Return (messages, new_delta_link, cursor_invalid)."""
    select = (
        "id,conversationId,subject,bodyPreview,body,from,toRecipients,ccRecipients,"
        "receivedDateTime,sentDateTime,isRead,hasAttachments,internetMessageId"
    )
    async with httpx.AsyncClient(timeout=60) as client:
        if delta_link:
            r = await client.get(delta_link, headers={"Authorization": f"Bearer {token}"})
        else:
            r = await client.get(
                f"{GRAPH}/me/mailFolders/Inbox/messages/delta",
                params={"$top": min(top, 50), "$select": select},
                headers={"Authorization": f"Bearer {token}"},
            )
        if r.status_code in (410, 404):
            return [], None, True
        if r.status_code == 401:
            raise PermissionError("Microsoft token expired")
        if r.status_code == 429:
            raise RuntimeError("Microsoft Graph rate limit exceeded — retry later")
        r.raise_for_status()
        data = r.json()
        messages = []
        for m in data.get("value") or []:
            if m.get("@removed"):
                continue
            messages.append(parse_outlook_message(m))
        new_link = data.get("@odata.deltaLink") or data.get("@odata.nextLink")
        return messages, new_link, False


async def download_attachment(token: str, message_id: str, attachment_id: str) -> Tuple[bytes, str, str]:
    async with httpx.AsyncClient(timeout=60) as client:
        data = await _get(
            client,
            f"{GRAPH}/me/messages/{message_id}/attachments/{attachment_id}",
            token,
        )
        import base64
        content = data.get("contentBytes") or ""
        raw = base64.b64decode(content) if content else b""
        return raw, data.get("contentType") or "application/octet-stream", data.get("name") or "attachment"
