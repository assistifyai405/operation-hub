"""CRM matching for inbound senders (org-scoped)."""
from __future__ import annotations

from core import db
from inbox.sanitize import normalize_email


async def match_sender(org_id: str, sender_email: str) -> dict:
    """Return strongest unambiguous match for a sender email.

    Priority: client > lead. Never creates records. Never crosses organizations.
    """
    email = normalize_email(sender_email)
    empty = {"matchType": None, "clientId": None, "leadId": None, "contactId": None, "matchedEmail": email or None}
    if not email or "@" not in email:
        return empty

    clients = await db.clients.find(
        {"organizationId": org_id, "email": {"$exists": True, "$ne": ""}},
        {"_id": 0, "id": 1, "name": 1, "email": 1},
    ).to_list(10000)
    client = next((c for c in clients if normalize_email(c.get("email")) == email), None)
    if client:
        return {
            "matchType": "client",
            "clientId": client["id"],
            "leadId": None,
            "contactId": client["id"],
            "matchedName": client.get("name"),
            "matchedEmail": email,
        }

    leads = await db.leads.find(
        {"organizationId": org_id, "email": {"$exists": True, "$ne": ""}},
        {"_id": 0, "id": 1, "name": 1, "contact_name": 1, "email": 1},
    ).to_list(10000)
    lead = next((l for l in leads if normalize_email(l.get("email")) == email), None)
    if lead:
        return {
            "matchType": "lead",
            "clientId": None,
            "leadId": lead["id"],
            "contactId": None,
            "matchedName": lead.get("name") or lead.get("contact_name"),
            "matchedEmail": email,
        }

    return empty
