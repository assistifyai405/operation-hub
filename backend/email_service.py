"""Transactional email delivery via Resend, with a safe dev-mode fallback.

If RESEND_API_KEY is not set, emails are NOT sent — the caller falls back to
dev mode (link logged + surfaced in the API response). Set RESEND_API_KEY in
the environment to switch on real delivery with zero code changes.
"""
import os
import html
import asyncio
import logging

import resend

logger = logging.getLogger(__name__)

DEFAULT_FROM = "onboarding@resend.dev"


def _api_key() -> str:
    return (os.environ.get("RESEND_API_KEY") or "").strip()


def _from_email() -> str:
    return (os.environ.get("FROM_EMAIL") or DEFAULT_FROM).strip()


def is_enabled() -> bool:
    """True when real email delivery is configured."""
    return bool(_api_key())


async def _send(to_email: str, subject: str, html_content: str) -> dict:
    """Send one email. Never raises — returns a status dict the caller can log."""
    key = _api_key()
    if not key:
        logger.info(f"[EMAIL:DEV] Skipped '{subject}' to {to_email} (RESEND_API_KEY not set)")
        return {"sent": False, "mode": "dev"}
    resend.api_key = key
    params = {"from": _from_email(), "to": [to_email], "subject": subject, "html": html_content}
    try:
        res = await asyncio.to_thread(resend.Emails.send, params)
        email_id = res.get("id") if isinstance(res, dict) else getattr(res, "id", None)
        logger.info(f"[EMAIL:SENT] '{subject}' to {to_email} id={email_id}")
        return {"sent": True, "mode": "resend", "id": email_id}
    except Exception as e:
        logger.error(f"[EMAIL:FAIL] '{subject}' to {to_email}: {e}")
        return {"sent": False, "mode": "error", "error": str(e)}


def _shell(brand: dict, heading: str, body_html: str, cta_label: str, cta_url: str, footer_note: str) -> str:
    company = html.escape((brand or {}).get("company_name") or "Assistify OS")
    primary = (brand or {}).get("primary") or "#7C3AED"
    logo_url = (brand or {}).get("logo_url") or ""
    # Only embed logos that are publicly fetchable (email clients cannot pass auth).
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
