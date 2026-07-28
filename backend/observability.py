"""Structured logging with secret redaction."""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

SENSITIVE_KEYS = re.compile(
    r"(authorization|cookie|token|secret|password|api[_-]?key|credential|refresh|access_token)",
    re.I,
)
BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.I)


def redact(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if SENSITIVE_KEYS.search(str(k)):
                out[k] = "[REDACTED]"
            else:
                out[k] = redact(v)
        return out
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return BEARER_RE.sub("Bearer [REDACTED]", value)
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        for key in ("request_id", "organization_id", "user_id", "route", "duration_ms", "status_code", "job_id", "provider", "error_code"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)[:2000]
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    root.addHandler(handler)
    root.setLevel(getattr(logging, (level or "INFO").upper(), logging.INFO))


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.time()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration = int((time.time() - start) * 1000)
            # Skip noisy health probes at debug
            path = request.url.path
            logger = logging.getLogger("http")
            extra = {
                "request_id": request_id,
                "route": path,
                "duration_ms": duration,
                "status_code": status,
            }
            if path.startswith("/api/health"):
                logger.debug("request", extra=extra)
            else:
                logger.info("request method=%s", request.method, extra=extra)
