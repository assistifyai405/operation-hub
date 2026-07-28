"""Normalized provider send errors (safe for clients; no secrets)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TransportError(Exception):
    code: str
    message: str
    http_status: int = 400
    actionable: Optional[str] = None  # UI hint

    def __str__(self) -> str:
        return self.message


# Stable error codes
EXPIRED_AUTH = "expired_authorization"
INSUFFICIENT_SCOPES = "insufficient_scopes"
DISCONNECTED = "disconnected_integration"
INVALID_RECIPIENT = "invalid_recipient"
MAILBOX_MISMATCH = "mailbox_mismatch"
RATE_LIMITED = "rate_limited"
PROVIDER_UNAVAILABLE = "provider_unavailable"
ATTACHMENT_TOO_LARGE = "attachment_too_large"
AMBIGUOUS_DELIVERY = "ambiguous_delivery"
SENDER_MISMATCH = "sender_mismatch"
NOT_CONFIGURED = "not_configured"

ACTIONABLE = {
    EXPIRED_AUTH: "Reconnect Google Workspace or Microsoft 365 under Integrations.",
    INSUFFICIENT_SCOPES: "Reconnect the integration to grant mail send permission.",
    DISCONNECTED: "Reconnect the email integration under Integrations.",
    MAILBOX_MISMATCH: "Sender does not match the connected mailbox.",
    SENDER_MISMATCH: "Sender does not match the connected mailbox.",
    RATE_LIMITED: "Provider rate limit reached — retry later.",
    AMBIGUOUS_DELIVERY: "Delivery status could not be confirmed. Check the provider mailbox before retrying.",
    PROVIDER_UNAVAILABLE: "Email provider is temporarily unavailable — retry later.",
    ATTACHMENT_TOO_LARGE: "One or more attachments exceed the provider size limit.",
    INVALID_RECIPIENT: "One or more recipients are invalid.",
    NOT_CONFIGURED: "Email sending is not configured.",
}


def map_http_error(provider: str, status_code: int, body_text: str = "") -> TransportError:
    text = (body_text or "")[:300].lower()
    if status_code in (401, 403) and ("scope" in text or "insufficient" in text or "consent" in text):
        return TransportError(
            INSUFFICIENT_SCOPES,
            f"{provider} rejected the request due to missing mail permissions",
            403,
            ACTIONABLE[INSUFFICIENT_SCOPES],
        )
    if status_code == 401:
        return TransportError(
            EXPIRED_AUTH,
            f"{provider} authorization expired",
            401,
            ACTIONABLE[EXPIRED_AUTH],
        )
    if status_code == 429:
        return TransportError(
            RATE_LIMITED,
            f"{provider} rate limit reached",
            429,
            ACTIONABLE[RATE_LIMITED],
        )
    if status_code in (502, 503, 504):
        return TransportError(
            PROVIDER_UNAVAILABLE,
            f"{provider} is temporarily unavailable",
            503,
            ACTIONABLE[PROVIDER_UNAVAILABLE],
        )
    if status_code == 400 and ("recipient" in text or "address" in text):
        return TransportError(
            INVALID_RECIPIENT,
            f"{provider} rejected one or more recipients",
            400,
            ACTIONABLE[INVALID_RECIPIENT],
        )
    if status_code == 413 or "too large" in text or "size" in text and "attachment" in text:
        return TransportError(
            ATTACHMENT_TOO_LARGE,
            "Attachment exceeds provider size limit",
            400,
            ACTIONABLE[ATTACHMENT_TOO_LARGE],
        )
    return TransportError(
        PROVIDER_UNAVAILABLE,
        f"{provider} send failed (HTTP {status_code})",
        400,
        ACTIONABLE[PROVIDER_UNAVAILABLE],
    )
