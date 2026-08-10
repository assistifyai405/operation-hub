"""CSRF double-submit for cookie-authenticated mutating requests.

Browser sessions use httpOnly access/refresh cookies. A readable csrf_token
cookie is set alongside the session; the SPA must echo it as X-CSRF-Token
on POST/PUT/PATCH/DELETE when not using Authorization: Bearer.

Bearer-authenticated requests (tests / future machine clients) skip CSRF.
"""
from __future__ import annotations

import secrets
from typing import Iterable

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "x-csrf-token"
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}

# Auth bootstrap + public webhooks — no CSRF required
CSRF_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    "/api/auth/verify-email",
    "/api/auth/demo",
    "/api/webhooks/",
    "/api/integrations/oauth/callback/",
    "/api/health",
    "/api/config/public",
)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_cookie_flags() -> dict:
    try:
        from config import get_settings
        s = get_settings()
        return {"httponly": False, "secure": s.cookie_secure, "samesite": s.cookie_samesite}
    except Exception:
        return {"httponly": False, "secure": False, "samesite": "lax"}


def _exempt(path: str) -> bool:
    for p in CSRF_EXEMPT_PREFIXES:
        if path == p or path.startswith(p):
            return True
    return False


def require_csrf_if_cookie_session(request: Request) -> None:
    """Raise 403 when cookie session mutates without matching CSRF header."""
    if request.method not in UNSAFE:
        return
    if _exempt(request.url.path):
        return
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return  # machine / test clients
    if not request.cookies.get("access_token") and not request.cookies.get("refresh_token"):
        return  # unauthenticated — endpoint will 401
    cookie_csrf = request.cookies.get(CSRF_COOKIE) or ""
    header_csrf = request.headers.get(CSRF_HEADER) or request.headers.get("X-CSRF-Token") or ""
    if not cookie_csrf or not header_csrf or not secrets.compare_digest(cookie_csrf, header_csrf):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            require_csrf_if_cookie_session(request)
        except HTTPException as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        return await call_next(request)
