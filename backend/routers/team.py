"""Team members, invitations, and ownership transfer.

Membership is stored on users (organizationId + role) for backward compatibility
with single-owner organizations. Invitations live in organization_invitations
with SHA-256 hashed tokens (raw token never persisted).
"""
from __future__ import annotations

import hashlib
import logging
import re
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

import auth as A
import email_service
from audit import write_audit
from config import get_settings
from core import db, now_iso
from dependencies import current_user, current_org, public_user, rate_limit, _client_ip
from permissions import (
    ASSIGNABLE_ROLES, normalize_role, require_admin, require_owner,
    assert_can_invite, assert_can_change_role, assert_can_remove_member, role_at_least,
)
from seats import seat_usage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/team")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------- helpers ----------------
def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _public_invitation(inv: dict, *, include_dev_link: bool = False, raw_token: str = None) -> dict:
    out = {
        "id": inv["id"],
        "organizationId": inv["organizationId"],
        "email": inv["email"],
        "role": inv["role"],
        "invitedBy": inv.get("invitedBy"),
        "invitedByName": inv.get("invitedByName"),
        "createdAt": inv.get("createdAt"),
        "expiresAt": inv.get("expiresAt"),
        "acceptedAt": inv.get("acceptedAt"),
        "status": inv.get("status"),
    }
    if include_dev_link and raw_token:
        settings = get_settings()
        out["invitationLink"] = f"{settings.frontend_url}/invite/{raw_token}"
    return out


def _public_member(u: dict, *, current_user_id: str = None, owner_id: str = None) -> dict:
    return {
        "id": u["id"],
        "firstName": u.get("firstName", ""),
        "lastName": u.get("lastName", ""),
        "email": u.get("email"),
        "avatar": u.get("avatar", ""),
        "role": normalize_role(u.get("role")),
        "status": "active",
        "joinedAt": u.get("joinedAt") or u.get("createdAt"),
        "lastLogin": u.get("lastLogin"),
        "isCurrentUser": bool(current_user_id and u["id"] == current_user_id),
        "isOwner": bool(owner_id and u["id"] == owner_id) or normalize_role(u.get("role")) == "owner",
    }


async def _org(org_id: str) -> dict:
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


async def _find_invitation_by_raw_token(raw_token: str) -> Optional[dict]:
    if not raw_token or len(raw_token) < 16:
        return None
    th = _hash_token(raw_token)
    return await db.organization_invitations.find_one({"tokenHash": th}, {"_id": 0})


def _invitation_state(inv: dict) -> str:
    """Return pending|accepted|cancelled|expired for UI."""
    status = inv.get("status") or "pending"
    if status != "pending":
        return status
    exp = inv.get("expiresAt")
    if exp:
        try:
            expires = datetime.fromisoformat(exp.replace("Z", "+00:00"))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires:
                return "expired"
        except Exception:
            pass
    return "pending"


async def _mark_expired_if_needed(inv: dict) -> dict:
    if _invitation_state(inv) == "expired" and inv.get("status") == "pending":
        await db.organization_invitations.update_one(
            {"id": inv["id"], "status": "pending"},
            {"$set": {"status": "expired", "updatedAt": now_iso()}},
        )
        inv = {**inv, "status": "expired"}
    return inv


async def _can_leave_current_org(user: dict) -> tuple[bool, str]:
    """Whether the user may leave their current org to join another via invite."""
    role = normalize_role(user.get("role"))
    if role != "owner":
        return True, ""
    others = await db.users.count_documents({
        "organizationId": user["organizationId"],
        "id": {"$ne": user["id"]},
    })
    if others > 0:
        return False, (
            "You are the owner of another organization with remaining members. "
            "Transfer ownership there before joining this team."
        )
    return True, ""


async def _attach_user_to_org(user: dict, org_id: str, role: str) -> dict:
    """Move/set user into org_id with role. Caller must have validated leave rules."""
    now = now_iso()
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "organizationId": org_id,
            "role": normalize_role(role),
            "joinedAt": now,
            "updatedAt": now,
            "onboardingCompleted": True,
        }},
    )
    return await db.users.find_one({"id": user["id"]}, {"_id": 0})


# ---------------- request models ----------------
class InviteRequest(BaseModel):
    email: str
    role: str = "member"


class RoleUpdate(BaseModel):
    role: str


class TransferOwnership(BaseModel):
    userId: str = Field(..., min_length=1)


# ---------------- routes ----------------
@router.get("/members")
async def list_members(user: dict = Depends(current_user), org: str = Depends(current_org)):
    org_doc = await _org(org)
    members = await db.users.find(
        {"organizationId": org},
        {"_id": 0, "passwordHash": 0},
    ).sort("createdAt", 1).to_list(500)
    seats = await seat_usage(org)
    return {
        "organization": {"id": org_doc["id"], "name": org_doc.get("name"), "ownerId": org_doc.get("ownerId")},
        "members": [_public_member(m, current_user_id=user["id"], owner_id=org_doc.get("ownerId")) for m in members],
        "seats": seats,
        "viewerRole": normalize_role(user.get("role")),
    }


@router.get("/seats")
async def get_seats(org: str = Depends(current_org)):
    return await seat_usage(org)


@router.post("/invitations")
async def create_invitation(payload: InviteRequest, request: Request, actor: dict = Depends(require_admin)):
    rate_limit(f"invite:{actor['id']}", 30, 3600)
    org = actor["organizationId"]
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Please enter a valid email address")
    assert_can_invite(actor.get("role"), payload.role)
    role = normalize_role(payload.role)

    existing = await db.users.find_one({"email": email, "organizationId": org}, {"_id": 0, "id": 1})
    if existing:
        raise HTTPException(status_code=409, detail="This person is already a member of your organization")

    pending = await db.organization_invitations.find_one({
        "organizationId": org, "email": email, "status": "pending",
    })
    if pending and _invitation_state(pending) == "pending":
        raise HTTPException(status_code=409, detail="A pending invitation already exists for this email")
    if pending and _invitation_state(pending) == "expired":
        await _mark_expired_if_needed(pending)

    settings = get_settings()
    raw = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.invitation_expiry_days)
    inv = {
        "id": A.gen_id(),
        "organizationId": org,
        "email": email,
        "role": role,
        "tokenHash": _hash_token(raw),
        "invitedBy": actor["id"],
        "invitedByName": f"{actor.get('firstName', '')} {actor.get('lastName', '')}".strip() or actor.get("email"),
        "createdAt": now.isoformat(),
        "expiresAt": expires.isoformat(),
        "acceptedAt": None,
        "status": "pending",
    }
    await db.organization_invitations.insert_one(dict(inv))

    org_doc = await _org(org)
    invite_link = f"{settings.frontend_url}/invite/{raw}"
    brand = {
        "company_name": org_doc.get("name") or "Assistify",
        "primary": "#16A34A",
        "logo_url": "",
    }
    await email_service.send_invitation_email(
        email, invite_link, brand,
        inviter_name=inv["invitedByName"],
        role=role,
        org_name=org_doc.get("name") or "your team",
    )
    await write_audit(
        org, "invitation_created",
        actor_id=actor["id"], actor_email=actor.get("email"),
        target_email=email, meta={"role": role, "invitationId": inv["id"]},
    )

    include_dev = not email_service.is_enabled() and not settings.is_production
    email_delivery = "sent" if email_service.is_enabled() else "manual"
    if include_dev:
        logger.info(f"[INVITE:DEV] {email} org={org} -> {invite_link}")
    out = _public_invitation(inv, include_dev_link=include_dev, raw_token=raw if include_dev else None)
    out["emailDelivery"] = email_delivery
    if email_delivery == "manual":
        out["emailDeliveryNote"] = (
            "Email sending is disabled. Share the invitation link manually "
            "(shown in development when available)."
        )
    return out


@router.get("/invitations")
async def list_invitations(actor: dict = Depends(require_admin)):
    org = actor["organizationId"]
    items = await db.organization_invitations.find(
        {"organizationId": org}, {"_id": 0, "tokenHash": 0},
    ).sort("createdAt", -1).to_list(200)
    # Refresh expired pending
    result = []
    for inv in items:
        inv = await _mark_expired_if_needed(inv)
        pub = _public_invitation(inv)
        pub["status"] = _invitation_state(inv) if inv.get("status") == "pending" else inv.get("status")
        result.append(pub)
    return {"invitations": result}


@router.delete("/invitations/{invitation_id}")
async def cancel_invitation(invitation_id: str, actor: dict = Depends(require_admin)):
    org = actor["organizationId"]
    inv = await db.organization_invitations.find_one(
        {"id": invitation_id, "organizationId": org}, {"_id": 0},
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if inv.get("status") != "pending":
        raise HTTPException(status_code=409, detail=f"Invitation is already {inv.get('status')}")
    await db.organization_invitations.update_one(
        {"id": invitation_id, "organizationId": org},
        {"$set": {"status": "cancelled", "updatedAt": now_iso()}},
    )
    await write_audit(
        org, "invitation_cancelled",
        actor_id=actor["id"], actor_email=actor.get("email"),
        target_email=inv.get("email"), meta={"invitationId": invitation_id},
    )
    return {"ok": True}


@router.get("/invitations/preview/{token}")
async def preview_invitation(token: str):
    """Public preview — never echoes the raw token; never returns tokenHash."""
    inv = await _find_invitation_by_raw_token(token)
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found or invalid")
    inv = await _mark_expired_if_needed(inv)
    state = _invitation_state(inv)
    org = await db.organizations.find_one({"id": inv["organizationId"]}, {"_id": 0, "id": 1, "name": 1})
    existing = await db.users.find_one({"email": inv["email"]}, {"_id": 0, "id": 1})
    return {
        "status": state,
        "email": inv["email"],
        "role": inv["role"],
        "organization": {"id": (org or {}).get("id"), "name": (org or {}).get("name") or "Organization"},
        "invitedByName": inv.get("invitedByName"),
        "expiresAt": inv.get("expiresAt"),
        "accountExists": bool(existing),
    }


@router.post("/invitations/{token}/accept")
async def accept_invitation(token: str, request: Request, response: Response, user: dict = Depends(current_user)):
    rate_limit(f"accept-invite:{_client_ip(request)}", 20, 3600)
    inv = await _find_invitation_by_raw_token(token)
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found or invalid")
    inv = await _mark_expired_if_needed(inv)
    state = _invitation_state(inv)
    if state == "expired":
        raise HTTPException(status_code=410, detail="This invitation has expired")
    if state == "cancelled":
        raise HTTPException(status_code=410, detail="This invitation was cancelled")
    if state == "accepted":
        raise HTTPException(status_code=409, detail="This invitation has already been used")
    if state != "pending":
        raise HTTPException(status_code=409, detail=f"Invitation is {state}")

    if (user.get("email") or "").lower() != inv["email"].lower():
        raise HTTPException(
            status_code=403,
            detail=f"This invitation was sent to {inv['email']}. Sign in with that email to accept.",
        )

    org_id = inv["organizationId"]
    if user.get("organizationId") == org_id:
        await db.organization_invitations.find_one_and_update(
            {"id": inv["id"], "status": "pending"},
            {"$set": {"status": "accepted", "acceptedAt": now_iso(), "acceptedBy": user["id"]}},
        )
        access = A.create_access_token(user["id"], user["email"], org_id)
        try:
            from server import _set_access_cookie, _set_csrf_cookie
            _set_access_cookie(response, access)
            _set_csrf_cookie(response)
        except Exception:
            pass
        return {"ok": True, "user": public_user(user), "alreadyMember": True, "auth": "cookie"}

    ok, reason = await _can_leave_current_org(user)
    if not ok:
        raise HTTPException(status_code=409, detail=reason)

    claimed = await db.organization_invitations.find_one_and_update(
        {"id": inv["id"], "status": "pending", "tokenHash": inv["tokenHash"]},
        {"$set": {"status": "accepted", "acceptedAt": now_iso(), "acceptedBy": user["id"]}},
        return_document=True,
    )
    if not claimed:
        raise HTTPException(status_code=409, detail="This invitation has already been used")

    previous_org = user.get("organizationId")
    updated = await _attach_user_to_org(user, org_id, inv["role"])

    if previous_org and previous_org != org_id:
        prev = await db.organizations.find_one({"id": previous_org}, {"_id": 0})
        if prev and prev.get("ownerId") == user["id"]:
            remaining = await db.users.count_documents({"organizationId": previous_org})
            if remaining == 0:
                await db.organizations.update_one(
                    {"id": previous_org},
                    {"$set": {"ownerId": None, "updatedAt": now_iso(), "abandonedAt": now_iso()}},
                )

    await write_audit(
        org_id, "invitation_accepted",
        actor_id=user["id"], actor_email=user.get("email"),
        target_user_id=user["id"], target_email=user.get("email"),
        meta={"role": inv["role"], "invitationId": inv["id"]},
    )
    access = A.create_access_token(updated["id"], updated["email"], org_id)
    try:
        from server import _set_access_cookie, _set_csrf_cookie
        _set_access_cookie(response, access)
        _set_csrf_cookie(response)
    except Exception:
        pass
    return {
        "ok": True,
        "user": public_user(updated),
        "organizationId": org_id,
        "role": inv["role"],
        "auth": "cookie",
        "requiresTokenRefresh": True,
    }


@router.patch("/members/{user_id}/role")
async def change_member_role(user_id: str, payload: RoleUpdate, actor: dict = Depends(require_admin)):
    org = actor["organizationId"]
    target = await db.users.find_one({"id": user_id, "organizationId": org}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    assert_can_change_role(actor, target, payload.role)
    new_role = normalize_role(payload.role)
    await db.users.update_one(
        {"id": user_id, "organizationId": org},
        {"$set": {"role": new_role, "updatedAt": now_iso()}},
    )
    await write_audit(
        org, "member_role_changed",
        actor_id=actor["id"], actor_email=actor.get("email"),
        target_user_id=user_id, target_email=target.get("email"),
        meta={"from": normalize_role(target.get("role")), "to": new_role},
    )
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "passwordHash": 0})
    org_doc = await _org(org)
    return _public_member(updated, current_user_id=actor["id"], owner_id=org_doc.get("ownerId"))


@router.delete("/members/{user_id}")
async def remove_member(user_id: str, actor: dict = Depends(current_user)):
    org = actor["organizationId"]
    target = await db.users.find_one({"id": user_id, "organizationId": org}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    assert_can_remove_member(actor, target)

    # Removing someone else requires admin+; self-leave for non-owners already allowed above
    if actor["id"] != user_id and not role_at_least(actor.get("role"), "admin"):
        raise HTTPException(status_code=403, detail="You do not have permission to remove members")

    # Detach: place removed user into a fresh personal org so they remain a valid account
    now = now_iso()
    if actor["id"] == user_id:
        # Self-leave → create personal org as owner
        new_org_id = A.gen_id()
        await db.organizations.insert_one({
            "id": new_org_id,
            "name": f"{target.get('firstName') or 'My'}'s Organization",
            "ownerId": target["id"],
            "createdAt": now, "updatedAt": now,
        })
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "organizationId": new_org_id, "role": "owner",
                "joinedAt": now, "updatedAt": now,
            }},
        )
    else:
        # Removed by admin/owner → create personal org for them
        new_org_id = A.gen_id()
        await db.organizations.insert_one({
            "id": new_org_id,
            "name": f"{target.get('firstName') or 'My'}'s Organization",
            "ownerId": target["id"],
            "createdAt": now, "updatedAt": now,
        })
        await db.users.update_one(
            {"id": user_id, "organizationId": org},
            {"$set": {
                "organizationId": new_org_id, "role": "owner",
                "joinedAt": now, "updatedAt": now,
            }},
        )

    await write_audit(
        org, "member_removed",
        actor_id=actor["id"], actor_email=actor.get("email"),
        target_user_id=user_id, target_email=target.get("email"),
        meta={"self": actor["id"] == user_id, "previousRole": normalize_role(target.get("role"))},
    )
    return {"ok": True}


@router.post("/transfer-ownership")
async def transfer_ownership(payload: TransferOwnership, actor: dict = Depends(require_owner)):
    org = actor["organizationId"]
    if payload.userId == actor["id"]:
        raise HTTPException(status_code=400, detail="You already own this organization")
    target = await db.users.find_one({"id": payload.userId, "organizationId": org}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Member not found in this organization")

    now = now_iso()
    # Promote target to owner; demote current owner to admin
    await db.users.update_one(
        {"id": target["id"], "organizationId": org},
        {"$set": {"role": "owner", "updatedAt": now}},
    )
    await db.users.update_one(
        {"id": actor["id"], "organizationId": org},
        {"$set": {"role": "admin", "updatedAt": now}},
    )
    await db.organizations.update_one(
        {"id": org},
        {"$set": {"ownerId": target["id"], "updatedAt": now}},
    )
    await write_audit(
        org, "ownership_transferred",
        actor_id=actor["id"], actor_email=actor.get("email"),
        target_user_id=target["id"], target_email=target.get("email"),
        meta={},
    )
    return {
        "ok": True,
        "ownerId": target["id"],
        "previousOwnerId": actor["id"],
    }


# ---------------- helpers exported for register flow ----------------
async def consume_invitation_for_new_user(raw_token: str, email: str) -> dict:
    """Validate invite for registration. Returns invitation dict or raises HTTPException."""
    inv = await _find_invitation_by_raw_token(raw_token)
    if not inv:
        raise HTTPException(status_code=400, detail="Invalid invitation token")
    inv = await _mark_expired_if_needed(inv)
    state = _invitation_state(inv)
    if state != "pending":
        raise HTTPException(status_code=400, detail=f"Invitation is {state}")
    if inv["email"].lower() != email.lower():
        raise HTTPException(status_code=400, detail="Invitation email does not match registration email")
    return inv


async def mark_invitation_accepted(inv_id: str, user_id: str, token_hash: str) -> bool:
    res = await db.organization_invitations.find_one_and_update(
        {"id": inv_id, "status": "pending", "tokenHash": token_hash},
        {"$set": {"status": "accepted", "acceptedAt": now_iso(), "acceptedBy": user_id}},
        return_document=True,
    )
    return bool(res)
