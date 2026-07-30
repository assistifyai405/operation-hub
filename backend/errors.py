"""Consistent API error envelope (preserves FastAPI `detail` for compatibility)."""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def error_body(
    *,
    code: str,
    message: str,
    request_id: Optional[str] = None,
    details: Any = None,
    detail: Any = None,
) -> dict:
    """Include both `error` envelope and legacy `detail`."""
    body = {
        "detail": detail if detail is not None else message,
        "error": {"code": code, "message": message, "requestId": request_id},
    }
    if details is not None:
        body["error"]["details"] = details
    return body


def _request_id(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None) or request.headers.get("x-request-id")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exc_handler(request: Request, exc: HTTPException):
        rid = _request_id(request)
        detail = exc.detail
        headers = getattr(exc, "headers", None) or {}
        if isinstance(detail, dict) and detail.get("code"):
            message = detail.get("message") or str(detail)
            body = error_body(
                code=detail.get("code") or "http_error",
                message=str(message),
                request_id=rid,
                details={k: v for k, v in detail.items() if k not in ("code", "message")},
                detail=detail,
            )
            if detail.get("actionable"):
                body["error"]["actionable"] = detail["actionable"]
            return JSONResponse(status_code=exc.status_code, content=body, headers=headers)
        if isinstance(detail, dict):
            message = detail.get("message") or detail.get("msg") or "Request failed"
            code = detail.get("code") or "http_error"
            return JSONResponse(
                status_code=exc.status_code,
                content=error_body(code=code, message=str(message), request_id=rid, detail=detail),
                headers=headers,
            )
        code = "not_found" if exc.status_code == 404 else "http_error"
        if exc.status_code == 401:
            code = "unauthorized"
        elif exc.status_code == 403:
            code = "forbidden"
        elif exc.status_code == 429:
            code = "rate_limited"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code=code, message=str(detail), request_id=rid, detail=detail),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error_body(
                code="validation_error",
                message="Request validation failed",
                request_id=_request_id(request),
                details=exc.errors(),
                detail=exc.errors(),
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        logger.exception("Unhandled error request_id=%s", _request_id(request))
        try:
            from config import get_settings
            prod = get_settings().is_production
        except Exception:
            prod = True
        message = "Internal server error" if prod else str(exc)
        return JSONResponse(
            status_code=500,
            content=error_body(code="internal_error", message=message, request_id=_request_id(request), detail=message),
        )
