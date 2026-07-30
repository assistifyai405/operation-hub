"""Transactional email delivery (verify / reset / invite).

Uses the shared email provider (Resend or console). Transactional mail is NOT
gated by EMAIL_SENDING_ENABLED so auth flows keep working in development.
"""
from __future__ import annotations

import html
import logging
from typing import Optional

from email_providers import EmailMessage, get_email_provider

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    """True when real (external) email delivery is configured — i.e. Resend with a key.

    Console provider is always "configured" for local testing but is not real delivery;
    callers use this to decide whether to surface invitation links in API responses.
    """
    try:
        from config import get_settings
        import os
        provider = (os.environ.get("EMAIL_PROVIDER") or get_settings().email_provider or "console").lower()
        if provider != "resend":
            return False
        return get_email_provider().is_configured()
    except Exception:
        return False


async def _send(to_email: str, subject: str, html_content: str) -> dict:
    """Send one transactional email. Never raises — returns a status dict."""
    try:
        provider = get_email_provider()
    except Exception as e:
        logger.error("[EMAIL:TX] provider unavailable: %s", e)
        return {"sent": False, "mode": "error", "error": str(e)}

    if not provider.is_configured():
        logger.info("[EMAIL:TX] Skipped '%s' to %s (provider not configured)", subject, to_email)
        return {"sent": False, "mode": "unconfigured"}

    result = await provider.send(EmailMessage(to=[to_email], subject=subject, html=html_content))
    if result.ok:
        return {
            "sent": True,
            "mode": result.provider,
            "id": result.provider_message_id,
            "preview": result.preview,
        }
    return {"sent": False, "mode": "error", "error": result.error}


def _shell(brand: dict, heading: str, body_html: str, cta_label: str, cta_url: str, footer_note: str) -> str:
    company = html.escape((brand or {}).get("company_name") or "Assistify OS")
    primary = (brand or {}).get("primary") or "#7C3AED"
    logo_url = (brand or {}).get("logo_url") or ""
    show_logo = logo_url.startswith("http") and "/api/settings/image/" not in logo_url
    header_inner = (
        f'<img src="{html.escape(logo_url)}" alt="{company}" height="36" style="height:36px;display:block;border:0;" />'
        if show_logo else
        f'<span style="font-size:20px;font-weight:700;color:#ffffff;letter-spacing:-0.3px;">{company}</span>'
    )
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background-color:#0b0b12;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0b0b12;padding:32px 0;">
    <tr><td align="center">
      <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="width:480px;max-width:92%;background-color:#14141f;border-radius:16px;overflow:hidden;border:1px solid #23232f;">
        <tr><td style="background-color:{primary};padding:22px 28px;">{header_inner}</td></tr>
        <tr><td style="padding:32px 28px 8px 28px;">
          <h1 style="margin:0 0 12px 0;font-size:22px;line-height:1.3;color:#f4f4f6;font-weight:700;">{html.escape(heading)}</h1>
          <div style="font-size:15px;line-height:1.6;color:#b8b8c4;">{body_html}</div>
        </td></tr>
        <tr><td style="padding:20px 28px 8px 28px;">
          <table role="presentation" cellpadding="0" cellspacing="0"><tr>
            <td style="border-radius:10px;background-color:{primary};">
              <a href="{html.escape(cta_url)}" style="display:inline-block;padding:13px 26px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:10px;">{html.escape(cta_label)}</a>
            </td>
          </tr></table>
        </td></tr>
        <tr><td style="padding:16px 28px 28px 28px;">
          <p style="margin:0 0 6px 0;font-size:12px;line-height:1.6;color:#6c6c7a;">If the button doesn't work, copy and paste this link into your browser:</p>
          <p style="margin:0;font-size:12px;line-height:1.6;word-break:break-all;"><a href="{html.escape(cta_url)}" style="color:{primary};">{html.escape(cta_url)}</a></p>
        </td></tr>
        <tr><td style="padding:18px 28px;border-top:1px solid #23232f;">
          <p style="margin:0;font-size:12px;line-height:1.6;color:#6c6c7a;">{html.escape(footer_note)}</p>
          <p style="margin:8px 0 0 0;font-size:12px;color:#4a4a57;">© {company}</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


async def send_verification_email(to_email: str, verify_link: str, brand: dict = None) -> dict:
    company = (brand or {}).get("company_name") or "Assistify OS"
    body = (
        f"Welcome to {html.escape(company)}! Please confirm your email address to "
        "secure your account and unlock all features."
    )
    html_content = _shell(
        brand, "Verify your email", body,
        "Verify email", verify_link,
        "This link expires in 48 hours. If you didn't create this account, you can ignore this email.",
    )
    return await _send(to_email, f"Verify your email · {company}", html_content)


async def send_password_reset_email(to_email: str, reset_link: str, brand: dict = None) -> dict:
    company = (brand or {}).get("company_name") or "Assistify OS"
    body = (
        "We received a request to reset your password. Click the button below to "
        "choose a new one."
    )
    html_content = _shell(
        brand, "Reset your password", body,
        "Reset password", reset_link,
        "This link expires in 1 hour. If you didn't request a password reset, you can safely ignore this email.",
    )
    return await _send(to_email, f"Reset your password · {company}", html_content)


async def send_invitation_email(
    to_email: str,
    invite_link: str,
    brand: dict = None,
    *,
    inviter_name: str = "",
    role: str = "member",
    org_name: str = "your team",
) -> dict:
    company = (brand or {}).get("company_name") or org_name or "Assistify OS"
    who = html.escape(inviter_name or "A teammate")
    org = html.escape(org_name or company)
    role_label = html.escape((role or "member").capitalize())
    body = (
        f"{who} invited you to join <strong style=\"color:#f4f4f6;\">{org}</strong> "
        f"on Assistify OS as a <strong style=\"color:#f4f4f6;\">{role_label}</strong>."
    )
    html_content = _shell(
        brand, f"Join {org}", body,
        "Accept invitation", invite_link,
        "This invitation expires soon. If you weren't expecting it, you can ignore this email.",
    )
    return await _send(to_email, f"You're invited to {company}", html_content)
