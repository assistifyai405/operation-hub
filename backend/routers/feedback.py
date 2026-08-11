"""Closed-beta feedback — store in Mongo, org-scoped, no external SaaS."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

import auth as A
from audit import write_audit
from core import db, now_iso
from dependencies import current_user, current_org, rate_limit
from permissions import require_admin

router = APIRouter(prefix="/api")

CATEGORIES = ("Bug", "Idea", "Confusing", "Other")


class FeedbackCreate(BaseModel):
    category: Literal["Bug", "Idea", "Confusing", "Other"]
    message: str = Field(..., min_length=3, max_length=4000)
    page: Optional[str] = Field(None, max_length=500)
    context: Optional[str] = Field(None, max_length=1000)


def _public(doc: dict) -> dict:
    return {
        "id": doc["id"],
        "organizationId": doc["organizationId"],
        "userId": doc.get("userId"),
        "userEmail": doc.get("userEmail"),
        "userName": doc.get("userName"),
        "category": doc.get("category"),
        "message": doc.get("message"),
        "page": doc.get("page"),
        "context": doc.get("context"),
        "createdAt": doc.get("createdAt"),
        "status": doc.get("status", "open"),
    }


@router.post("/feedback")
async def submit_feedback(
    body: FeedbackCreate,
    user: dict = Depends(current_user),
    org: str = Depends(current_org),
):
    """Authenticated beta feedback submission."""
    rate_limit(f"feedback:{user['id']}", 20, 3600)
    msg = (body.message or "").strip()
    if len(msg) < 3:
        raise HTTPException(status_code=400, detail="Please include a short message.")
    if body.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")

    name = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip() or user.get("email")
    doc = {
        "id": A.gen_id(),
        "organizationId": org,
        "userId": user["id"],
        "userEmail": user.get("email"),
        "userName": name,
        "category": body.category,
        "message": msg[:4000],
        "page": (body.page or "")[:500] or None,
        "context": (body.context or "")[:1000] or None,
        "createdAt": now_iso(),
        "status": "open",
    }
    await db.beta_feedback.insert_one(dict(doc))
    await write_audit(
        org, "beta_feedback_submitted",
        actor_id=user.get("id"), actor_email=user.get("email"),
        meta={"feedbackId": doc["id"], "category": body.category},
    )
    return _public(doc)


@router.get("/feedback")
async def list_feedback(
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    org: str = Depends(current_org),
    user: dict = Depends(require_admin),
):
    """Owner/admin view of feedback for this workspace only."""
    q = {"organizationId": org}
    if category:
        if category not in CATEGORIES:
            raise HTTPException(status_code=400, detail="Invalid category")
        q["category"] = category
    items = await db.beta_feedback.find(q, {"_id": 0}).sort("createdAt", -1).to_list(limit)
    return {
        "feedback": [_public(i) for i in items],
        "total": await db.beta_feedback.count_documents({"organizationId": org}),
    }


@router.get("/feedback/count")
async def feedback_count(org: str = Depends(current_org), user: dict = Depends(require_admin)):
    total = await db.beta_feedback.count_documents({"organizationId": org})
    return {"total": total}
