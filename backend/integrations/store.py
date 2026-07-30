"""Organization-scoped integration persistence helpers."""
from __future__ import annotations

import uuid
from typing import Any, Optional

from core import db, now_iso
from integrations.base import PROVIDER_CATALOG
from integrations.crypto import decrypt_credentials, encrypt_credentials, public_safe


async def list_integrations(org_id: str) -> list:
    items = await db.integrations.find(
        {"organizationId": org_id},
        {"_id": 0, "encryptedCredentials": 0},
    ).sort("provider", 1).to_list(50)
    # Ensure catalog completeness — disconnected stubs for missing providers
    by_provider = {i["provider"]: i for i in items}
    out = []
    for pid, meta in PROVIDER_CATALOG.items():
        if pid in by_provider:
            out.append(public_safe(by_provider[pid]))
        else:
            out.append({
                "id": None,
                "organizationId": org_id,
                "provider": pid,
                "name": meta.name,
                "status": "disconnected",
                "services": meta.services,
                "permissions": [],
                "lastSyncAt": None,
                "lastHealthCheckAt": None,
                "healthStatus": None,
                "healthMessage": None,
                "accountEmail": None,
                "connectedAt": None,
                "config": {},
            })
    return out


async def get_by_provider(org_id: str, provider: str) -> Optional[dict]:
    return await db.integrations.find_one(
        {"organizationId": org_id, "provider": provider},
        {"_id": 0},
    )


async def get_by_id(org_id: str, integration_id: str) -> Optional[dict]:
    return await db.integrations.find_one(
        {"id": integration_id, "organizationId": org_id},
        {"_id": 0},
    )


async def upsert_connection(
    *,
    org_id: str,
    provider: str,
    user: dict,
    credentials: dict,
    account_email: str = "",
    account_name: str = "",
    permissions: list = None,
    services: list = None,
    config: dict = None,
    status: str = "connected",
) -> dict:
    meta = PROVIDER_CATALOG[provider]
    existing = await get_by_provider(org_id, provider)
    now = now_iso()
    blob = encrypt_credentials(credentials)
    doc = {
        "organizationId": org_id,
        "provider": provider,
        "name": meta.name,
        "status": status,
        "services": services or meta.services,
        "permissions": permissions or meta.permissions,
        "accountEmail": account_email or None,
        "accountName": account_name or None,
        "encryptedCredentials": blob,
        "config": config or {},
        "lastSyncAt": now,
        "lastHealthCheckAt": now,
        "healthStatus": "healthy",
        "healthMessage": "Connected",
        "connectedBy": user.get("id"),
        "connectedAt": (existing or {}).get("connectedAt") or now,
        "updatedAt": now,
        "error": None,
    }
    if existing:
        await db.integrations.update_one(
            {"id": existing["id"], "organizationId": org_id},
            {"$set": doc},
        )
        doc["id"] = existing["id"]
    else:
        doc["id"] = str(uuid.uuid4())
        await db.integrations.insert_one(dict(doc))
    return public_safe(doc)


async def mark_disconnected(org_id: str, provider: str) -> Optional[dict]:
    existing = await get_by_provider(org_id, provider)
    if not existing:
        return None
    await db.integrations.update_one(
        {"id": existing["id"], "organizationId": org_id},
        {"$set": {
            "status": "disconnected",
            "encryptedCredentials": None,
            "permissions": [],
            "healthStatus": None,
            "healthMessage": "Disconnected",
            "updatedAt": now_iso(),
            "error": None,
        }},
    )
    return public_safe(await get_by_id(org_id, existing["id"]))


async def load_credentials(doc: dict) -> dict:
    blob = (doc or {}).get("encryptedCredentials")
    if not blob:
        return {}
    return decrypt_credentials(blob)


async def save_credentials(org_id: str, integration_id: str, credentials: dict, **extra) -> None:
    updates = {
        "encryptedCredentials": encrypt_credentials(credentials),
        "updatedAt": now_iso(),
        "lastSyncAt": now_iso(),
        **extra,
    }
    await db.integrations.update_one(
        {"id": integration_id, "organizationId": org_id},
        {"$set": updates},
    )


async def update_health(org_id: str, integration_id: str, ok: bool, message: str) -> None:
    await db.integrations.update_one(
        {"id": integration_id, "organizationId": org_id},
        {"$set": {
            "healthStatus": "healthy" if ok else "error",
            "healthMessage": (message or "")[:500],
            "lastHealthCheckAt": now_iso(),
            "updatedAt": now_iso(),
            "status": "connected" if ok else "error",
            "error": None if ok else (message or "")[:500],
        }},
    )
