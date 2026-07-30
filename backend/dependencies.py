import time

from fastapi import Request, HTTPException, Depends

from core import db
import auth as A
from rate_limit import rate_limit, _rl_store  # noqa: F401 — re-export for tests


def public_user(u: dict) -> dict:
    return {
        "id": u["id"], "firstName": u.get("firstName", ""), "lastName": u.get("lastName", ""),
        "email": u["email"], "emailVerified": u.get("emailVerified", False),
        "avatar": u.get("avatar", ""), "role": u.get("role", "owner"),
        "organizationId": u.get("organizationId"), "timezone": u.get("timezone", "UTC"),
        "language": u.get("language", "en"), "createdAt": u.get("createdAt"),
        "updatedAt": u.get("updatedAt"), "lastLogin": u.get("lastLogin"),
        "onboardingCompleted": u.get("onboardingCompleted", True),
    }


async def current_user(request: Request) -> dict:
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = A.decode_token(token)
    except A.jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except A.jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def current_org(user: dict = Depends(current_user)) -> str:
    return user["organizationId"]


async def require_project(project_id: str, org: str) -> dict:
    p = await db.projects.find_one({"id": project_id, "organizationId": org}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
