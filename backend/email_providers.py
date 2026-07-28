"""Outbound email provider interface (Resend + console).

Provider API keys never leave the backend. Console never contacts external services.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    to: List[str]
    subject: str
    html: str
    text: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    # Internal tags only — never arbitrary headers
    tags: Optional[List[dict]] = None


@dataclass
class SendResult:
    ok: bool
    provider: str
    provider_message_id: Optional[str] = None
    error: Optional[str] = None
    preview: Optional[dict] = None  # safe metadata for console/dev


class EmailProvider(Protocol):
    name: str

    def is_configured(self) -> bool:
        ...

    async def send(self, message: EmailMessage) -> SendResult:
        ...


class ConsoleEmailProvider:
    """Development/test provider — validates and logs safe metadata only."""

    name = "console"

    def is_configured(self) -> bool:
        return True

    async def send(self, message: EmailMessage) -> SendResult:
        mid = f"console_{abs(hash((message.subject, tuple(message.to)))) % 10**12}"
        preview = {
            "to": message.to,
            "cc": message.cc or [],
            "bcc_count": len(message.bcc or []),
            "subject": message.subject,
            "from": _format_from(message),
            "reply_to": message.reply_to,
            "html_bytes": len(message.html or ""),
            "text_bytes": len(message.text or ""),
        }
        logger.info(
            "[EMAIL:CONSOLE] subject=%r to=%s cc=%s bcc=%d from=%s id=%s",
            message.subject,
            message.to,
            message.cc or [],
            len(message.bcc or []),
            _format_from(message),
            mid,
        )
        return SendResult(ok=True, provider=self.name, provider_message_id=mid, preview=preview)


class ResendEmailProvider:
    name = "resend"

    def __init__(self, api_key: str, default_from: str, default_from_name: str = "", default_reply_to: str = ""):
        self.api_key = (api_key or "").strip()
        self.default_from = default_from
        self.default_from_name = default_from_name
        self.default_reply_to = default_reply_to

    def is_configured(self) -> bool:
        return bool(self.api_key and self.default_from)

    async def send(self, message: EmailMessage) -> SendResult:
        if not self.is_configured():
            return SendResult(
                ok=False,
                provider=self.name,
                error="Resend is not configured (RESEND_API_KEY / FROM_EMAIL required)",
            )
        import resend

        resend.api_key = self.api_key
        from_addr = message.from_email or self.default_from
        from_name = message.from_name or self.default_from_name
        params = {
            "from": f"{from_name} <{from_addr}>" if from_name else from_addr,
            "to": message.to,
            "subject": message.subject,
            "html": message.html,
        }
        if message.text:
            params["text"] = message.text
        if message.cc:
            params["cc"] = message.cc
        if message.bcc:
            params["bcc"] = message.bcc
        reply = message.reply_to or self.default_reply_to
        if reply:
            params["reply_to"] = reply
        if message.tags:
            params["tags"] = message.tags
        try:
            res = await asyncio.to_thread(resend.Emails.send, params)
            email_id = res.get("id") if isinstance(res, dict) else getattr(res, "id", None)
            logger.info("[EMAIL:RESEND] subject=%r to=%s id=%s", message.subject, message.to, email_id)
            return SendResult(ok=True, provider=self.name, provider_message_id=email_id)
        except Exception as e:
            logger.error("[EMAIL:RESEND:FAIL] subject=%r to=%s err=%s", message.subject, message.to, e)
            return SendResult(ok=False, provider=self.name, error=str(e))


def _format_from(message: EmailMessage) -> str:
    if message.from_name and message.from_email:
        return f"{message.from_name} <{message.from_email}>"
    return message.from_email or ""


def get_email_provider(settings=None) -> EmailProvider:
    import os
    from config import get_settings

    s = settings or get_settings()
    provider = (os.environ.get("EMAIL_PROVIDER") or s.email_provider or "console").lower()
    if provider == "resend":
        key = os.environ.get("RESEND_API_KEY")
        if key is None:
            key = s.resend_api_key or ""
        from_email = os.environ.get("FROM_EMAIL") or s.from_email
        from_name = os.environ.get("FROM_NAME") or s.from_name or ""
        reply_to = os.environ.get("REPLY_TO_EMAIL")
        if reply_to is None:
            reply_to = s.reply_to_email or ""
        return ResendEmailProvider(
            api_key=key or "",
            default_from=from_email,
            default_from_name=from_name,
            default_reply_to=reply_to or "",
        )
    if provider != "console":
        logger.warning("Unknown EMAIL_PROVIDER=%r — using console", provider)
    return ConsoleEmailProvider()


def outbound_sending_allowed(settings=None) -> tuple[bool, str]:
    """Gate for product/outbound sends (not transactional auth mail)."""
    import os
    from config import get_settings

    s = settings or get_settings()
    raw = os.environ.get("EMAIL_SENDING_ENABLED")
    if raw is not None and str(raw).strip() != "":
        enabled = str(raw).strip().lower() in {"1", "true", "yes", "on"}
    else:
        enabled = bool(s.email_sending_enabled)
    if not enabled:
        return False, "Email sending is disabled (EMAIL_SENDING_ENABLED=false)"
    provider_name = (os.environ.get("EMAIL_PROVIDER") or s.email_provider or "console").lower()
    provider = get_email_provider(s)
    if provider_name == "resend" and not provider.is_configured():
        return False, "Resend provider is not configured"
    return True, ""
