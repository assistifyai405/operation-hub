"""Execute automation actions against connected integrations."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import httpx

from integrations import store
from integrations.providers import get_provider

logger = logging.getLogger(__name__)


async def _ensure_google_token(org_id: str) -> tuple[dict, dict]:
    doc = await store.get_by_provider(org_id, "google")
    if not doc or doc.get("status") not in ("connected", "error"):
        raise RuntimeError("Google Workspace is not connected")
    creds = await store.load_credentials(doc)
    if not creds.get("access_token") and creds.get("refresh_token"):
        provider = get_provider("google")
        creds = await provider.refresh(creds)
        await store.save_credentials(org_id, doc["id"], creds, status="connected", healthStatus="healthy")
    return doc, creds


async def _ensure_microsoft_token(org_id: str) -> tuple[dict, dict]:
    doc = await store.get_by_provider(org_id, "microsoft")
    if not doc or doc.get("status") not in ("connected", "error"):
        raise RuntimeError("Microsoft 365 is not connected")
    creds = await store.load_credentials(doc)
    if not creds.get("access_token") and creds.get("refresh_token"):
        provider = get_provider("microsoft")
        creds = await provider.refresh(creds)
        await store.save_credentials(org_id, doc["id"], creds, status="connected", healthStatus="healthy")
    return doc, creds


async def create_calendar_event(org_id: str, payload: dict) -> dict:
    """Create a Google or Microsoft calendar event (prefers Google if both connected)."""
    title = payload.get("title") or payload.get("summary") or "Assistify event"
    description = payload.get("description") or ""
    start = payload.get("start")  # ISO
    end = payload.get("end")
    provider_pref = (payload.get("provider") or "auto").lower()

    now = datetime.now(timezone.utc)
    if not start:
        start = (now + timedelta(hours=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if not end:
        end_dt = datetime.fromisoformat(start.replace("Z", "+00:00")) + timedelta(hours=1)
        end = end_dt.isoformat().replace("+00:00", "Z")

    use_ms = provider_pref == "microsoft"
    if provider_pref == "auto":
        g = await store.get_by_provider(org_id, "google")
        use_ms = not (g and g.get("status") == "connected")

    if use_ms:
        doc, creds = await _ensure_microsoft_token(org_id)
        body = {
            "subject": title,
            "body": {"contentType": "Text", "content": description},
            "start": {"dateTime": start.replace("Z", ""), "timeZone": "UTC"},
            "end": {"dateTime": end.replace("Z", ""), "timeZone": "UTC"},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://graph.microsoft.com/v1.0/me/events",
                headers={"Authorization": f"Bearer {creds['access_token']}", "Content-Type": "application/json"},
                json=body,
            )
            if r.status_code == 401:
                provider = get_provider("microsoft")
                creds = await provider.refresh(creds)
                await store.save_credentials(org_id, doc["id"], creds)
                r = await client.post(
                    "https://graph.microsoft.com/v1.0/me/events",
                    headers={"Authorization": f"Bearer {creds['access_token']}", "Content-Type": "application/json"},
                    json=body,
                )
            r.raise_for_status()
            data = r.json()
        await store.update_health(org_id, doc["id"], True, "Calendar event created")
        return {"provider": "microsoft", "eventId": data.get("id"), "webLink": data.get("webLink")}

    doc, creds = await _ensure_google_token(org_id)
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start if "T" in start else f"{start}T09:00:00Z", "timeZone": "UTC"},
        "end": {"dateTime": end if "T" in end else f"{end}T10:00:00Z", "timeZone": "UTC"},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {creds['access_token']}", "Content-Type": "application/json"},
            json=body,
        )
        if r.status_code == 401:
            provider = get_provider("google")
            creds = await provider.refresh(creds)
            await store.save_credentials(org_id, doc["id"], creds)
            r = await client.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={"Authorization": f"Bearer {creds['access_token']}", "Content-Type": "application/json"},
                json=body,
            )
        r.raise_for_status()
        data = r.json()
    await store.update_health(org_id, doc["id"], True, "Calendar event created")
    return {"provider": "google", "eventId": data.get("id"), "htmlLink": data.get("htmlLink")}


async def create_google_task(org_id: str, payload: dict) -> dict:
    doc, creds = await _ensure_google_token(org_id)
    title = payload.get("title") or "Follow-up"
    notes = payload.get("notes") or payload.get("description") or ""
    async with httpx.AsyncClient(timeout=30) as client:
        # Ensure default task list
        lists = await client.get(
            "https://tasks.googleapis.com/tasks/v1/users/@me/lists",
            headers={"Authorization": f"Bearer {creds['access_token']}"},
        )
        if lists.status_code == 401:
            provider = get_provider("google")
            creds = await provider.refresh(creds)
            await store.save_credentials(org_id, doc["id"], creds)
            lists = await client.get(
                "https://tasks.googleapis.com/tasks/v1/users/@me/lists",
                headers={"Authorization": f"Bearer {creds['access_token']}"},
            )
        lists.raise_for_status()
        items = (lists.json() or {}).get("items") or []
        list_id = items[0]["id"] if items else "@default"
        r = await client.post(
            f"https://tasks.googleapis.com/tasks/v1/lists/{list_id}/tasks",
            headers={"Authorization": f"Bearer {creds['access_token']}", "Content-Type": "application/json"},
            json={"title": title, "notes": notes},
        )
        r.raise_for_status()
        data = r.json()
    await store.update_health(org_id, doc["id"], True, "Google Task created")
    return {"provider": "google", "taskId": data.get("id"), "title": data.get("title")}


async def send_slack_message(org_id: str, payload: dict) -> dict:
    doc = await store.get_by_provider(org_id, "slack")
    if not doc or doc.get("status") not in ("connected", "error"):
        raise RuntimeError("Slack is not connected")
    creds = await store.load_credentials(doc)
    text = payload.get("text") or payload.get("message") or "Notification from Assistify"
    channel = payload.get("channel") or (doc.get("config") or {}).get("channel")
    webhook = creds.get("webhook_url")
    token = creds.get("access_token")

    async with httpx.AsyncClient(timeout=30) as client:
        if webhook:
            r = await client.post(webhook, json={"text": text})
            r.raise_for_status()
            await store.update_health(org_id, doc["id"], True, "Slack message sent")
            return {"provider": "slack", "via": "webhook"}
        if not token:
            raise RuntimeError("Slack credentials incomplete")
        body = {"text": text}
        if channel:
            body["channel"] = channel
        r = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        )
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("error") or "Slack chat.postMessage failed")
    await store.update_health(org_id, doc["id"], True, "Slack message sent")
    return {"provider": "slack", "via": "api", "ts": data.get("ts")}


async def send_discord_message(org_id: str, payload: dict) -> dict:
    doc = await store.get_by_provider(org_id, "discord")
    if not doc or doc.get("status") not in ("connected", "error"):
        raise RuntimeError("Discord is not connected")
    creds = await store.load_credentials(doc)
    url = creds.get("webhook_url")
    if not url:
        raise RuntimeError("Discord webhook URL missing")
    content = payload.get("content") or payload.get("text") or payload.get("message") or "Notification from Assistify"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json={"content": content[:2000]})
        r.raise_for_status()
    await store.update_health(org_id, doc["id"], True, "Discord message sent")
    return {"provider": "discord", "via": "webhook"}


async def trigger_webhook(org_id: str, payload: dict, *, prefer: str = "auto") -> dict:
    """Fire Zapier or generic webhook. prefer: zapier | webhook | auto."""
    providers = []
    if prefer == "zapier":
        providers = ["zapier"]
    elif prefer == "webhook":
        providers = ["webhook"]
    else:
        providers = ["zapier", "webhook"]

    last_err = None
    for pid in providers:
        doc = await store.get_by_provider(org_id, pid)
        if not doc or doc.get("status") not in ("connected", "error"):
            continue
        creds = await store.load_credentials(doc)
        url = creds.get("webhook_url")
        if not url:
            continue
        body = payload.get("body") if isinstance(payload.get("body"), dict) else {
            "event": payload.get("event") or "assistify.automation",
            "message": payload.get("message") or payload.get("text"),
            "data": payload.get("data") or payload,
        }
        headers = {"Content-Type": "application/json"}
        secret = creds.get("signing_secret")
        if secret:
            headers["X-Assistify-Secret"] = secret
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, json=body, headers=headers)
                r.raise_for_status()
            await store.update_health(org_id, doc["id"], True, f"{pid} webhook triggered")
            return {"provider": pid, "status_code": r.status_code}
        except Exception as e:
            last_err = e
            logger.exception("webhook trigger failed for %s", pid)
    raise RuntimeError(str(last_err) if last_err else "No webhook integration connected")
