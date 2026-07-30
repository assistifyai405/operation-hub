"""Role-based access helpers for organization membership.

Roles (stored on users.role, compatible with pre-Sprint-13 single-owner orgs):
  - owner  — full control; exactly one per organization (organizations.ownerId)
  - admin  — manage members/invites; cannot touch ownership
  - member — product access only
"""
from __future__ import annotations

from typing import Callable, Optional

from fastapi import Depends, HTTPException

from dependencies import current_user

ROLES = ("owner", "admin", "member")
ROLE_RANK = {"member": 1, "admin": 2, "owner": 3}

ASSIGNABLE_ROLES = ("admin", "member")  # cannot invite/promote directly to owner


def normalize_role(role: Optional[str]) -> str:
    r = (role or "member").strip().lower()
    if r not in ROLE_RANK:
        return "member"
    return r


def role_at_least(user_role: str | None, minimum: str) -> bool:
    return ROLE_RANK.get(normalize_role(user_role), 0) >= ROLE_RANK.get(minimum, 99)


def require_roles(*allowed: str) -> Callable:
    """FastAPI dependency factory: current user must have one of the allowed roles."""
    allowed_set = {normalize_role(r) for r in allowed}

    async def _dep(user: dict = Depends(current_user)) -> dict:
        role = normalize_role(user.get("role"))
        if role not in allowed_set:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
        return user

    return _dep


require_owner = require_roles("owner")
require_admin = require_roles("owner", "admin")  # min admin
require_member = require_roles("owner", "admin", "member")


def assert_can_invite(actor_role: str, invite_role: str) -> None:
    invite_role = normalize_role(invite_role)
    if invite_role == "owner":
        raise HTTPException(status_code=400, detail="Cannot invite someone as owner — transfer ownership instead")
    if invite_role not in ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Use one of: {', '.join(ASSIGNABLE_ROLES)}")
    if not role_at_least(actor_role, "admin"):
        raise HTTPException(status_code=403, detail="Only owners and admins can invite members")


def assert_can_change_role(actor: dict, target: dict, new_role: str) -> None:
    actor_role = normalize_role(actor.get("role"))
    target_role = normalize_role(target.get("role"))
    new_role = normalize_role(new_role)

    if actor["id"] == target["id"]:
        raise HTTPException(status_code=400, detail="You cannot change your own role")
    if target_role == "owner":
        raise HTTPException(status_code=403, detail="Cannot change the owner's role — transfer ownership instead")
    if new_role == "owner":
        raise HTTPException(status_code=400, detail="Cannot promote to owner — use transfer ownership")
    if new_role not in ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Use one of: {', '.join(ASSIGNABLE_ROLES)}")
    if actor_role == "owner":
        return
    if actor_role == "admin":
        if target_role != "member" or new_role != "member":
            # Admin may only manage regular members (keep as member or… actually admin can remove members
            # but changing member→admin should be owner-only for safety? Spec: Admin cannot promote to owner.
            # Spec doesn't forbid admin promoting member to admin. Allow admin to set admin|member on members only.
            if target_role == "admin":
                raise HTTPException(status_code=403, detail="Admins cannot change another admin's role")
            return
        return
    raise HTTPException(status_code=403, detail="You do not have permission to change roles")


def assert_can_remove_member(actor: dict, target: dict) -> None:
    actor_role = normalize_role(actor.get("role"))
    target_role = normalize_role(target.get("role"))

    if actor["id"] == target["id"]:
        if target_role == "owner":
            raise HTTPException(
                status_code=400,
                detail="Owners cannot leave without transferring ownership first",
            )
        # Non-owners may leave themselves
        return
    if target_role == "owner":
        raise HTTPException(status_code=403, detail="Cannot remove the organization owner")
    if actor_role == "owner":
        return
    if actor_role == "admin":
        if target_role != "member":
            raise HTTPException(status_code=403, detail="Admins can only remove regular members")
        return
    raise HTTPException(status_code=403, detail="You do not have permission to remove members")
