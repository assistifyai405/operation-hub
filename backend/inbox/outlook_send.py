"""Microsoft Graph native send / reply."""
from __future__ import annotations

import base64
import logging
from typing import List, Optional

import httpx

from inbox.transport_errors import (
    ACTIONABLE,
    AMBIGUOUS_DELIVERY,
    TransportError,
    map_http_error,
)

logger = logging.getLogger(__name__)
GRAPH = "https://graph.microsoft.com/v1.0"
MAX_TOTAL_ATTACHMENT_BYTES = 20 * 1024 * 1024


def _recipient(addr: str) -> dict:
    return {"emailAddress": {"address": addr}}


def _message_payload(
    *,
    subject: str,
    text_body: str,
    html_body: str,
    to: List[str],
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[dict]] = None,
) -> dict:
    content = html_body or text_body or ""
    content_type = "HTML" if html_body else "Text"
    msg = {
        "subject": subject,
        "body": {"contentType": content_type, "content": content},
        "toRecipients": [_recipient(a) for a in to],
    }
    if cc:
        msg["ccRecipients"] = [_recipient(a) for a in cc]
    if bcc:
        msg["bccRecipients"] = [_recipient(a) for a in bcc]
    if attachments:
        total = 0
        graph_atts = []
        for att in attachments:
            data = att.get("content") or b""
            total += len(data)
            if total > MAX_TOTAL_ATTACHMENT_BYTES:
                raise TransportError(
                    "attachment_too_large",
                    "Attachments exceed maximum size for Outlook send",
                    400,
                    ACTIONABLE.get("attachment_too_large"),
                )
            graph_atts.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": att.get("filename") or "attachment",
                "contentType": att.get("mimeType") or "application/octet-stream",
                "contentBytes": base64.b64encode(data).decode("ascii"),
            })
        msg["attachments"] = graph_atts
    return msg


async def send_outlook_message(
    token: str,
    *,
    to: List[str],
    subject: str,
    text_body: str = "",
    html_body: str = "",
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    reply_to_provider_message_id: Optional[str] = None,
    attachments: Optional[List[dict]] = None,
) -> dict:
    """Send new mail or reply via Graph. Prefer createReply when replying."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60) as client:
        draft_id = None
        conversation_id = None
        internet_message_id = None

        if reply_to_provider_message_id:
            # createReply → patch body/recipients → send (preserves conversation)
            r = await client.post(
                f"{GRAPH}/me/messages/{reply_to_provider_message_id}/createReply",
                headers=headers,
            )
            if r.status_code >= 400:
                logger.warning("[OUTLOOK:REPLY:FAIL] status=%s", r.status_code)
                raise map_http_error("Microsoft", r.status_code, r.text)
            draft = r.json()
            draft_id = draft.get("id")
            conversation_id = draft.get("conversationId")
            internet_message_id = draft.get("internetMessageId")
            patch = {
                "subject": subject,
                "body": {
                    "contentType": "HTML" if html_body else "Text",
                    "content": html_body or text_body or "",
                },
                "toRecipients": [_recipient(a) for a in to],
            }
            if cc:
                patch["ccRecipients"] = [_recipient(a) for a in cc]
            if bcc:
                patch["bccRecipients"] = [_recipient(a) for a in bcc]
            pr = await client.patch(f"{GRAPH}/me/messages/{draft_id}", headers=headers, json=patch)
            if pr.status_code >= 400:
                raise map_http_error("Microsoft", pr.status_code, pr.text)
            if attachments:
                for att in attachments:
                    data = att.get("content") or b""
                    ar = await client.post(
                        f"{GRAPH}/me/messages/{draft_id}/attachments",
                        headers=headers,
                        json={
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": att.get("filename") or "attachment",
                            "contentType": att.get("mimeType") or "application/octet-stream",
                            "contentBytes": base64.b64encode(data).decode("ascii"),
                        },
                    )
                    if ar.status_code >= 400:
                        raise map_http_error("Microsoft", ar.status_code, ar.text)
        else:
            # Create draft then send so we retain ids
            payload = _message_payload(
                subject=subject, text_body=text_body, html_body=html_body,
                to=to, cc=cc, bcc=bcc, attachments=attachments,
            )
            r = await client.post(f"{GRAPH}/me/messages", headers=headers, json=payload)
            if r.status_code >= 400:
                logger.warning("[OUTLOOK:DRAFT:FAIL] status=%s", r.status_code)
                raise map_http_error("Microsoft", r.status_code, r.text)
            draft = r.json()
            draft_id = draft.get("id")
            conversation_id = draft.get("conversationId")
            internet_message_id = draft.get("internetMessageId")

        if not draft_id:
            raise TransportError(
                AMBIGUOUS_DELIVERY,
                "Microsoft Graph did not return a draft id",
                502,
                ACTIONABLE[AMBIGUOUS_DELIVERY],
            )

        sr = await client.post(f"{GRAPH}/me/messages/{draft_id}/send", headers=headers)
        # Graph returns 202 Accepted with empty body on success
        if sr.status_code not in (202, 200):
            logger.warning("[OUTLOOK:SEND:FAIL] status=%s", sr.status_code)
            raise map_http_error("Microsoft", sr.status_code, sr.text)

        # Confirm by reading the message (still addressable by id after send)
        confirmed = False
        provider_message_id = draft_id
        try:
            gr = await client.get(
                f"{GRAPH}/me/messages/{draft_id}",
                headers=headers,
                params={"$select": "id,conversationId,internetMessageId,isDraft,sentDateTime"},
            )
            if gr.status_code == 200:
                g = gr.json()
                confirmed = not g.get("isDraft", True)
                provider_message_id = g.get("id") or draft_id
                conversation_id = g.get("conversationId") or conversation_id
                internet_message_id = g.get("internetMessageId") or internet_message_id
            elif gr.status_code == 404:
                # Sent items may move; treat 202 + missing draft as likely sent
                confirmed = True
        except Exception:
            confirmed = False

        logger.info(
            "[OUTLOOK:SEND] conversation=%s message=%s confirmed=%s to_count=%d",
            conversation_id, provider_message_id, confirmed, len(to),
        )
        if not confirmed and not internet_message_id:
            raise TransportError(
                AMBIGUOUS_DELIVERY,
                "Microsoft Graph accepted send but delivery could not be confirmed",
                502,
                ACTIONABLE[AMBIGUOUS_DELIVERY],
            )

        return {
            "ok": True,
            "provider": "microsoft",
            "providerMessageId": provider_message_id,
            "providerThreadId": conversation_id,
            "providerConversationId": conversation_id,
            "internetMessageId": internet_message_id,
            "providerRawStatus": "sent" if confirmed else "accepted_unconfirmed",
            "deliveryConfirmed": confirmed,
        }
