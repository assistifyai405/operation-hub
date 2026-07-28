"""Provider webhooks (no JWT). Resend delivery events."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from pymongo.errors import DuplicateKeyError

from config import get_settings
from core import db, now_iso

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks")


@router.post("/resend")
async def resend_webhook(request: Request):
    """Verify Svix signature and update delivery state idempotently.

    Invalid signatures are never acknowledged as successful.
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
        logger.warning("Resend webhook verification failed")
        raise HTTPException(status_code=401, detail="Invalid webhook signature") from e
    except Exception as e:
        logger.error("Resend webhook verify error: %s", type(e).__name__)
        raise HTTPException(status_code=401, detail="Webhook verification failed") from e

    try:
        body = json.loads(payload)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    event_type = body.get("type") or body.get("event") or ""
    data = body.get("data") or {}
    provider_id = data.get("email_id") or data.get("id")
    svix_id = headers["id"]

    # Atomic idempotency via unique svixId
    if svix_id:
        try:
            await db.email_webhook_events.insert_one({
                "svixId": svix_id,
                "type": event_type,
                "providerMessageId": provider_id,
                "deliveryStatus": None,
                "createdAt": now_iso(),
                "processedAt": None,
            })
        except DuplicateKeyError:
            return {"ok": True, "duplicate": True}
        except Exception:
            existing = await db.email_webhook_events.find_one({"svixId": svix_id})
            if existing:
                return {"ok": True, "duplicate": True}
            raise

    # Enqueue async processing (or run inline in sync mode)
    try:
        from jobs import enqueue
        import jobs.handlers  # noqa: F401
        await enqueue(
            "process_webhook",
            payload={
                "type": event_type,
                "data": {"email_id": provider_id, "id": provider_id},
                "providerMessageId": provider_id,
                "svixId": svix_id,
            },
            idempotency_key=f"webhook:resend:{svix_id}" if svix_id else None,
        )
    except Exception:
        # Fallback synchronous apply
        from jobs.webhooks import apply_resend_event
        await apply_resend_event({
            "type": event_type,
            "data": data,
            "providerMessageId": provider_id,
            "svixId": svix_id,
        })

    return {"ok": True, "type": event_type, "accepted": True}
