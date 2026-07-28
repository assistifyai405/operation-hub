"""Provider webhooks (no JWT). Resend delivery events."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request

from config import get_settings
from core import db, now_iso

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks")


@router.post("/resend")
async def resend_webhook(request: Request):
    """Verify Svix signature and update delivery state idempotently.

    Configure in Resend dashboard → Webhooks → endpoint
    ``https://<api-host>/api/webhooks/resend`` with secret as RESEND_WEBHOOK_SECRET.
    """
    settings = get_settings()
    secret = (settings.resend_webhook_secret or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Resend webhooks are not configured")

    payload = (await request.body()).decode("utf-8")
    headers = {
        "id": request.headers.get("svix-id") or "",
        "timestamp": request.headers.get("svix-timestamp") or "",
        "signature": request.headers.get("svix-signature") or "",
    }
    try:
        import resend
        resend.Webhooks.verify({
            "payload": payload,
            "headers": headers,
            "webhook_secret": secret,
        })
    except ValueError as e:
        logger.warning("Resend webhook verification failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid webhook signature") from e
    except Exception as e:
        logger.error("Resend webhook verify error: %s", e)
        raise HTTPException(status_code=401, detail="Webhook verification failed") from e

    try:
        body = json.loads(payload)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    event_type = body.get("type") or body.get("event") or ""
    data = body.get("data") or {}
    provider_id = data.get("email_id") or data.get("id")
    svix_id = headers["id"]

    # Idempotency: skip if we've already processed this svix id
    if svix_id:
        existing = await db.email_webhook_events.find_one({"svixId": svix_id})
        if existing:
            return {"ok": True, "duplicate": True}

    delivery_map = {
        "email.delivered": "delivered",
        "email.bounced": "bounced",
        "email.complained": "complained",
        "email.failed": "failed",
        "email.delivery_delayed": "delayed",
    }
    delivery = delivery_map.get(event_type)

    if provider_id and delivery:
        await db.outbound_emails.update_one(
            {"providerMessageId": provider_id},
            {"$set": {
                "deliveryStatus": delivery,
                "deliveryUpdatedAt": now_iso(),
                "updatedAt": now_iso(),
            }},
        )

    await db.email_webhook_events.insert_one({
        "svixId": svix_id,
        "type": event_type,
        "providerMessageId": provider_id,
        "deliveryStatus": delivery,
        "createdAt": now_iso(),
    })
    return {"ok": True, "type": event_type, "deliveryStatus": delivery}
