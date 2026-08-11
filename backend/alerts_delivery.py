"""Optional lightweight alert delivery (webhook / Slack incoming webhook).

Disabled by default. Never logs or sends secret values.
Deduplicates by alert code with a TTL (Redis when available, else process memory).
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_memory_dedupe: dict[str, float] = {}
DEFAULT_TTL_SECONDS = 900  # 15 minutes
MAX_ALERTS_PER_PAYLOAD = 20


def _settings():
    from config import get_settings
    return get_settings()


def delivery_enabled() -> bool:
    import os
    raw = os.environ.get("ALERT_DELIVERY_ENABLED", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    return False


def webhook_url() -> Optional[str]:
    import os
    from config import get_settings
    url = (os.environ.get("ALERT_WEBHOOK_URL") or "").strip()
    if url:
        return url
    # Optional settings field if present
    try:
        s = get_settings()
        return getattr(s, "alert_webhook_url", None) or None
    except Exception:
        return None


def _dedupe_key(code: str, environment: str) -> str:
    return f"alert:{environment}:{code}"


def _already_sent(key: str, ttl: int) -> bool:
    now = time.time()
    # Redis
    try:
        from redis_client import get_redis
        r = get_redis()
        if r:
            full = f"assistify:{key}"
            if r.get(full):
                return True
            r.setex(full, ttl, "1")
            return False
    except Exception:
        pass
    # Memory fallback
    exp = _memory_dedupe.get(key)
    if exp and exp > now:
        return True
    _memory_dedupe[key] = now + ttl
    # opportunistic prune
    if len(_memory_dedupe) > 200:
        for k, v in list(_memory_dedupe.items()):
            if v <= now:
                _memory_dedupe.pop(k, None)
    return False


async def collect_alert_snapshot() -> dict[str, Any]:
    """Build the same shape as /api/health/alerts without importing the route response wrapper."""
    from routers.health import health_alerts
    result = await health_alerts()
    if hasattr(result, "body"):
        import json
        status = getattr(result, "status_code", 200)
        try:
            body = json.loads(result.body.decode() if isinstance(result.body, (bytes, bytearray)) else result.body)
        except Exception:
            body = {"ok": False, "alerts": [], "critical": True}
        body["_httpStatus"] = status
        return body
    if isinstance(result, dict):
        result = {**result, "_httpStatus": 200}
        return result
    return {"ok": True, "alerts": [], "critical": False, "_httpStatus": 200}


def _slack_text(snapshot: dict) -> str:
    env = snapshot.get("environment") or "unknown"
    release = snapshot.get("release") or "dev"
    lines = [f"*Assistify alert* (`{env}` / `{release}`)"]
    for a in (snapshot.get("alerts") or [])[:MAX_ALERTS_PER_PAYLOAD]:
        sev = a.get("severity", "info")
        code = a.get("code", "unknown")
        msg = a.get("message", "")
        # Strip anything that looks like a secret-ish token
        msg = _redact(str(msg))
        lines.append(f"• `{sev}` `{code}` — {msg}")
    if not snapshot.get("alerts"):
        lines.append("• (no alerts)")
    return "\n".join(lines)


def _redact(text: str) -> str:
    import re
    text = re.sub(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*\S+", r"\1=[redacted]", text)
    text = re.sub(r"sk-[A-Za-z0-9]{10,}", "sk-[redacted]", text)
    return text[:500]


async def deliver_alerts(force: bool = False) -> dict[str, Any]:
    """Evaluate health alerts and POST to webhook when enabled.

    Returns a safe status dict (no secrets).
    """
    if not delivery_enabled() and not force:
        return {"delivered": False, "reason": "disabled"}

    url = webhook_url()
    if not url:
        return {"delivered": False, "reason": "no_webhook_url"}
    if not url.lower().startswith("https://"):
        logger.warning("ALERT_WEBHOOK_URL ignored — must be https")
        return {"delivered": False, "reason": "webhook_not_https"}

    snapshot = await collect_alert_snapshot()
    alerts = snapshot.get("alerts") or []
    if not alerts:
        return {"delivered": False, "reason": "no_alerts", "alertCount": 0}

    # Deduplicate: only send codes not recently notified
    ttl = DEFAULT_TTL_SECONDS
    try:
        import os
        ttl = int(os.environ.get("ALERT_DEDUPE_SECONDS") or DEFAULT_TTL_SECONDS)
    except Exception:
        ttl = DEFAULT_TTL_SECONDS

    env = str(snapshot.get("environment") or "unknown")
    new_alerts = []
    for a in alerts:
        code = str(a.get("code") or "unknown")
        key = _dedupe_key(code, env)
        if force or not _already_sent(key, ttl):
            new_alerts.append(a)

    if not new_alerts:
        return {"delivered": False, "reason": "deduped", "alertCount": len(alerts)}

    payload_snapshot = {**snapshot, "alerts": new_alerts}
    # Slack incoming webhooks accept {"text": "..."}
    body = {"text": _slack_text(payload_snapshot), "alerts": [
        {"severity": a.get("severity"), "code": a.get("code"), "message": _redact(str(a.get("message") or ""))}
        for a in new_alerts
    ], "environment": env, "release": snapshot.get("release"), "critical": bool(snapshot.get("critical"))}

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body)
        ok = 200 <= resp.status_code < 300
        if not ok:
            logger.warning("Alert webhook delivery failed status=%s", resp.status_code)
        return {
            "delivered": ok,
            "statusCode": resp.status_code,
            "alertCount": len(new_alerts),
            "codes": [a.get("code") for a in new_alerts],
        }
    except Exception as e:
        logger.warning("Alert webhook delivery error: %s", type(e).__name__)
        return {"delivered": False, "reason": "request_failed"}
