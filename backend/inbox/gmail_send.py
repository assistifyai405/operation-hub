"""Gmail API native send (MIME + threadId)."""
from __future__ import annotations

import base64
import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from typing import List, Optional, Tuple

import httpx

from inbox.transport_errors import TransportError, map_http_error, AMBIGUOUS_DELIVERY, ACTIONABLE

logger = logging.getLogger(__name__)
GMAIL_API = "https://gmail.googleapis.com/gmail/v1"

# Soft limit for total encoded payload (~25MB Gmail; we stay under)
MAX_TOTAL_ATTACHMENT_BYTES = 20 * 1024 * 1024


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def build_mime(
    *,
    from_email: str,
    from_name: str,
    to: List[str],
    subject: str,
    text_body: str = "",
    html_body: str = "",
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
    internet_message_id: Optional[str] = None,
    attachments: Optional[List[dict]] = None,
) -> Tuple[str, str]:
    """Return (raw_b64url, internet_message_id)."""
    msg_id = internet_message_id or make_msgid(domain=(from_email.split("@")[-1] if "@" in from_email else "assistify.local"))
    if not msg_id.startswith("<"):
        msg_id = f"<{msg_id}>"

    root = MIMEMultipart("mixed") if attachments else None
    alt = MIMEMultipart("alternative")
    if text_body:
        alt.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        alt.attach(MIMEText(html_body, "html", "utf-8"))
    elif text_body:
        pass
    else:
        alt.attach(MIMEText("", "plain", "utf-8"))

    if root is None:
        msg = alt
    else:
        root.attach(alt)
        total = 0
        for att in attachments or []:
            data = att.get("content") or b""
            total += len(data)
            if total > MAX_TOTAL_ATTACHMENT_BYTES:
                raise TransportError(
                    "attachment_too_large",
                    "Attachments exceed maximum size for Gmail send",
                    400,
                    ACTIONABLE.get("attachment_too_large"),
                )
            part = MIMEApplication(data, Name=att.get("filename") or "attachment")
            part.add_header("Content-Disposition", "attachment", filename=att.get("filename") or "attachment")
            if att.get("mimeType"):
                part.set_type(att["mimeType"])
            root.attach(part)
        msg = root

    msg["From"] = formataddr((from_name or "", from_email))
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if bcc:
        msg["Bcc"] = ", ".join(bcc)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = msg_id
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to if in_reply_to.startswith("<") else f"<{in_reply_to}>"
    if references:
        msg["References"] = references

    raw = _b64url(msg.as_bytes())
    return raw, msg_id


async def send_gmail_message(
    token: str,
    *,
    from_email: str,
    from_name: str = "",
    to: List[str],
    subject: str,
    text_body: str = "",
    html_body: str = "",
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    thread_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
    attachments: Optional[List[dict]] = None,
) -> dict:
    """Send via Gmail API. Returns safe metadata dict."""
    raw, msg_id = build_mime(
        from_email=from_email,
        from_name=from_name,
        to=to,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        cc=cc,
        bcc=bcc,
        in_reply_to=in_reply_to,
        references=references,
        attachments=attachments,
    )
    body = {"raw": raw}
    if thread_id:
        body["threadId"] = thread_id

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{GMAIL_API}/users/me/messages/send",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        )
        if r.status_code >= 400:
            logger.warning("[GMAIL:SEND:FAIL] status=%s", r.status_code)
            raise map_http_error("Gmail", r.status_code, r.text)
        data = r.json()
        provider_message_id = data.get("id")
        provider_thread_id = data.get("threadId") or thread_id
        if not provider_message_id:
            raise TransportError(
                AMBIGUOUS_DELIVERY,
                "Gmail accepted the request but did not return a message id",
                502,
                ACTIONABLE[AMBIGUOUS_DELIVERY],
            )
        logger.info(
            "[GMAIL:SEND] thread=%s message=%s to_count=%d",
            provider_thread_id, provider_message_id, len(to),
        )
        return {
            "ok": True,
            "provider": "gmail",
            "providerMessageId": provider_message_id,
            "providerThreadId": provider_thread_id,
            "providerConversationId": provider_thread_id,
            "internetMessageId": msg_id,
            "providerRawStatus": "sent",
        }
