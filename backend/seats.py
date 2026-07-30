"""Seat-count helpers for future Stripe plan enforcement.

Does NOT enforce paid limits yet — only reports usage.
"""
from __future__ import annotations

from core import db


async def seat_usage(organization_id: str) -> dict:
    """Return active member + pending invitation counts for an organization."""
    active_members = await db.users.count_documents({"organizationId": organization_id})
    pending_invitations = await db.organization_invitations.count_documents({
        "organizationId": organization_id,
        "status": "pending",
    })
    return {
        "active_members": active_members,
        "pending_invitations": pending_invitations,
        "seats_used": active_members + pending_invitations,
        # Placeholder for future plan limits (Stripe). None = unlimited / not enforced.
        "seat_limit": None,
        "enforcement_enabled": False,
    }
