"""Webhook event application (async-safe, org-scoped when possible)."""
from __future__ import annotations

from core import db, now_iso

# Delivery states that must not be overwritten by weaker events
_RANK = {
    "complained": 50,
    "bounced": 40,
    "failed": 30,
    "delivered": 20,
    "delayed": 10,
}


async def apply_resend_event(payload: dict) -> dict:
    event_type = payload.get("type") or ""
    data = payload.get("data") or {}
    provider_id = payload.get("providerMessageId") or data.get("email_id") or data.get("id")
    svix_id = payload.get("svixId")
    delivery_map = {
        "email.delivered": "delivered",
        "email.bounced": "bounced",
        "email.complained": "complained",
        "email.failed": "failed",
        "email.delivery_delayed": "delayed",
    }
    delivery = delivery_map.get(event_type)
    if not provider_id or not delivery:
        return {"ok": True, "skipped": True}

    email = await db.outbound_emails.find_one(
        {"providerMessageId": provider_id, "provider": "resend"},
        {"_id": 0, "id": 1, "organizationId": 1, "deliveryStatus": 1},
    )
    if not email:
        # Fallback without provider filter for legacy rows
        email = await db.outbound_emails.find_one(
            {"providerMessageId": provider_id},
            {"_id": 0, "id": 1, "organizationId": 1, "deliveryStatus": 1},
        )
    if email:
        current = email.get("deliveryStatus")
        if _RANK.get(delivery, 0) >= _RANK.get(current or "", 0):
            await db.outbound_emails.update_one(
                {"id": email["id"], "organizationId": email["organizationId"]},
                {"$set": {
                    "deliveryStatus": delivery,
                    "deliveryUpdatedAt": now_iso(),
                    "updatedAt": now_iso(),
                }},
            )
    if svix_id:
        await db.email_webhook_events.update_one(
            {"svixId": svix_id},
            {"$set": {
                "processedAt": now_iso(),
                "deliveryStatus": delivery,
                "matchedEmailId": (email or {}).get("id"),
            }},
            upsert=False,
        )
    return {"ok": True, "deliveryStatus": delivery, "emailId": (email or {}).get("id")}
