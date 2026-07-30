"""Inbox event recording for future automation triggers."""
from __future__ import annotations

import uuid
from typing import Any, Optional

from core import db, now_iso

INBOX_EVENTS = (
    "inbound_message_received",
    "thread_created",
    "unread_message_received",
    "message_linked_to_client",
    "message_linked_to_lead",
)


async def record_inbox_event(
    org_id: str,
    event_type: str,
    *,
    mailbox_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    message_id: Optional[str] = None,
    meta: Optional[dict] = None,
) -> dict:
    if event_type not in INBOX_EVENTS:
        event_type = event_type or "inbound_message_received"
    entry = {
        "id": str(uuid.uuid4()),
        "organizationId": org_id,
        "type": event_type,
        "mailboxId": mailbox_id,
        "threadId": thread_id,
        "messageId": message_id,
        "meta": meta or {},
        "createdAt": now_iso(),
    }
    await db.inbox_events.insert_one(dict(entry))
    # Also append to automation_logs for visibility
    await db.automation_logs.insert_one({
        "id": str(uuid.uuid4()),
        "organizationId": org_id,
        "level": "info",
        "event": f"inbox.{event_type}",
        "message": f"Inbox event: {event_type}",
        "meta": {"mailboxId": mailbox_id, "threadId": thread_id, "messageId": message_id, **(meta or {})},
        "created_at": now_iso(),
    })
    return entry
