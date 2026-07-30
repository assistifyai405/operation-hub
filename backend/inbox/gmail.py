"""Gmail inbox sync (history API + fallback list)."""
from __future__ import annotations

import base64
import logging
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

from inbox.sanitize import html_to_text, normalize_email, parse_address_list, sanitize_html

logger = logging.getLogger(__name__)

GMAIL_API = "https://gmail.googleapis.com/gmail/v1"


async def _get(client: httpx.AsyncClient, path: str, token: str, params: dict = None) -> dict:
    r = await client.get(f"{GMAIL_API}{path}", params=params or {}, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 401:
        raise PermissionError("Gmail token expired")
    if r.status_code == 429:
        raise RuntimeError("Gmail rate limit exceeded — retry later")
    r.raise_for_status()
    return r.json()


def _decode_body(payload: dict) -> Tuple[str, str]:
    """Return (text, html) from Gmail message payload."""
    text, html = "", ""

    def walk(part: dict):
        nonlocal text, html
        mime = (part.get("mimeType") or "").lower()
        body = part.get("body") or {}
        data = body.get("data")
        if data:
            raw = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            if mime == "text/plain" and not text:
                text = raw
            elif mime == "text/html" and not html:
                html = raw
        for child in part.get("parts") or []:
            walk(child)

    walk(payload or {})
    return text, html


def _headers_map(payload: dict) -> Dict[str, str]:
    out = {}
    for h in (payload or {}).get("headers") or []:
        name = (h.get("name") or "").lower()
        if name:
            out[name] = h.get("value") or ""
    return out


def _attachments_meta(payload: dict, provider_message_id: str) -> List[dict]:
    items = []

    def walk(part: dict):
        filename = part.get("filename") or ""
        body = part.get("body") or {}
        att_id = body.get("attachmentId")
        if filename and att_id:
            items.append({
                "filename": filename[:255],
                "mimeType": part.get("mimeType") or "application/octet-stream",
                "size": int(body.get("size") or 0),
                "providerAttachmentId": att_id,
                "providerMessageId": provider_message_id,
            })
        for child in part.get("parts") or []:
            walk(child)

    walk(payload or {})
    return items


async def discover_account(token: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        profile = await _get(client, "/users/me/profile", token)
        # Prefer people/userinfo from token; profile has emailAddress
        return {
            "providerAccountId": profile.get("emailAddress") or "",
            "emailAddress": (profile.get("emailAddress") or "").lower(),
            "displayName": profile.get("emailAddress") or "",
            "messagesTotal": profile.get("messagesTotal"),
            "historyId": str(profile.get("historyId") or ""),
        }


def parse_gmail_message(msg: dict) -> dict:
    payload = msg.get("payload") or {}
    headers = _headers_map(payload)
    text, html = _decode_body(payload)
    if not text and html:
        text = html_to_text(html)
    sanitized = sanitize_html(html) if html else ""
    received = None
    if headers.get("date"):
        try:
            received = parsedate_to_datetime(headers["date"]).isoformat()
        except Exception:
            received = None
    if not received and msg.get("internalDate"):
        try:
            ms = int(msg["internalDate"])
            from datetime import datetime, timezone
            received = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
        except Exception:
            received = None

    label_ids = msg.get("labelIds") or []
    return {
        "providerMessageId": msg["id"],
        "providerThreadId": msg.get("threadId") or msg["id"],
        "internetMessageId": headers.get("message-id") or None,
        "inReplyTo": headers.get("in-reply-to") or None,
        "references": headers.get("references") or None,
        "from": normalize_email(parse_address_list(headers.get("from"))[0] if parse_address_list(headers.get("from")) else headers.get("from")),
        "fromRaw": headers.get("from") or "",
        "to": parse_address_list(headers.get("to")),
        "cc": parse_address_list(headers.get("cc")),
        "bcc": parse_address_list(headers.get("bcc")),
        "subject": headers.get("subject") or "(no subject)",
        "textBody": text[:500000],
        "sanitizedHtmlBody": sanitized[:500000],
        "snippet": (msg.get("snippet") or text[:240] or "")[:500],
        "receivedAt": received,
        "sentAt": received,
        "isRead": "UNREAD" not in label_ids,
        "direction": "inbound",
        "attachments": _attachments_meta(payload, msg["id"]),
        "providerLabels": label_ids,
    }


async def fetch_message(client: httpx.AsyncClient, token: str, message_id: str) -> dict:
    msg = await _get(client, f"/users/me/messages/{message_id}", token, {"format": "full"})
    return parse_gmail_message(msg)


async def list_inbox_message_ids(
    token: str,
    *,
    max_results: int = 50,
    page_token: str = None,
) -> Tuple[List[str], Optional[str], Optional[str]]:
    """List message IDs in INBOX (excludes spam/trash by default via label)."""
    params = {
        "labelIds": "INBOX",
        "maxResults": min(max_results, 100),
    }
    if page_token:
        params["pageToken"] = page_token
    async with httpx.AsyncClient(timeout=60) as client:
        data = await _get(client, "/users/me/messages", token, params)
        ids = [m["id"] for m in (data.get("messages") or [])]
        return ids, data.get("nextPageToken"), str(data.get("resultSizeEstimate") or "")


async def history_message_ids(token: str, start_history_id: str, *, max_results: int = 100) -> Tuple[List[str], Optional[str], bool]:
    """Return (message_ids, new_history_id, cursor_invalid)."""
    params = {
        "startHistoryId": start_history_id,
        "historyTypes": "messageAdded",
        "labelId": "INBOX",
        "maxResults": min(max_results, 100),
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"{GMAIL_API}/users/me/history",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        if r.status_code == 404:
            return [], None, True  # historyId too old
        if r.status_code == 401:
            raise PermissionError("Gmail token expired")
        if r.status_code == 429:
            raise RuntimeError("Gmail rate limit exceeded — retry later")
        r.raise_for_status()
        data = r.json()
        ids = []
        for h in data.get("history") or []:
            for added in h.get("messagesAdded") or []:
                mid = (added.get("message") or {}).get("id")
                labels = (added.get("message") or {}).get("labelIds") or []
                if mid and (not labels or "INBOX" in labels) and "SPAM" not in labels and "TRASH" not in labels:
                    ids.append(mid)
        # dedupe preserve order
        seen = set()
        unique = []
        for i in ids:
            if i not in seen:
                seen.add(i)
                unique.append(i)
        return unique, str(data.get("historyId") or start_history_id), False


async def fetch_messages_batch(token: str, message_ids: List[str], *, limit: int = 50) -> List[dict]:
    out = []
    async with httpx.AsyncClient(timeout=60) as client:
        for mid in message_ids[:limit]:
            try:
                out.append(await fetch_message(client, token, mid))
            except Exception:
                logger.exception("Failed to fetch Gmail message %s", mid)
    return out


async def download_attachment(token: str, message_id: str, attachment_id: str) -> Tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=60) as client:
        data = await _get(
            client,
            f"/users/me/messages/{message_id}/attachments/{attachment_id}",
            token,
        )
        raw = base64.urlsafe_b64decode((data.get("data") or "") + "==")
        return raw, "application/octet-stream"
