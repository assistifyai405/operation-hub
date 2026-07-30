"""Organization audit log helpers (team / security events)."""
from __future__ import annotations

import uuid
from typing import Any, Optional

from core import db, now_iso


async def write_audit(
    organization_id: str,
    action: str,
    *,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    target_user_id: Optional[str] = None,
    target_email: Optional[str] = None,
    meta: Optional[dict] = None,
) -> dict:
    entry = {
        "id": str(uuid.uuid4()),
        "organizationId": organization_id,
        "action": action,
        "actorId": actor_id,
        "actorEmail": actor_email,
        "targetUserId": target_user_id,
        "targetEmail": target_email,
        "meta": meta or {},
        "createdAt": now_iso(),
    }
    await db.audit_logs.insert_one(dict(entry))
    entry.pop("_id", None)
    return entry
